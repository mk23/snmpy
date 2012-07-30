import re
import snmpy

class log_processor(snmpy.plugin):
    def create(self):
        for k, v in sorted(self.conf['objects'].items()):
            self.data['1.%s' % k] = 'string', v['label']
            self.data['2.%s' % k] = 'integer', 0, {'re': re.compile(v['regex'])}

        self.tail()

    @snmpy.plugin.task
    def tail(self):
        for line in snmpy.tail(self.conf['logfile']):
            for item in self.data['2.0':]:
                find = self.data[item:'re'].search(line)
                if find:
                    self.data[item] = self.data[item:True] + (int(find.group(1)) if len(find.groups()) > 0 else 1)
                    break
