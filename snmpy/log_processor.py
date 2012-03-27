import re
import snmpy

class log_processor(snmpy.plugin):
    def __init__(self, conf, script=False):
        snmpy.plugin.__init__(self, conf, script)

    def key(self, idx):
        return 'string', self.data[idx - 1]['label']

    def val(self, idx):
        return 'integer', self.data[idx - 1]['value']

    def worker(self):
        self.data = [{'value':0, 'label': self.conf['objects'][item]['label'], 'regex': re.compile(self.conf['objects'][item]['regex'])} for item in sorted(self.conf['objects'])]
        self.tail()

    @snmpy.task
    def tail(self):
        for line in snmpy.tail(self.conf['logfile']):
            for item in xrange(len(self.data)):
                find = self.data[item]['regex'].search(line)
                if find:
                    self.data[item]['value'] += 1
                    break
