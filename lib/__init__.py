import ctypes.util
import logging
import multiprocessing
import os
import signal
import threading
import traceback

LOG = logging.getLogger()

VERSION = '2.0.13-upstream1'

THREAD_TASK  = threading.Thread
PROCESS_TASK = multiprocessing.Process

def task_func(kind=THREAD_TASK):
    def wrapper(func):
        def wrapped(*args, **kwargs):
            t = kind(target=work_func, args=[func, kind == PROCESS_TASK]+list(args), kwargs=kwargs)
            t.daemon = True
            t.start()
        return wrapped
    return wrapper

def work_func(func, proc, *args, **kwargs):
    try:
        LOG.info('starting background task: %s', func.__name__)
        if proc:
            libc = ctypes.CDLL(ctypes.util.find_library('libc'))
            libc.prctl(1, signal.SIGTERM)
        func(*args, **kwargs)
    except Exception as e:
        log_fatal(e)

def log_error(e, msg=None):
    if msg:
        LOG.error('%s: %s', msg, e)
    else:
        LOG.error(e)

    for line in traceback.format_exc().split('\n'):
        LOG.debug('  %s', line)

def log_fatal(item, prio='error', exit=1):
    if isinstance(item, Exception):
        log_error(item)
    else:
        vars(LOG).get(prio, 'error')(item)

    if exit is not None:
        os._exit(exit)
