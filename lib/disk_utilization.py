import logging
import os
import time
import snmpy
import subprocess

class disk_utilization(snmpy.plugin):
    @snmpy.save
    def script(self):
        os.environ['LC_TIME'] = 'POSIX'

        item = 1
        disk = {}
        date = time.localtime(time.time() - 60 * 20)
        proc = [self.conf.get('sar_command', '/usr/bin/sar'), '-d', '-f', self.conf.get('sysstat_log', '/var/log/sysstat/sa%02d') % date.tm_mday, '-s', time.strftime('%H:%M:00', date)]

        logging.debug('running sar command: %s', ' '.join(proc))
        for line in subprocess.check_output(proc, stderr=open(os.devnull, 'w')).split('\n'):
            logging.debug('line: %s', line)

            part = line.split()
            if len(part) and part[0] != 'Average:' and part[1].startswith('dev'):
                disk[part[1]] = int(float(part[9]))

        for line in open('/proc/diskstats'):
            name = 'dev{}-{}'.format(*line.split()[0:2])
            self.data['1.%d' % item] = 'string', name
            self.data['2.%d' % item] = 'integer', disk.get(name, 0)

            item += 1
