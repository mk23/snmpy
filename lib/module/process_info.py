import logging
import os
import snmpy.module

LOG = logging.getLogger()

class process_data(object):
    def __init__(self, pid):
        self._f = len(os.listdir('/proc/%s/fd' % pid))
        self._c = open('/proc/%s/cmdline' % pid).read().replace('\0', ' ').strip()
        self._t = os.stat('/proc/%s' % pid).st_mtime
        self._s = {}
        self._l = {}

        for line in open('/proc/%s/status' % pid):
            data = line.split()
            if len(data) > 1:
                self._s[data[0].strip(':').lower()] = data[1]

        for line in open('/proc/%s/limits' % pid):
            if line.startswith('Max'):
                data = map(str.strip, filter(None, line.split('  ')))
                self._l['_'.join(data[0].strip().split()[1:])] = data[1:-1]

    @property
    def pid(self):
        return int(self._s['pid'])
    @property
    def ppid(self):
        return int(self._s['ppid'])
    @property
    def name(self):
        return self._s['name']
    @property
    def args(self):
        return self._c
    @property
    def start_time(self):
        return self._t
    @property
    def fd_open(self):
        return self._f
    @property
    def fd_limit_soft(self):
        return int(self._l['open_files'][0])
    @property
    def fd_limit_hard(self):
        return int(self._l['open_files'][1])
    @property
    def thr_running(self):
        return int(self._s.get('threads', 1))
    @property
    def mem_resident(self):
        return int(self._s.get('vmrss', 0))
    @property
    def mem_swap(self):
        return int(self._s.get('vmswap', 0))
    @property
    def ctx_voluntary(self):
        return int(self._s.get('voluntary_ctxt_switches', 0))
    @property
    def ctx_involuntary(self):
        return int(self._s.get('nonvoluntary_ctxt_switches', 0))


class process_info(snmpy.module.TableModule):
    def __init__(self, conf):
        conf['table'] = [
            {'pid':             {'type': 'integer'}},
            {'ppid':            {'type': 'integer'}},
            {'name':            {'type': 'string'}},
            {'args':            {'type': 'string'}},
            {'start_time':      {'type': 'integer'}},
            {'fd_open':         {'type': 'integer'}},
            {'fd_limit_soft':   {'type': 'integer'}},
            {'fd_limit_hard':   {'type': 'integer'}},
            {'thr_running':     {'type': 'integer'}},
            {'mem_resident':    {'type': 'integer64'}},
            {'mem_swap':        {'type': 'integer64'}},
            {'ctx_voluntary':   {'type': 'counter64'}},
            {'ctx_involuntary': {'type': 'counter64'}},
        ]

        snmpy.module.TableModule.__init__(self, conf)

    def update(self):
        for pid in os.listdir('/proc'):
            if not pid.isdigit():
                continue

            try:
                p = process_data(pid)
                self.append([getattr(p, c) for c in self.cols.keys()])
            except Exception as e:
                snmpy.log_error(e, pid)

        LOG.debug('%d entries updated', len(self.rows))
