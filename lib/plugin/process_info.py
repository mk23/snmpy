import logging
import os
import snmpy.plugin

class process_info(snmpy.plugin.TablePlugin):
    def __init__(self, conf):
        conf['table'] = [
            {'pid':             {'type': 'integer',   'func': lambda s, l, f: int(self.parser(s, 'Pid'))}},
            {'ppid':            {'type': 'integer',   'func': lambda s, l, f: int(self.parser(s, 'PPid'))}},
            {'name':            {'type': 'string',    'func': lambda s, l, f: self.parser(s, 'Name')}},
            {'fd_open':         {'type': 'integer',   'func': lambda s, l, f: f}},
            {'fd_limit_soft':   {'type': 'integer',   'func': lambda s, l, f: int(self.parser(l, 'Max open files', 3))}},
            {'fd_limit_hard':   {'type': 'integer',   'func': lambda s, l, f: int(self.parser(l, 'Max open files', 4))}},
            {'thr_running':     {'type': 'integer',   'func': lambda s, l, f: int(self.parser(s, 'Threads'))}},
            {'mem_resident':    {'type': 'integer64', 'func': lambda s, l, f: int(self.parser(s, 'VmRSS'))}},
            {'mem_swap':        {'type': 'integer64', 'func': lambda s, l, f: int(self.parser(s, 'VmSwap'))}},
            {'ctx_voluntary':   {'type': 'counter64', 'func': lambda s, l, f: int(self.parser(s, 'voluntary_ctxt_switches'))}},
            {'ctx_involuntary': {'type': 'counter64', 'func': lambda s, l, f: int(self.parser(s, 'nonvoluntary_ctxt_switches'))}},
        ]

        snmpy.plugin.TablePlugin.__init__(self, conf)

    def update(self):
        for pid in os.listdir('/proc'):
            try:
                s = open('/proc/%s/status' % pid).readlines()
                l = open('/proc/%s/limits' % pid).readlines()
                f = len(os.listdir('/proc/%s/fd' % pid))

                self.append([c.func(s, l, f) for c in self.cols.values()])
            except:
                pass

        logging.debug('%d entries updated', len(self.rows))

    def parser(self, text, key, col=1, sep=None):
        return [l.split(sep)[col] for l in text if l.startswith(key)][0]
