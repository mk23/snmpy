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

    def worker(self):
        pass

    @staticmethod
    def load(func):
        def load_func(self, *args, **kwargs):
            data_file = '%s/%s.dat' % (self.conf['path'], self.conf['name'])
            self.data = pickle.load(open(data_file, 'r'))
            log.debug('loaded saved data from %s' % data_file)

            return func(self, *args, **kwargs)
        return load_func

    @staticmethod
    def save(func):
        def save_func(self, *args, **kwargs):
            data_file = '%s/%s.dat' % (self.conf['path'], self.conf['name'])
            if not os.path.exists(data_file) or os.stat(data_file).st_mtime < time.time() - int(self.conf['script']):
                func(self, *args, **kwargs)
                pickle.dump(self.data, open('%s/%s.dat' % (self.conf['path'], self.conf['name']), 'w'))
                log.info('saved result data to %s' % data_file)
            else:
                log.debug('%s: skipping run: recent change', data_file)

            return func(self, *args, **kwargs)
        return save_func

    def len(self):
        return len(self.data)

    def key(self, idx):
        raise SnmpyError('plugin error:  key() unimplemented')

    def val(self, idx):
        raise SnmpyError('plugin error:  val() unimplemented')


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
