import re
import snmpy
import subprocess

class periodic_cmd(snmpy.plugin):
    def __init__(self, conf, script=False):
        snmpy.plugin.__init__(self, conf, script)

    def len(self):
        return len(self.conf['objects'])

    def key(self, idx):
        return 'string', self.conf['objects'][idx]['label']

    def val(self, idx):
        snmpy.load(self)
        return self.conf['objects'][idx]['type'], self.data[idx - 1]

    def script(self):
        data = [{'value': None, 'label': self.conf['objects'][item]['label'], 'regex': re.compile(self.conf['objects'][item]['regex'])} for item in sorted(self.conf['objects'])]

        for line in subprocess.check_output(self.conf['command'], shell=True, stderr=subprocess.STDOUT).split('\n'):
            for item in xrange(len(data)):
                find = data[item]['regex'].search(line)
                if find:
                    value = find.group(1)
                    data[item]['value'] = unicode(value).isnumeric and int(value) or value

        self.data = [item['value'] for item in data]
        snmpy.save(self)
