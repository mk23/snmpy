import re, snmpy
import logging as log

class log_processor:
    def __init__(self, conf):
        self.data = ({'value':0, 'label': item[0], 'regex': re.compile(item[1])} for item in conf.objects)
        self.proc(conf.logfile)

    def len(self):
        return len(self.data)

    def key(self, idx):
        return 'string', self.data[idx - 1]['label']

    def val(self, idx):
        return 'integer', self.data[idx - 1]['value']

    @snmpy.task
    def proc(self, file):
        for line in snmpy.tail(file):
            for item in xrange(len(self.data)):
                find = self.data[item]['regex'].search(line)
                if find:
                    self.data[item]['value'] += 1
                    break
