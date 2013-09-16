import __builtin__
import re
import snmpy
import subprocess

class periodic_cmd(snmpy.Plugin):
    def update(self):
        text = subprocess.Popen(self.conf['exec'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        print text
        for indx in xrange(len(self.conf['items'])):
            item, conf = self.conf['items'][indx].items().pop()
            regex = re.compile(conf['regex'])
            found = regex.findall(text)

            if found:
                if regex.groups == 0:
                    self.conf['items'][indx][item]['val'] = len(found)
                elif not conf.has_key('cdef'):
                    self.conf['items'][indx][item]['val'] = found[0].strip()
                else:
                    self.conf['items'][indx][item]['val'] = getattr(__builtin__, conf['cdef'])([int(i) for i in found])
