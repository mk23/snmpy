import snmpy.parser
import snmpy.plugin

class file_table(snmpy.plugin.TablePlugin):
    def update(self):
        text = open(self.conf['object']).read()
        for item in snmpy.parser.parse_table(self.conf['parser'], text):
            self.append(item)
