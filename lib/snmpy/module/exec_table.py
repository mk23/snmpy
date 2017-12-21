import snmpy.module
import snmpy.parser
import subprocess


class exec_table(snmpy.module.TableModule):
    def update(self):
        text = subprocess.Popen(self.conf['object'].format(**self.conf['snmpy_extra']), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for item in snmpy.parser.parse_table(self.conf['parser'], text):
            self.append(item)
