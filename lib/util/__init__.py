import ctypes
import ctypes.util
import datetime
import glob
import logging
import logging.handlers
import os
import sys
import traceback
import yaml

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
                    'snmpy_datadir': args.datadir,
                    'snmpy_collect': args.collect,
                }
                conf[name].update(yaml.load(open(item)))
            except (IOError, yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
                parser.error('cannot parse configuration file: %s' % e)

    return conf

def log_exc(e, msg=None):
    if msg:
        logging.error('%s: %s', msg, e)
    else:
        logging.error(e)
    for line in traceback.format_exc().split('\n'):
        logging.debug('  %s', line)


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

def get_boot():
    if sys.platform.startswith('linux'):
        return boot_lnx()
    elif sys.platform.startswith('darwin'):
        return boot_bsd()
    elif sys.platform.startswith('freebsd'):
        return boot_bsd()

    raise OSError('unsupported platform')
