import re, snmpy

class log_processor:
    def __init__(self, conf):
        self.data = [{'value':0, 'label': conf['objects'][item]['label'], 'regex': re.compile(conf['objects'][item]['regex'])} for item in sorted(conf['objects'])]
        self.proc(conf['logfile'])

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
