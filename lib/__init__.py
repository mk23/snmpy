import logging
import sys
import threading
import traceback

VERSION = '1.0.0'

def task_func(func):
    def decorated(*args, **kwargs):
        t = threading.Thread(target=work_func, args=[func]+list(args), kwargs=kwargs)
        t.daemon = True
        t.start()

    return decorated

def work_func(func, *args, **kwargs):
    try:
        logging.info('starting background task: %s', func.__name__)
        func(*args, **kwargs)
    except Exception as e:
        log_fatal(e)

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
