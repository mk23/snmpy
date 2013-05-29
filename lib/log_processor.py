import re
import snmpy

class log_processor(snmpy.plugin):
    def create(self):
        if not len(self.data):
            for k, v in self:
                extra = {
                    'count':  re.compile(v.get('count', r'(?:)')),
                    'reset':  re.compile(v.get('reset', r'(?!)')),
                    'start':  v.get('start', 0),
                    'rotate': v.get('rotate', False),
                }

                self.data['1.%s' % k] = 'string', v['label']
                self.data['2.%s' % k] = 'integer', extra['start'], extra

        self.tail()

    @snmpy.plugin.task
    def tail(self):
        for line in snmpy.plugin.tail(self.conf['object'].format(**self.conf['snmpy_extra']), True):
            if line is True:
                for item in self.data['2.0':]:
                    if self.data[item:'rotate'] and line is True:
                        self.data[item] = self.data[item:'start']
                continue

            for item in self.data['2.0':]:
                count = self.data[item:'count'].search(line)
                if count:
                    self.data[item] = self.data[item:True] + (int(count.group(1)) if len(count.groups()) > 0 else 1)
                    break
                if self.data[item:'reset'].search(line):
                    self.data[item] = self.data[item:'start']
                    break
