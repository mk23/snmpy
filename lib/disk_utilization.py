import os
import time
import snmpy
import subprocess
import logging as log

class disk_utilization(snmpy.plugin):
    def gather(self, obj):
        ts = time.localtime(time.time() - 60 * 20)

        command = ['/usr/bin/sar', '-d', '-f', '/var/log/sysstat/sa%02d' % ts.tm_mday, '-s', time.strftime('%H:%M:00', ts)]
        log.debug('running command: %s', ' '.join(command))

        for line in subprocess.check_output(command, stderr=open('/dev/null', 'w')).split('\n'):
            log.debug('line: %s', line)

            line = line.split()
            if len(line) and line[0] != 'Average:' and line[1] in self.dmap:
                self.data[self.dmap[line[1]]] = int(float(line[9]))

    def create(self):
        os.environ['LC_TIME'] = 'POSIX'
        self.dmap = {}

        item = 1
        for line in open('/proc/diskstats'):
            name = 'dev%s-%s' % tuple(line.split()[0:2])
            self.dmap[name] = '2.%d' % item

            self.data['1.%d' % item] = 'string', name
            self.data['2.%d' % item] = 'integer', 0, {'run': self.gather}
            item += 1
