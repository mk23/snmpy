import logging
import sys
import traceback
from snmpy.mibgen import *
from snmpy.plugin import *
from snmpy.server import *

VERSION = '1.0.0'

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
