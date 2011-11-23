#!/usr/bin/env python

import os, sys, signal, traceback
import logging as log

def delete_pid(*args):
    log.debug('removing pidfile: %s', delete_pid.pidfile)
    try:
        os.remove(delete_pid.pidfile)
    finally:
        os._exit(1)

def initialize(opts):
    log.info('initialization started')

    try:
        delete_pid.pidfile = opts.pidfile
        signal.signal(signal.SIGTERM, delete_pid)

        open(opts.pidfile, 'w').write('%d\n' % os.getpid())
        log.debug('wrote pidfile: %s (%d)', opts.pidfile, os.getpid())

        sys.path.insert(0, os.path.dirname(os.path.abspath(opts.modules)))

        root = __import__(os.path.basename(opts.modules))
        log.debug('imported root module')

        conf = [item.strip() for line in open(opts.cfgfile) for item in line.split() if not line.startswith('#') and item.strip()]
        log.debug('read enabled object list: %s', ' '.join(conf))

        mods = {}
        for name, opts in root.configuration.modules():
            if name in conf:
                path = '%s.%s' % (root.__name__, opts.module)

                if path not in sys.modules:
                    __import__(path)
                    log.debug('imported plugin module: %s', path)

                item = sys.modules[path].__dict__[opts.module](opts)
            else:
                item = root.disabled_plugin()

            mods[opts.index] = item
            log.debug('created plugin instance: %s (%s)', name, item.__class__)

    except Exception as e:
        log.error('initialization failed: %s', e)
        for line in traceback.format_exc().split('\n'):
            log.debug('  %s', line)
        os._exit(1)

    log.info('initialization complete')
    return mods

def chop_index(oid, base, next=False):
    top, sep, bot = oid.partition(base)
    log.debug('partitioned oid: %s / %s / %s', top, sep, bot)

    obj = [int(item) for item in bot.lstrip('.').split('.') if item]
    log.debug('requested oid parts: %s', obj)

    ret = tuple(i < len(obj) and obj[i] or int(not next or i != 2) for i in xrange(3))
    log.debug('normalized oid parts: %s', ret)

    if (not next and len(obj) != 3) or ret[1] not in (1, 2):
        raise ValueError('invalid oid: %s' % oid)

    return ret

def enter_loop(base, mods):
    log.info('command loop started')

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', False)
    log.debug('stdout set unbuffered')
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

#TEMPORARY FOR OID MIGRATION
            if oid == '.1.3.6.1.4.1.2021.1123.1.25':
                vtype, vdata = mods[1].val(25)
                print '.1.3.6.1.4.1.2021.1123.2.25'
                print vtype
                print vdata
                continue
#TEMPORARY FOR OID MIGRATION

            tbl, sub, idx = chop_index(oid, base, req == 'getnext')
            if req == 'getnext':
                log.debug('requested table length: %d', mods[tbl].len())
                if idx < mods[tbl].len():
                    idx += 1;
                elif idx == mods[tbl].len():
                    if sub == 1:
                        sub = 2; idx = 1
                    else:
                        tbl += 1; sub = 1; idx = 1
                else:
                    raise ValueError('%s request for %s is out of range' % (req, oid))
            elif tbl > len(mods) or idx > mods[tbl].len():
                raise ValueError('%s request for %s is out of range' % (req, oid))

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
    parser.add_option('-m', '--modules', default='/usr/local/lib/snmpy',
                      help='location for extra snmpy modules')
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
