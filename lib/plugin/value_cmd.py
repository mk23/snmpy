import re
import snmpy.plugin
import subprocess

class value_cmd(snmpy.plugin.ValuePlugin):
    CDEF_FUNCS = {
        'min': min,
        'max': max,
        'len': len,
        'sum': sum,
        'len': len,
        'avg': lambda l: 0 if len(l) == 0 else sum(l) / len(l),
    }

    def __init__(self, conf):
        self.item_attributes = {
            'cdef': None,
            'join': '',
        }
        snmpy.plugin.ValuePlugin.__init__(self, conf)

    def update(self):
        text = subprocess.Popen(self.conf['object'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
        for item in self:
            find = re.findall(self[item].regex, text)

            if find:
                if self[item].cdef in self.CDEF_FUNCS:
                    self[item] = self.CDEF_FUNCS[self[item].cdef](self[item].native(i) for i in find)
                else:
                    self[item] = self[item].native(self[item].join.join(find))
