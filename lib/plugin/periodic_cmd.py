import __builtin__
import re
import snmpy
import subprocess

class periodic_cmd(snmpy.ValuePlugin):
    def update(self):
        text = subprocess.Popen(self.conf['object'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for indx, (item, conf) in self:
            regex = re.compile(conf['regex'])
            found = regex.findall(text)

            if found:
                if regex.groups == 0:
                    self[item] = len(found)
                elif not conf.has_key('cdef'):
                    self[item] = found[0].strip()
                else:
                    self[item] = getattr(__builtin__, conf['cdef'])([int(i) for i in found])
