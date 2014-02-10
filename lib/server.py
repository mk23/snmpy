import httpd
import logging
import multiprocessing
import signal
import snmpy
import snmpy.agentx
import snmpy.mibgen
import snmpy.plugin
import tempfile
import time

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

    @snmpy.task_func(snmpy.THREAD_TASK)
    def start_fetch(self, mod):
        logging.info('began plugin update thread: %s', mod.name)
        while not self.done:
            logging.debug('updating plugin: %s', mod.name)

            try:
                mod.update()

                if isinstance(mod, snmpy.plugin.ValuePlugin):
                    for item in mod:
                        self.snmp.replace_value(mod[item].oidstr, mod[item].value)
                elif isinstance(mod, snmpy.plugin.TablePlugin):
                    self.snmp.replace_table(snmpy.mibgen.get_oidstr(mod.name, 'table'), *mod.rows)
            except Exception as e:
                snmpy.log_error(e)

            if mod.conf['period'] in ('boot', 'once', '0', 0):
                logging.debug('run-once plugin complete: %s', mod.name)
                break

            time.sleep(mod.conf['period'] * 60)
        logging.info('ended plugin update thread: %s', mod.name)

    def start_agent(self):
        temp = tempfile.NamedTemporaryFile()
        temp.write(self.text)
        temp.flush()

        self.snmp = snmpy.agentx.AgentX(self.__class__.__name__, temp.name)

        self.snmp.OctetString(
            snmpy.VERSION,
            snmpy.mibgen.get_oidstr(snmpy.mibgen.VERSION_KEY)
        )
        mtbl = self.snmp.Table(
            snmpy.mibgen.get_oidstr(snmpy.mibgen.PLUGINS_KEY, 'table'),
            self.snmp.OctetString()
        )

        for mod in self.mods:
            mtbl.append(mod.name)

            if isinstance(mod, snmpy.plugin.ValuePlugin):
                for item in mod:
                    getattr(self.snmp, mod[item].syntax.object_type)(mod[item].value, mod[item].oidstr)

            elif isinstance(mod, snmpy.plugin.TablePlugin):
                self.snmp.Table(snmpy.mibgen.get_oidstr(mod.name, 'table'), *list(getattr(self.snmp, col.syntax.object_type)() for col in mod.cols.values()))

            self.start_fetch(mod)

    def start_snmpd(self):
        signal.signal(signal.SIGINT,  self.end_agent)
        signal.signal(signal.SIGTERM, self.end_agent)

        logging.info('starting snmpy agent')

        self.snmp.start_subagent()
        while not self.done and multiprocessing.active_children():
            self.snmp.check_and_process()

        logging.info('stopping snmpy agent: %sprocess terminated', 'httpd ' if not multiprocessing.active_children() else '')

    def end_agent(self, signum, *args):
        self.done = True
