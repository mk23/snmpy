import BaseHTTPServer

import bisect
import ctypes
import ctypes.util
import datetime
import glob
import logging
import logging.handlers
import multiprocessing
import os
import pickle
import re
import select
import sys
import time
import threading
import traceback
import urllib2
import yaml

VERSION = '20120921.001'

class ReachedLastKeyError(Exception): pass
class ReachedLastModError(Exception): pass

class oidkey:
    def __init__(self, o):
        if isinstance(o, (str, unicode)):
            self.s = str(o)
            self.k = tuple(int(i) for i in o.split('.'))
        elif isinstance(o, (list, tuple)) and len([None for i in o if not isinstance(i, int) and not str(i).isdigit()]) == 0:
            self.s = '.'.join(str(s) for s in o)
            self.k = tuple(o)
        elif isinstance(o, oidkey):
            self = o
        else:
            raise TypeError('require a list or dot-separated string of positive integers')

    def __str__(self):
        return self.s

    def __repr__(self):
        return 'snmpy.oidkey(%r)' % self.s

    def __cmp__(self, other):
        if isinstance(other, oidkey):
            peer = other
        elif isinstance(other, (str, unicode, list, tuple)):
            peer = oidkey(other)
        else:
            raise TypeError('cannot compare with %s' % type(other))

        t1 = self.k + tuple(0 for i in xrange(len(peer.k) - len(self.k)))
        t2 = peer.k + tuple(0 for i in xrange(len(self.k) - len(peer.k)))

        if t1  < t2:
            return -1
        if t1 == t2:
            return 0
        if t1  > t2:
            return 1


class oidval:
    def __init__(self, t, v, e={}):
        self.t = t
        self.v = v
        self.e = e

    def get(self):
        return self.t, self.v

    def set(self, v):
        if type(v) == dict:
            self.e = v
        else:
            self.v = v

    def __str__(self):
        return '%s: %s' % (self.t, self.v)

    def __repr__(self):
        return 'snmpy.oidval(%r, %r, %r)' % (self.t, self.v, self.e)

    def __contains__(self, k):
        return k in self.e

    def __getitem__(self, k):
        return self.e[k]

    def __iadd__(self, v):
        self.v += v
        return self
    def __add__(self, v):
        return self.v + v

    def __isub__(self, v):
        self.v -= v
        return self
    def __sub__(self, v):
        return self.v - v

    def __imul__(self, v):
        self.v *= v
        return self
    def __mul__(self, v):
        return self * v

    def __idiv__(self, v):
        self.v /= v
        return self
    def __div__(self, v):
        return self.v / v

    def __imod__(self, v):
        self.v %= v
        return self
    def __mod__(self, v):
        return self.v % v


class bucket:
    def __init__(self, name=None):
        self.d = {}
        self.l = []
        self.f = name

        self.load()

    def save(self, f=None):
        dst = self.f or f
        if dst:
            try:
                pickle.dump(dict((k, v.get()) for k, v in self.d.items()), open(dst, 'w'))
                logging.debug('saved bucket change to %s', dst)
            except Exception as e:
                log_error(e, 'unable to save data file: %s' % dst)

    def load(self, f=None):
        src = self.f or f
        if src:
            try:
                for k, v in pickle.load(open(src)).items():
                    self[k] = v[1] if k in self else v

                logging.info('loaded saved bucket state from: %s', src)
            except Exception as e:
                log_error(e, 'unable to load data file: %s' % src)

    def __str__(self):
        return '\n'.join('%-3d: %5s: %s' % (i, self.l[i], self.d[str(self.l[i])]) for i in xrange(len(self.l)))

    def __contains__(self, key):
        return key in self.d

    def __delitem__(self, key):
        idx = bisect.bisect_left(self.l, oidkey(key))
        del self.l[idx]
        del self.d[key]

    def __getitem__(self, key):
        if type(key) == slice:
            if key.stop is None:
                logging.debug('requested iterator starting from key %s', key.start)
                idx = bisect.bisect_right(self.l, oidkey(key.start))
                return (str(k) for k in self.l[idx:])
            if key.stop is True:
                logging.debug('requested just value from key %s', key.start)
                return self.d[str(key.start)]
            if type(key.stop) == str:
                logging.debug('requested attribute %s from key %s', key.stop, key.start)
                return self.d[str(key.start)][key.stop]

            logging.debug('requested key position %d starting from %s', key.stop, key.start)
            idx = bisect.bisect_right(self.l, oidkey(key.start)) + key.stop
            ref = str(self.l[idx])
        elif type(key) == int:
            logging.debug('requested key position %d', key)
            ref = str(self.l[key])
        else:
            logging.debug('requested key %s', key)
            ref = str(key)

        if 'run' in self.d[ref]:
            logging.debug('performing callback')
            self.d[ref]['run'](ref)

        return ref, self.d[ref].get()

    def __setitem__(self, key, val):
        if key not in self.d:
            oid = oidkey(key)
            idx = bisect.bisect_right(self.l, oid)

            self.l.insert(idx, oid)
            self.d[key] = oidval(*val)
            logging.debug('created key %5s: %s', key, self.d[key])
        else:
            self.d[key].set(val)
            logging.debug('changed key %5s: %s', key, val)

    def __len__(self):
        return len(self.l)

    def __iter__(self):
        return (str(k) for k in self.l)


