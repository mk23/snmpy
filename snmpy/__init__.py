import os
import pickle
import time
import socket
import threading
import logging as log

class SnmpyError(Exception): pass

class plugin:
    def __init__(self, conf, script=False):
        self.conf = conf
        self.init = script and self.script or self.worker

    def script(self):
        if self.conf.get('script', False):
            raise SnmpyError('script enabled, but script() unimplemented')
        return

    def worker(self):
        return

    def len(self):
        return len(self.data)

    def key(self, idx):
        raise SnmpyError('plugin error:  key() unimplemented')

    def val(self, idx):
        raise SnmpyError('plugin error:  val() unimplemented')

def load(item):
    if isinstance(item, plugin):
        item.data = pickle.load(open('%s/%s.dat' % (item.conf['path'], item.conf['name']), 'r'))
    else:
        raise SnmpyError('%s: not a plugin instance')

def save(item):
    if isinstance(item, plugin):
        pickle.dump(item.data, open('%s/%s.dat' % (item.conf['path'], item.conf['name']), 'w'))
    else:
        raise SnmpyError('%s: not a plugin instance')

def tail(file):
    file = open(file)
    file.seek(0, 2) # start at the end
    log.debug('opened file for tail: %s', file.name)

    while True:
        spot = file.tell()
        stat = os.fstat(file.fileno())

        if stat.st_nlink == 0 or spot > stat.st_size:
            try:
                file = open(file.name)
                log.info('file truncated or removed, reopened')
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

def task(func):
    def async_task(*args, **kwargs):
        threading.Thread(target=func, args=args, kwargs=kwargs).start()
        log.debug('started background task: %s', func.__name__)

    return async_task

def role():
    host = socket.gethostname()
    try:
        return dict(line.strip().split()[0:2] for line in open('/etc/rolename')).get(host, host)
    except IOError:
        return host
