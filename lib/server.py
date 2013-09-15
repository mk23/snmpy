import logging
import netsnmpagent
import signal
import snmpy.mib_gen
import tempfile

class SnmpyAgent(object):
    def __init__(self, conf, mods):
        temp = tempfile.NamedTemporaryFile()
        temp.write(snmpy.mib_gen.create_mib(conf, mods))
        temp.flush()

        self.done = False
        self.conf = conf
        self.mods = mods
        self.snmp = netsnmpagent.netsnmpAgent(
            AgentName    = 'SnmpyAgent',
            MasterSocket = conf['snmpy_global']['master_sock'],
            MIBFiles     = [temp.name]
        )
        self.snmp.DisplayString(
            oidstr  = 'SNMPY-MIB::snmpyInfoVersion',
            initval = snmpy.VERSION
        )
        mtab = self.snmp.Table(
            oidstr  = 'SNMPY-MIB::snmpyInfoPluginsTable',
            indexes = [self.snmp.Integer32()],
            columns = [(2, self.snmp.DisplayString('plugin name'))]
        )
        for key, mod in mods.items():
            row = mtab.addRow([self.snmp.Integer32(mod.conf['snmpy_index'])])
            row.setRowCell(2, self.snmp.DisplayString(key))

    def run_agent(self):
        signal.signal(signal.SIGINT, self.end_agent)
        logging.info('starting snmpy agent')

        self.snmp.start()
        while not self.done:
            self.snmp.check_and_process()

        logging.info('stopping snmpy agent')

    def end_agent(self, *args):
        self.done = True


class SnmpyData(object):
    def __init__(self, snmp):
        self.snmp = snmp
        self.data = {}

    def obj_instance(self, kind):
        return getattr(self.sever, snmpy.mib_gen.get_syntax(kind))

    def create_value(self, kind, oid, val):
        if oid not in self.data:
            self.data[oid] = self.obj_instance(kind)(oidstr=oid, initval=val)

    def create_table(self, kind, oid, col):
        if oid not in self.data:
            self.data[oid] = self.snmp.Table(
                oidstr=oid,
                indexes=self.obj_instance(kind)(),
                columns=[(i + 2, self.obj_instance(col[i]['kind'])(col[i]['val'])) for i in range(len(col))]
            )

    def update_value(self, oid, val):
        self.data[oid].update(val)

    def update_table(self, oid, tbl):
        self.data[oid].clear()