class plugin:
    def __init__(self, name, conf=None):
        self.name = name
        self.conf = {} if conf is None else conf
        self.data = bucket()

        if self.conf.get('snmpy_collect'):
            if self.conf.get('script'):
                self.script()
            else:
                logging.debug('%s: skipping collection in non-collector plugin', name)
        else:
            if self.conf.has_key('snmpy_datadir'):
                self.reload()
            self.create()

    def __iter__(self):
        items = self.conf.get('objects')
        if type(items) in (tuple, list):
            return ((i + 1, items[i]) for i in xrange(len(items)))
        elif isinstance(items, dict):
            return ((k, v) for k, v in sorted(items.items()))

    def reload(self):
        temp_data = bucket('%s/%s.dat' % (self.conf['snmpy_datadir'], self.name))
        self.data = temp_data

    def member(self, obj, nxt=False):
        if nxt:
            try:
                oid, val = self.data[0]
                if obj < oid:
                    return oid, val
                else:
                    return self.data[obj:0]
            except IndexError:
                raise ReachedLastKeyError
        else:
            return self.data[obj]

    def create(self):
        pass

    def script(self):
        raise NotImplementedError('%s: plugin cannot run scripts' % self.name)

###
# plugin utility
###
def save(func):
    def decorated(self, *args, **kwargs):
        data_file = '%s/%s.dat' % (self.conf['snmpy_datadir'], self.name)

        threshold = self.conf['system_boot'] if self.conf['script'] == 'boot' else time.time() - self.conf['script']
        code_date = os.stat(sys.modules[self.__class__.__module__].__file__).st_mtime
        run_limit = max(code_date, threshold)

        logging.debug('%s: run limit: %s', self.name, datetime.datetime.fromtimestamp(run_limit))
        if self.conf['snmpy_collect'] == 'force' or not os.path.exists(data_file) or os.stat(data_file).st_mtime < run_limit:
            func(self, *args, **kwargs)
            self.data.save(data_file)
            urllib2.urlopen('http://localhost:%d/%d' %(self.conf['snmpy_runport'], self.conf['snmpy_index']))
            logging.info('saved result data to %s', data_file)
        else:
            logging.debug('%s: skipping run: recent change', data_file)

    return decorated

def task(func):
    def decorated(*args, **kwargs):
        threading.Thread(target=work, args=[func]+list(args), kwargs=kwargs).start()

    return decorated

def work(func, *args, **kwargs):
    try:
        logging.debug('starting background task: %s', func.__name__)
        func(*args, **kwargs)
    except Exception as e:
        log_fatal(e)

def tail(name, notify=False):
    while True:
        try:
            file = open(name)
            file.seek(0, 2) # start at the end
            logging.debug('%s: opened file for tail', name)
            break
        except IOError as e:
            logging.info('%s: cannot open for tail: %s', name, e)
            time.sleep(5)
        except Exception as e:
            log_error(e)

    while True:
        spot = file.tell()
        stat = os.fstat(file.fileno())

        if os.stat(name).st_ino != stat.st_ino or stat.st_nlink == 0 or spot > stat.st_size:
            if notify:
                yield True

            try:
                file = open(name)
                logging.info('%s: repopened for tail: moved, truncated, or removed', name)
            except IOError as e:
                logging.info('%s: cannot open for tail: %s', name, e)
        elif spot != stat.st_size:
            buff = file.read(stat.st_size - spot)
            while True:
                indx = buff.find('\n')
                if indx == -1:
                    file.seek(-len(buff), 1)
                    break
                line = buff[0:indx]
                buff = buff[indx + 1:]

                yield line

        time.sleep(1)


###
# offline loader
###
class handler(BaseHTTPServer.BaseHTTPRequestHandler):
    log_message = lambda *args: True
    server_version = '%s %s/%s' % (BaseHTTPServer.BaseHTTPRequestHandler.server_version, __name__, VERSION)

    def do_GET(self):
        find = re.match(r'^/(\d+)$', self.path)
        if find:
            self.server.pipe.send(int(find.group(1)))
            code, body = self.server.pipe.recv()

            self.send_error(200 if code == 'success' else 404, body)
        else:
            self.send_error(404, '%s is not available' % self.path)


