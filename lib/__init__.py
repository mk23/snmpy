import bisect
import ctypes
import ctypes.util
import datetime
import logging as log
import os
import pickle
import time
import sys
import threading
import traceback

from snmpy.__version__ import __version__

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

    def __repr__(self):
        return self.s

    def __str__(self):
        return self.s

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
        self.v = v

    def __str__(self):
        return '%s: %s' % (self.t, self.v)

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
    def __init__(self):
        self.d = {}
        self.l = []

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
                log.debug('requested iterator starting from key %s', key.start)
                idx = bisect.bisect_right(self.l, oidkey(key.start))
                return (str(k) for k in self.l[idx:])
            if key.stop is True:
                log.debug('requested just value from key %s', key.start)
                return self.d[str(key.start)]
            if type(key.stop) == str:
                log.debug('requested attribute %s from key %s', key.stop, key.start)
                return self.d[str(key.start)][key.stop]

            log.debug('requested key position %d starting from %s', key.stop, key.start)
            idx = bisect.bisect_left(self.l, oidkey(key.start)) + key.stop
            ref = str(self.l[idx])
        elif type(key) == int:
            log.debug('requested key position %d', key)
            ref = str(self.l[key])
        else:
            log.debug('requested key %s', key)
            ref = str(key)

        if 'run' in self.d[ref]:
            log.debug('performing callback')
            self.d[ref]['run'](ref)

        return ref, self.d[ref].get()

    def __setitem__(self, key, val):
        if key not in self.d:
            oid = oidkey(key)
            idx = bisect.bisect_right(self.l, oid)

            self.l.insert(idx, oid)
            self.d[key] = oidval(*val)
            log.debug('created key %5s: %s', key, self.d[key])
        else:
            self.d[key].set(val)
            log.debug('changed key %5s: %s', key, val)

    def __len__(self):
        return len(self.l)

    def __iter__(self):
        return (str(k) for k in self.l)

class plugin:
    def __init__(self, conf, script=False):
        self.conf = conf
        self.data = bucket()
        if not script:
            self.create()
        elif 'script' in self.conf:
            self.info = {}
            self.script()

    def create(self):
        pass

    def script(self):
        raise NotImplementedError('%s: plugin cannot run scripts' % self.name)

    def member(self, obj, nxt=False):
        if nxt:
            oid, val = self.data[0]
            if obj < oid:
                return oid, val
            else:
                return self.data[obj:1]
        else:
            return self.data[obj]

    @staticmethod
    def load(func):
        def decorated(self, *args, **kwargs):
            data_file = '%s/%s.dat' % (self.conf['path'], self.conf['name'])
            log.debug('loading saved data from %s', data_file)
            for key, val in pickle.load(open(data_file, 'r')).items():
                self.data[key] = val

            return func(self, *args, **kwargs)
        return decorated

    @staticmethod
    def save(func):
        def decorated(self, *args, **kwargs):
            data_file = '%s/%s.dat' % (self.conf['path'], self.conf['name'])

            threshold = boot if self.conf['script'] == 'boot' else time.time() - int(self.conf['script'])
            code_date = os.stat(sys.modules[self.__class__.__module__].__file__).st_mtime
            run_limit = max(code_date, threshold)

            log.debug('%s run limit: %s', self.conf['name'], datetime.datetime.fromtimestamp(run_limit))
            if not os.path.exists(data_file) or os.stat(data_file).st_mtime < run_limit:
                func(self, *args, **kwargs)
                pickle.dump(self.info, open(data_file, 'w'))
                log.info('saved result data to %s', data_file)
            else:
                log.debug('%s: skipping run: recent change', data_file)

        return decorated

    @staticmethod
    def task(func):
        def decorated(*args, **kwargs):
            threading.Thread(target=func, args=args, kwargs=kwargs).start()
            log.debug('started background task: %s', func.__name__)

        return decorated

    @staticmethod
    def tail(file, notify=False):
        file = open(file)
        file.seek(0, 2) # start at the end
        log.debug('opened file for tail: %s', file.name)

        while True:
            spot = file.tell()
            stat = os.fstat(file.fileno())

            if os.stat(file.name).st_ino != stat.st_ino or stat.st_nlink == 0 or spot > stat.st_size:
                if notify:
                    yield True

                try:
                    file = open(file.name)
                    log.info('repopened file for tail: %s: because it was moved, truncated, or removed', file)
                except IOError:
                    pass
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


def log_exc(e, msg=None):
    if msg:
        log.error('%s: %s', msg, e)
    else:
        log.error(e)
    for line in traceback.format_exc().split('\n'):
        log.debug('  %s', line)


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


if sys.platform.startswith('linux'):
    boot = boot_lnx()
elif sys.platform.startswith('darwin'):
    boot = boot_bsd()
elif sys.platform.startswith('freebsd'):
    boot = boot_bsd()
else:
    raise OSError('unsupported platform')
log.debug('system boot time: %s', str(datetime.datetime.fromtimestamp(boot)))
