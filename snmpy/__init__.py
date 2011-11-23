import os, time, socket, threading
import logging as log

class disabled_plugin:
    def len(self):
        return 1

    def key(self, idx):
        return 'string', 'disabled'

    def val(self, idx):
        return 'string', 'disabled'

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

class configuration:
    @staticmethod
    def modules():
        for k, v in configuration.__dict__.items():
            if type(v) == type(configuration):
                yield k, v

    class disk_utilization:
        index  = 1
        module = 'disk_utilization'

    class rabbitmq_statistics:
        index  = 2
        module = 'rabbitmq_statistics'

    class http_status_counter:
        index   = 3
        module  = 'log_processor'
        logfile = '/var/log/varnish/varnishncsa.log'
        objects = [
            ('HTTP 1XX', r'"[^\s]+ [^\s]+ [^\s]+" 1\d\d'),
            ('HTTP 2XX', r'"[^\s]+ [^\s]+ [^\s]+" 2\d\d'),
            ('HTTP 3XX', r'"[^\s]+ [^\s]+ [^\s]+" 3\d\d'),
            ('HTTP 4XX', r'"[^\s]+ [^\s]+ [^\s]+" 4\d\d'),
            ('HTTP 5XX', r'"[^\s]+ [^\s]+ [^\s]+" 5\d\d'),
        ]

