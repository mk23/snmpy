import snmpy.module
import snmpy.parser
import subprocess


class exec_value(snmpy.module.ValueModule):
    def __init__(self, conf):
        self.item_attributes = {
            'cdef': None,
            'join': '',
        }
        snmpy.module.ValueModule.__init__(self, conf)

    def update(self):
        text = subprocess.Popen(self.conf['object'].format(**self.conf['snmpy_extra']), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for item in self:
            self[item] = snmpy.parser.parse_value(text, self[item])
