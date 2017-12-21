import snmpy.module
import snmpy.parser


class file_table(snmpy.module.TableModule):
    def update(self):
        text = open(self.conf['object'].format(**self.conf['snmpy_extra'])).read()
        for item in snmpy.parser.parse_table(self.conf['parser'], text):
            self.append(item)
