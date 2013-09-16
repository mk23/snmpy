import logging
import netsnmpagent
import signal
import snmpy
import tempfile

class SnmpyData(object):
    def __init__(self, snmp):
        self.snmp = snmp
        self.data = {}

    def obj_instance(self, kind):
        return getattr(self.snmp, snmpy.get_syntax(kind))

    def create_value(self, kind, oid, val=None):
        if val is None:
            val = snmpy.get_default(kind)

        if oid not in self.data:
            logging.debug('registering value %s/%s (%s)', oid, snmpy.get_syntax(kind), val)
            self.data[oid] = self.obj_instance(kind)(oidstr=oid, initval=val)

    def create_table(self, kind, oid, col):
        if oid not in self.data:
            logging.debug('registering table %s/%s (%d cols)]', oid, snmpy.get_syntax(kind), len(col))
            self.data[oid] = self.snmp.Table(
                oidstr  = oid,
                indexes = self.obj_instance(kind)(),
                columns = [(i + 2, self.obj_instance(col[i]['kind'])(col[i]['val'])) for i in range(len(col))]
            )

class SnmpyAgent(object):
    def update_value(self, oid, val):
        self.data[oid].update(val)

    def update_table(self, oid, tbl):
        self.data[oid].clear()
    def __init__(self, conf, mods):
        temp = tempfile.NamedTemporaryFile()
        temp.write(snmpy.create_mib(conf, mods))
        temp.flush()

        self.done = False
        self.conf = conf
        self.mods = mods
        self.snmp = netsnmpagent.netsnmpAgent(
            AgentName    = self.__class__.__name__,
            MasterSocket = conf['snmpy_global']['master_sock'],
            MIBFiles     = [temp.name]
        )

        self.make_data()
        self.run_agent()

    def make_data(self):
        self.data = SnmpyData(self.snmp)

        self.snmp.DisplayString(
            oidstr  = snmpy.get_oidstr(snmpy.VERSION_KEY),
            initval = snmpy.VERSION
        )
        mtab = self.snmp.Table(
            oidstr  = snmpy.get_oidstr(snmpy.PLUGINS_KEY, 'table'),
            indexes = [self.snmp.Integer32()],
            columns = [(2, self.snmp.DisplayString('plugin name'))]
        )
        for key, mod in self.mods.items():
            mod_row = mtab.addRow([self.snmp.Integer32(mod.conf['snmpy_index'])])
            mod_row.setRowCell(2, self.snmp.DisplayString(key))

            if 'items' in mod.conf:
                for indx in xrange(len(mod.conf['items'])):
                    item, conf = mod.conf['items'][indx].items().pop()
                    self.mods[key].conf['items'][indx]['oid'] = snmpy.get_oidstr(key, item)

                    self.data.create_value(conf['type'], self.mods[key].conf['items'][indx]['oid'], conf.get('val'))

    def run_agent(self):
        signal.signal(signal.SIGINT, self.end_agent)
        logging.info('starting snmpy agent')

        self.snmp.start()
        while not self.done:
            self.snmp.check_and_process()

        logging.info('stopping snmpy agent')

    def end_agent(self, *args):
        self.done = True

