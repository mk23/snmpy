import bisect
import datetime
import logging
import os
import pickle
import time
import snmpy.util
import sys
import threading

from snmpy.__version__ import __version__

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
    def __init__(self, save=None):
        self.d = {}
        self.l = []
        self.f = save

        self.load()

    def save(self, f=None):
        dst = self.f or f
        if dst:
            try:
                pickle.dump(dict((k, v.get()) for k, v in self.d.items()), open(dst, 'w'))
                logging.debug('saved bucket change to %s', dst)
            except Exception as e:
                snmpy.util.log_exc(e, 'unable to save data file: %s' % dst)

    def load(self, f=None):
        src = self.f or f
        if src:
            try:
                for k, v in pickle.load(open(src)).items():
                    self[k] = v[1] if k in self else v

                logging.info('loaded saved bucket state from: %s', src)
            except Exception as e:
                snmpy.util.log_exc(e, 'unable to load data file: %s' % src)

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
                log.debug('requested just value from key %s', key.start)
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

        self.save()

    def __len__(self):
        return len(self.l)

    def __iter__(self):
        return (str(k) for k in self.l)


class plugin:
    def __init__(self, name, conf=None):
        self.name = name
        self.conf = {} if conf is None else conf

        if self.conf.get('persist') and self.conf.get('snmpy_datadir'):
            self.data = bucket('%s/%s.dat' % (self.conf['snmpy_datadir'], self.name))
        else:
            self.data = bucket()

        if self.conf.get('snmpy_collect'):
            if self.conf.get('script'):
                self.script()
            else:
                logging.debug('%s: skipping collection in non-collector plugin', name)
        else:
            self.create()

    def __iter__(self):
        items = self.conf.get('objects')
        if type(items) in (tuple, list):
            return ((i + 1, items[i]) for i in xrange(len(items)))
        elif isinstance(items, dict):
            return ((k, v) for k, v in sorted(items.items()))

    def create(self):
        pass

    def script(self):
        raise NotImplementedError('%s: plugin cannot run scripts' % self.name)

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

    @staticmethod
    def load(func):
        def decorated(self, *args, **kwargs):
            self.data.load('%s/%s.dat' % (self.conf['snmpy_datadir'], self.name))

            return func(self, *args, **kwargs)
        return decorated

    @staticmethod
    def save(func):
        def decorated(self, *args, **kwargs):
            data_file = '%s/%s.dat' % (self.conf['snmpy_datadir'], self.name)

            threshold = boot if self.conf['script'] == 'boot' else time.time() - self.conf['script']
            code_date = os.stat(sys.modules[self.__class__.__module__].__file__).st_mtime
            run_limit = max(code_date, threshold)

            logging.debug('%s: run limit: %s', self.name, datetime.datetime.fromtimestamp(run_limit))
            if self.conf['snmpy_collect'] == 'force' or not os.path.exists(data_file) or os.stat(data_file).st_mtime < run_limit:
                func(self, *args, **kwargs)
                self.data.save(data_file)
                logging.info('saved result data to %s', data_file)
            else:
                logging.debug('%s: skipping run: recent change', data_file)

        return decorated

    @staticmethod
    def task(func):
        def decorated(*args, **kwargs):
            threading.Thread(target=func, args=args, kwargs=kwargs).start()
            logging.debug('started background task: %s', func.__name__)

        return decorated

    @staticmethod
    def tail(name, notify=False):
        while True:
            try:
                file = open(name)
                file.seek(0, 2) # start at the end
                logging.debug('%s: opened file for tail', name)
                break
            except IOError as e:
                logging.info('%s: cannot open for tail: %s', name, e)
                time.sleep(1)

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
