import __builtin__
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
        text = subprocess.Popen(self.conf['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]

        self.data = []
        for key, val in sorted(self.conf['objects'].items()):
            regex = re.compile(val['regex'])
            found = regex.findall(text)

            if found:
                if regex.groups == 0:
                    self.data.append(len(found))
                elif not val.has_key('cdef'):
                    self.data.append(found[0])
                else:
                    self.data.append(getattr(__builtin__, val['cdef'])([int(i) for i in found]))
            else:
                self.data.append(0)
