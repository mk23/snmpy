import logging
import netsnmpagent
import signal
import snmpy
import snmpy.mibgen
import snmpy.plugin
import tempfile
import time

class SnmpyData(object):
    def __init__(self, snmp):
        self.snmp = snmp
        self.data = {}

    def create_value(self, syn, oid, val=None):
        if val is None:
            val = snmpy.mibgen.get_syntax(syn)[2]

        if oid not in self.data:
            logging.debug('registering value %s/%s (%s)', oid, syn, val)
            self.data[oid] = getattr(self.snmp, syn)(oidstr=oid, initval=val)

    def create_table(self, syn, oid, col):
        if oid not in self.data:
            logging.debug('registering table %s/%s (%d cols)]', oid, syn, len(col))
            self.data[oid] = self.snmp.Table(
                oidstr  = oid,
                indexes = getattr(self.snmp, syn)(),
                columns = [(i + 2, getattr(self.snmp, col[i]['syn'])(col[i]['val'])) for i in range(len(col))]
            )

    def update_value(self, oid, val):
        self.data[oid].update(val)

    def update_table(self, oid, tbl):
        self.data[oid].clear()

class SnmpyAgent(object):
    def __init__(self, conf, mods):
        temp = tempfile.NamedTemporaryFile()
        temp.write(snmpy.mibgen.create_mib(conf, mods))
        temp.flush()

        self.done = False
        self.conf = conf
        self.mods = mods
        self.snmp = netsnmpagent.netsnmpAgent(
            AgentName    = self.__class__.__name__,
            MasterSocket = conf['snmpy_global']['master_sock'],
            MIBFiles     = [temp.name]
        )

        self.data = SnmpyData(self.snmp)
        self.snmp.DisplayString(
            oidstr  = snmpy.mibgen.get_oidstr(snmpy.mibgen.VERSION_KEY),
            initval = snmpy.VERSION
        )
        mtab = self.snmp.Table(
            oidstr  = snmpy.mibgen.get_oidstr(snmpy.mibgen.PLUGINS_KEY, 'table'),
            indexes = [self.snmp.Integer32()],
            columns = [(2, self.snmp.DisplayString('plugin name'))]
        )
        for key, mod in self.mods.items():
            mod_row = mtab.addRow([self.snmp.Integer32(mod.conf['snmpy_index'])])
            mod_row.setRowCell(2, self.snmp.DisplayString(key))

            mod.last_run = 0
            if isinstance(mod, snmpy.plugin.ValuePlugin):
                for item in mod:
                    self.data.create_value(mod[item].syntax, mod[item].oidstr, mod[item].value)

        self.start_gather()
        self.start_server()

    @snmpy.task_func
    def start_gather(self):
        while not self.done:
            logging.debug('performing module updates')
            for mod in self.mods.values():
                if mod.conf['period'] in ('boot', 'once') and not mod.last_run or time.time() - mod.last_run > mod.conf['period']:
                    logging.debug('updating module: %s', mod.name)

                    mod.update()
                    mod.last_run = time.time()
                    if isinstance(mod, snmpy.plugin.ValuePlugin):
                        for item in mod:
                            self.data.update_value(mod[item].oidstr, mod[item].value)

            time.sleep(60)

    def start_server(self):
        signal.signal(signal.SIGINT, self.end_agent)
        logging.info('starting snmpy agent')

        self.snmp.start()
        while not self.done:
            self.snmp.check_and_process()

        logging.info('stopping snmpy agent')

    def end_agent(self, *args):
        self.done = True
