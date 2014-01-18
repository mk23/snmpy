import snmpy.parser
import snmpy.plugin
import subprocess

class exec_table(snmpy.plugin.TablePlugin):
    def update(self):
        self.clear()

        text = subprocess.Popen(self.conf['object'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for item in snmpy.parser.parse_table(self.conf['parser'], text):
            self.append(item)
