import re
import snmpy

class proc_query(snmpy.plugin):
    def create(self):
        for key, val in sorted(self.conf['objects'].items()):
            extra = {
                'run':   self.gather,
                'start': val.get('start', 0),
                'regex': re.compile(val['regex']),
            }

            self.data['1.%s' % key] = 'string', val['label']
            self.data['2.%s' % key] = val['type'], val.get('start', 0), extra

    def gather(self, obj):
        text = open('/proc/%s' % self.conf['proc_entry'])
        find = self.data[obj:'regex'].findall(text)
        if find:
            if self.data[obj:'regex'].groups == 0:
                self.data[obj] = len(find)
            else:
                self.data[obj] = find[0].strip()
        else:
            self.data[obj] = self.data[obj:'start']
