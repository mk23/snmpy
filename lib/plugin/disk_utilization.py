import datetime
import logging
import os
import snmpy.plugin
import subprocess

class disk_utilization(snmpy.plugin.TablePlugin):
    def __init__(self, conf):
        conf['table'] = [
            {'dev':  'string'},
            {'wait': 'integer'},
            {'util': 'integer'},
        ]

        snmpy.plugin.TablePlugin.__init__(self, conf)

    def update(self):
        os.environ['LC_TIME'] = 'POSIX'

        disk = {}
        date = datetime.datetime.now() - datetime.timedelta(minutes=20)
        comm = [self.conf.get('sar_command', '/usr/bin/sar'), '-d', '-f', self.conf.get('sysstat_log', '/var/log/sysstat/sa%02d') % date.day, '-s', date.strftime('%H:%M:00')]

        logging.debug('running sar command: %s', ' '.join(comm))
        for line in subprocess.check_output(comm, stderr=open(os.devnull, 'w')).split('\n'):
            logging.debug('line: %s', line)

            part = line.split()
            if part and part[0] != 'Average:' and part[1].startswith('dev'):
                disk[part[-9]] = [int(float(part[-3])), int(float(part[-1]))]

        for line in open('/proc/diskstats'):
            name = 'dev{}-{}'.format(*line.split()[0:2])
            self.append([line.split()[2]] + disk.get(name, [0, 0]))
