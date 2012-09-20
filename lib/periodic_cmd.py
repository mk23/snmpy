import __builtin__
import re
import snmpy
import subprocess

class periodic_cmd(snmpy.plugin):
    @snmpy.plugin.load
    def gather(self, key):
        pass

    @snmpy.plugin.save
    def script(self):
        text = subprocess.Popen(self.conf['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for key, val in sorted(self.conf['objects'].items()):
            regex = re.compile(val['regex'])
            found = regex.findall(text)

            if found:
                if regex.groups == 0:
                    self.data['2.%s' % key] = len(found)
                elif not val.has_key('cdef'):
                    self.data['2.%s' % key] = found[0].strip()
                else:
                    self.data['2.%s' % key] = getattr(__builtin__, val['cdef'])([int(i) for i in found])
            else:
                self.data['2.%s' % key] = val.get('init', 0)

    def create(self):
        for key, val in sorted(self.conf['objects'].items()):
            self.data['1.%s' % key] = 'string', val['label']
            self.data['2.%s' % key] = val['type'], val.get('init', 0), {'run': self.gather}
