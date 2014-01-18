import snmpy.parser
import snmpy.plugin
import subprocess

class exec_value(snmpy.plugin.ValuePlugin):
    def __init__(self, conf):
        self.item_attributes = {
            'cdef': None,
            'join': '',
        }
        snmpy.plugin.ValuePlugin.__init__(self, conf)

    def update(self):
        text = subprocess.Popen(self.conf['object'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for item in self:
            self[item] = snmpy.parser.parse_value(text, self[item])
