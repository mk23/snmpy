#!/usr/bin/env python

import os, sys, signal, traceback, ConfigParser
import logging as log

def delete_pid(*args):
    log.debug('removing pidfile: %s', delete_pid.pidfile)
    try:
        os.remove(delete_pid.pidfile)
    finally:
        os._exit(1)

def build_conf(items):
    conf = {'objects':{}}
    for item in items:
        key = item[0].split('.')
        if unicode(key[-1]).isnumeric():
            if conf['objects'].has_key(key[-1]):
                conf['objects'][key[-1]][key[0]] = item[1]
            else:
                conf['objects'][key[-1]] = {key[0]: item[1]}
        else:
            conf[item[0]] = item[1]

    return conf

def initialize(opts):
    log.info('initialization started')

    try:
        delete_pid.pidfile = opts.pidfile
        signal.signal(signal.SIGTERM, delete_pid)

        open(opts.pidfile, 'w').write('%d\n' % os.getpid())
        log.debug('wrote pidfile: %s (%d)', opts.pidfile, os.getpid())

        conf = ConfigParser.SafeConfigParser()
        conf.read(opts.cfgfile)

        mods = {}
        for name in conf.sections():
            if name == 'snmpy_global':
                continue

            base = conf.get(name, 'module')
            full = 'snmpy.%s' % base

            if full not in sys.modules:
                __import__(full)
                log.debug('importing module %s', full)

            item = sys.modules[full].__dict__[base](build_conf(conf.items(name)))
            mods[conf.getint(name, 'index')] = item
            log.debug('created plugin %s instance of %s (%s)', name, base, item)
    except Exception as e:
        log.error('initialization failed: %s', e)
        for line in traceback.format_exc().split('\n'):
            log.debug('  %s', line)
        os._exit(1)

    log.info('initialization complete')
    return mods

def enter_loop(base, mods):
    log.info('command loop started')

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', False)
    log.debug('stdout set unbuffered')

    keys = sorted(mods)
    while True:
        try:
            req = sys.stdin.readline().strip()
            if req == 'PING':
                print 'PONG'
                continue
            if req == 'set':
                sys.stdin.readline() # type
                sys.stdin.readline() # value
                print 'not-writable'
                continue
            if req != 'get' and req != 'getnext':
                raise ValueError('invalid request: %s' % req.strip())

            oid = sys.stdin.readline().strip()
            log.info('received %s request for %s', req, oid)

            top, sep, bot = oid.partition(base)
            log.debug('partitioned oid: %s / %s / %s', top, sep, bot)

            obj = [int(prt) for prt in bot.lstrip('.').split('.') if prt]
            log.debug('requested oid parts: %s', obj)

            if req == 'get':
                if len(obj) == 3 and obj[1] in (1, 2) and obj[0] in keys and obj[2] <= mods[obj[0]].len():
                    tbl, sub, idx = obj
                else:
                    raise ValueError('invalid oid: %s' % oid)
            elif req == 'getnext':
                if len(obj) == 0:
                    idx = 1
                    sub = 1
                    tbl = min(keys)
                elif len(obj) == 1:
                    idx = 1
                    sub = 1
                    if obj[0] in keys:
                        tbl = obj[0]
                    elif obj[0] <= min(keys):
                        tbl = min(i for i in keys if i >= obj[0])
                    else:
                        raise ValueError('invalid oid: %s' % oid)
                elif len(obj) == 2:
                    if obj[0] in keys:
                        idx = 1
                        tbl = obj[0]
                        if obj[1] in (1, 2):
                            sub = obj[1]
                        else:
                            raise ValueError('invalid oid: %s' % oid)
                    elif obj[0] <= min(keys):
                        idx = 1
                        sub = 1
                        tbl = min(i for i in keys if i >= obj[0])
                    else:
                        raise ValueError('invalid oid: %s' % oid)
                elif len(obj) == 3:
                    if obj[0] in keys:
                        tbl = obj[0]
                        if obj[1] in (1, 2):
                            sub = obj[1]
                        else:
                            raise ValueError('invalid oid: %s' % oid)
                        if obj[2] < mods[tbl].len():
                            idx = obj[2] + 1
                        else:
                            idx = 1
                            if sub == 1:
                                sub = 2
                            elif tbl + 1 <= min(keys):
                                sub = 1
                                tbl = min(i for i in keys if i >= obj[0])
                            else:
                                raise ValueError('invalid oid: %s' % oid)
                    elif obj[0] <= min(keys):
                        idx = 1
                        sub = 1
                        tbl = min(i for i in keys if i >= obj[0])
                    else:
                        raise ValueError('invalid oid: %s' % oid)

            vtype, vdata = sub == 1 and mods[tbl].key(idx) or mods[tbl].val(idx)
            log.debug('received plugin data: %s/%s', vtype, vdata)

            print '%s.%d.%d.%d' % (base, tbl, sub, idx)
            print vtype
            print vdata

        except KeyboardInterrupt:
            log.info('caught user interrupt, exiting')
            delete_pid()
        except Exception as e:
            log.error(e)
            for line in traceback.format_exc().split('\n'):
                log.debug('  %s', line)
            print 'NONE'

    log.info('command loop complete')

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(usage='%prog [options]')
    parser.add_option('-b', '--baseoid', default='.1.3.6.1.4.1.2021.1123',
                      help='base oid as configured in pass_persist by snmpd.conf')
    parser.add_option('-f', '--cfgfile', default='/etc/snmpy.cfg',
                      help='location for the snmpy module configuration')
    parser.add_option('-l', '--logfile', default=None,
                      help='log file destination path, implies --verbose')
    parser.add_option('-p', '--pidfile', default='/var/run/snmpy/agent.pid',
                      help='pid file destination path')
    parser.add_option('-k', '--killpid', default=False, action='store_true',
                      help='kill existing process saved in pidfile if exists')
    parser.add_option('-v', '--verbose', default=False, action='store_true',
                      help='enable basic logging')
    parser.add_option('-d', '--debug', default=False, action='store_true',
                      help='enable debug logging')

    opts, args = parser.parse_args()
    if opts.logfile or opts.verbose or opts.debug:
        log.basicConfig(format='%(asctime)s.%(msecs)03d - %(funcName)10s:%(lineno)-3d - %(levelname)10s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=opts.debug and log.DEBUG or log.INFO, filename=opts.logfile)
        log.info('logging started')
    else:
        log.disable(log.CRITICAL)

    if opts.killpid:
        try:
            os.kill(int(open(opts.pidfile).readline()), signal.SIGTERM)
            sys.exit(0)
        except:
            sys.exit(1)
    elif os.path.exists(opts.pidfile):
        log.debug('%s exists' % opts.pidfile)
        try:
            os.kill(int(open(opts.pidfile).readline()), 0)
            log.error('snmpy process is running')
        except OSError:
            os.remove(opts.pidfile)
            log.debug('removed orphaned pidfile')
        else:
            sys.exit(1)

    mods = initialize(opts)
    enter_loop(opts.baseoid, mods)
