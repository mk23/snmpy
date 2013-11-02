import snmpy.parser
import snmpy.plugin

class table_file(snmpy.plugin.TablePlugin):
    def update(self):
        self.clear()

        text = open(self.conf['object']).read()
        for item in snmpy.parser.parse_table(self.conf['parser'], text):
            self.append(item)
