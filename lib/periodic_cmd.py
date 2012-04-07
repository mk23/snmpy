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

    @snmpy.plugin.load
    def val(self, idx):
        return self.conf['objects'][idx]['type'], self.data[idx - 1]

    @snmpy.plugin.save
    def script(self):
        data = [{'value': 0, 'regex': re.compile(self.conf['objects'][item]['regex'])} for item in sorted(self.conf['objects'])]
        text = subprocess.Popen(self.conf['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]

        for item in xrange(len(data)):
            find = data[item]['regex'].search(text)
            if find:
                data[item]['value'] = find.group(1) if len(find.groups()) > 0 else len(data[item]['regex'].findall(text))

        self.data = [item['value'] for item in data]
