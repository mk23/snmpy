import os
import time
import snmpy
import subprocess
import logging as log

class disk_utilization(snmpy.plugin):
    def __init__(self, conf, script=False):
        snmpy.plugin.__init__(self, conf, script)

    def key(self, idx):
        return 'string', self.data[idx - 1]

    def val(self, idx):
        ts = time.localtime(time.time() - 60 * 20)

        results = {}
        command = ['/usr/bin/sar', '-d', '-f', '/var/log/sysstat/sa%02d' % ts.tm_mday, '-s', time.strftime('%H:%M:00', ts)]
        log.debug('running command: %s', ' '.join(command))

        for line in subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].split('\n'):
            line = line.split()
            log.debug('line: %s', line)
            if len(line) and line[0] != 'Average:' and line[1].startswith('dev'):
                results[line[1]] = int(float(line[9]))

        log.debug('results: %s', results)
        return 'integer', results.get(self.data[idx - 1], 0)

    def worker(self):
        os.environ['LC_TIME'] = 'POSIX'
        self.data = ['dev%s-%s' % tuple(line.split()[0:2]) for line in open('/proc/diskstats')]