def start_server(port):
    try:
        logging.info('starting http command channel on port %d', port)
        serv = BaseHTTPServer.HTTPServer(('127.0.0.1', port), handler)
        comm = multiprocessing.Pipe(duplex=True)
        proc = multiprocessing.Process(target=start_worker, args=(serv, comm))
        proc.start()

        comm[1].close()
        return comm[0]
    except Exception as e:
        log_fatal(e)

def start_worker(server, (unused, worker)):
    logging.debug('started http command channel')

    unused.close()
    server.pipe = worker

    while True:
        try:
            for reader in select.select([server, worker], [], [])[0]:
                logging.debug('http worker received event on %s', reader)
                if reader == server:
                    server.handle_request()
                else:
                    worker.recv()
        except KeyboardInterrupt:
            log_fatal('caught user interrupt in http server, exiting', exit=0)
        except EOFError:
            log_fatal('parent exited, terminating http command channel', exit=0)
        except Exception as e:
            log_fatal(e)


###
# initialization helpers
###
def create_log(logger=None, debug=False):
    log = logging.getLogger()

    if logger or debug:
        if logger and logger.startswith('syslog:'):
            log_hdlr = logging.handlers.SysLogHandler(facility=logger.split(':')[-1])
        elif logger and not logger.startswith('console:'):
            log_hdlr = logging.FileHandler(logger)
        else:
            log_hdlr = logging.StreamHandler()

        log_hdlr.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(filename)16s:%(lineno)-3d %(levelname)8s: %(message)s', '%Y-%m-%d %H:%M:%S'))

        log.setLevel(logging.DEBUG if debug else logging.INFO)
        log.addHandler(log_hdlr)

        log.info('logging started')
    else:
        log.addHandler(logging.NullHandler())

    return log

def parse_conf(parser):
    try:
        args = parser.parse_args()
        conf = yaml.load(open(args.cfgfile))

        parser.set_defaults(**(conf['snmpy_global']))

        args = parser.parse_args()
        conf['snmpy_global'].update(vars(args))

        create_log(conf['snmpy_global']['logfile'], conf['snmpy_global']['verbose'])

        logging.debug('starting system with merged args: %s', args)
    except (IOError, yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
        parser.error('cannot parse configuration file: %s' % e)

    boot_time = get_boot()
    logging.debug('system boot time: %s', str(datetime.datetime.fromtimestamp(boot_time)))

    if conf['snmpy_global']['include_dir']:
        for item in glob.glob('%s/*.y*ml' % conf['snmpy_global']['include_dir']):
            try:
                indx, name = os.path.splitext(os.path.basename(item))[0].split('_', 1)
                if name in conf:
                    raise ValueError('%s: plugin name already assigned at another index', name)
                if int(indx) < 1:
                    raise ValueError('%s: invalid plugin index', indx)
                if int(indx) in list(v['snmpy_index'] for k, v in conf.items() if k != 'snmpy_global'):
                    raise ValueError('%s: index already assigned to another plugin', indx)

                conf[name] = {
                    'system_boot':   boot_time,
                    'snmpy_index':   int(indx),
                    'snmpy_extra':   dict(args.extra),
                    'snmpy_runport': args.runport,
                    'snmpy_datadir': args.datadir,
                    'snmpy_collect': args.collect,
                }
                conf[name].update(yaml.load(open(item)))
            except (IOError, yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
                parser.error('cannot parse configuration file: %s' % e)

    return conf


###
# log utility
###
def log_error(e, msg=None):
    if msg:
        logging.error('%s: %s', msg, e)
    else:
        logging.error(e)

    for line in traceback.format_exc().split('\n'):
        logging.debug('  %s', line)

def log_fatal(item, prio='error', exit=1):
    if isinstance(item, Exception):
        log_error(item)
    else:
        vars(logging).get(prio, 'error')(item)

    if exit is not None:
        sys.exit(exit)


###
# boot time
###
def get_boot():
    if sys.platform.startswith('linux'):
        return boot_lnx()
    elif sys.platform.startswith('darwin'):
        return boot_bsd()
    elif sys.platform.startswith('freebsd'):
        return boot_bsd()

    raise OSError('unsupported platform')

def boot_lnx():
    return int([line.split()[1] for line in open('/proc/stat') if line.startswith('btime')][0])

def boot_bsd():
    class timeval(ctypes.Structure):
        _fields_ = [
            ('tv_sec',  ctypes.c_long),
            ('tv_usec', ctypes.c_long),
        ]

    c = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))

    tv = timeval()
    sz = ctypes.c_size_t(ctypes.sizeof(tv))

    if (c.sysctlbyname(ctypes.c_char_p('kern.boottime'), ctypes.byref(tv), ctypes.byref(sz), None, ctypes.c_size_t(0)) == -1):
        raise RuntimeError('sysctl error')

    return tv.tv_sec

