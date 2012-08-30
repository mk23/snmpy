import re
import snmpy

class log_processor(snmpy.plugin):
    def create(self):
        for k, v in sorted(self.conf['objects'].items()):
            extra = {
                'count':  re.compile(v['count']),
                'reset':  re.compile(v['reset']) if 'reset' in v else None,
                'start':  int(v['start']) if 'start' in v else 0,
                'rotate': bool(v['rotate']) if 'rotate' in v else False
            }

            self.data['1.%s' % k] = 'string', v['label']
            self.data['2.%s' % k] = 'integer', extra['start'], extra

        self.tail()

    @snmpy.plugin.task
    def tail(self):
        for line in snmpy.plugin.tail(self.conf['file_name'].format(**self.conf['info']), True):
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
                if self.data[item:'reset'] is not None and self.data[item:'reset'].search(line):
                    self.data[item] = self.data[item:'start']
                    break
