import httpd
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

    def create_table(self, oid, col):
        if oid not in self.data:
            logging.debug('registering table %s (%d columns)', oid, len(col))
            self.data[oid] = self.snmp.Table(
                oidstr  = oid,
                indexes = [self.snmp.Integer32()],
                columns = [(i + 2, getattr(self.snmp, col[i].syntax)(col[i].value)) for i in range(len(col))]
            )

    def update_value(self, oid, val):
        self.data[oid].update(val)

    def update_table(self, oid, tbl):
        self.data[oid].clear()
        for row in range(len(tbl)):
            cur = self.data[oid].addRow([self.snmp.Integer32(row + 1)])
            for col in tbl[row]:
                cur.setRowCell(col[0], getattr(self.snmp, col[1])(col[2]))

class SnmpyAgent(object):
    def __init__(self, conf, mods):
        self.text = snmpy.mibgen.create_mib(conf, mods)
        self.done = False
        self.conf = conf
        self.mods = mods

        self.start_httpd()
        self.start_agent()
        self.start_snmpd()

    @snmpy.task_func(snmpy.PROCESS_TASK)
    def start_httpd(self):
        @httpd.GET()
        def mib(req, res):
            res.body = self.text

        logging.info('starting http server')
        httpd.Server(self.conf['snmpy_global']['httpd_port'])
        logging.info('WTF WTF WTF')

    @snmpy.task_func(snmpy.THREAD_TASK)
    def start_fetch(self, mod):
        logging.info('began plugin update thread: %s', mod.name)
        while not self.done:
            logging.debug('updating plugin: %s', mod.name)

            mod.update()
            if isinstance(mod, snmpy.plugin.ValuePlugin):
                for item in mod:
                    self.data.update_value(mod[item].oidstr, mod[item].value)
            elif isinstance(mod, snmpy.plugin.TablePlugin):
                self.data.update_table(snmpy.mibgen.get_oidstr(mod.name, 'table'), mod.rows)

            if mod.conf['period'] in ('boot', 'once', '0', 0):
                logging.debug('run-once plugin complete: %s', mod.name)
                break

            time.sleep(mod.conf['period'] * 60)
        logging.info('ended plugin update thread: %s', mod.name)

    def start_agent(self):
        temp = tempfile.NamedTemporaryFile()
        temp.write(self.text)
        temp.flush()

        self.snmp = netsnmpagent.netsnmpAgent(
            AgentName    = self.__class__.__name__,
            MasterSocket = self.conf['snmpy_global']['master_sock'],
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
            columns = [(2, self.snmp.DisplayString())]
        )
        for mod in self.mods:
            mod_row = mtab.addRow([self.snmp.Integer32(mod.conf['snmpy_index'])])
            mod_row.setRowCell(2, self.snmp.DisplayString(mod.name))

            if isinstance(mod, snmpy.plugin.ValuePlugin):
                for item in mod:
                    self.data.create_value(mod[item].syntax, mod[item].oidstr, mod[item].value)
            elif isinstance(mod, snmpy.plugin.TablePlugin):
                self.data.create_table(snmpy.mibgen.get_oidstr(mod.name, 'table'), mod.cols.values())
            self.start_fetch(mod)

    def start_snmpd(self):
        signal.signal(signal.SIGINT,  self.end_agent)
        signal.signal(signal.SIGTERM, self.end_agent)
        signal.signal(signal.SIGCHLD, self.end_agent)

        logging.info('starting snmpy agent')

        self.snmp.start()
        while not self.done:
            self.snmp.check_and_process()

        done = 'child process terminated' if self.done == signal.SIGCHLD else 'process terminated'
        logging.info('stopping snmpy agent: %s', done)

    def end_agent(self, signum, *args):
        self.done = signum
