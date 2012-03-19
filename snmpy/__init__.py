import os, time, socket, threading
import logging as log

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
