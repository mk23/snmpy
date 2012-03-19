import json, httplib2, snmpy_plugins
import logging as log

class rabbitmq_statistics:
    data = [
        'uptime',
        'run_queue',
        'processors',
        'proc_total',
        'proc_used',
        'mem_limit',
        'mem_ets',
        'mem_used',
        'mem_binary',
        'fd_used',
        'fd_total',
        'sockets_used',
        'sockets_total',
    ]

    def __init__(self, conf):
        self.http = httplib2.Http()
        self.http.add_credentials('guest', 'guest')

    def len(self):
        return len(self.data)

    def key(self, idx):
        return 'string', self.data[idx - 1]

    def val(self, idx):
        resp, text = self.http.request('http://localhost:55672/api/nodes/rabbit@%s' % snmpy_plugins.role())
        log.debug('received http api response: (%d) %s', resp.status, text)

        stat = json.loads(text)
        log.debug('parsed json stats object: %s', stat)

        return 'integer', int(json.loads(text).get(self.data[idx - 1], 0))
