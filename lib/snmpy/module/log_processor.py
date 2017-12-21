import logging
import os
import snmpy.module
import snmpy.parser
import time

LOG = logging.getLogger()


class log_processor(snmpy.module.ValueModule):
    def __init__(self, conf):
        snmpy.module.ValueModule.__init__(self, conf)

        self.tail(self.conf['object'].format(**self.conf['snmpy_extra']))

    def update(self):
        pass

    @snmpy.task_func(snmpy.THREAD_TASK)
    def tail(self, name):
        while True:
            try:
                data = open(name)
                data.seek(0, 2) # start at the end
                LOG.debug('%s: opened file for tail', name)
                break
            except IOError as e:
                LOG.info('%s: cannot open for tail: %s', name, e)
                time.sleep(5)
            except Exception as e:
                snmpy.log_error(e)

        while True:
            spot = data.tell()
            stat = os.fstat(data.fileno())

            if os.stat(name).st_ino != stat.st_ino or stat.st_nlink == 0 or spot > stat.st_size:
                try:
                    data = open(name)
                    LOG.info('%s: repopened for tail: moved, truncated, or removed', name)
                except IOError as e:
                    LOG.info('%s: cannot open for tail: %s', name, e)
            elif spot != stat.st_size:
                text = data.read(stat.st_size - spot)
                while True:
                    indx = text.find('\n')
                    if indx == -1:
                        data.seek(-len(text), 1)
                        break
                    line = text[0:indx]
                    text = text[indx + 1:]

                    for item in self:
                        self[item] = snmpy.parser.parse_value(line, self[item], ignore=True)

            time.sleep(1)
