import snmpy

class Plugin(object):
    def __init__(self, conf):
        self.conf = conf
        self.name = conf['name']

    def update(self):
        raise(NotImplementedError('plugin module is missing update() method'))

class ValuePlugin(Plugin):
    def __init__(self, conf):
        Plugin.__init__(self, conf)

        for oid in xrange(len(self.conf['items'])):
            obj, cfg = self.conf['items'][oid].items().pop()
            self.conf['items'][oid][obj]['oidnum'] = oid + 1
            self.conf['items'][oid][obj]['oidstr'] = '%s.%d' % (snmpy.get_oidstr(conf['name'], obj), oid + 1)
            self.conf['items'][oid][obj]['syntax'] = snmpy.get_syntax(cfg['type'])

        self._obj = dict((o, c['oidnum'] - 1) for o, c in self)

    def __iter__(self):
        return (item.items().pop() for item in self.conf['items'])

    def __getitem__(self, obj):
        if type(obj) == slice:
            return self.conf['items'][self._obj[obj.start]][obj.stop]
        else:
            return self.conf['items'][self._obj[obj]]['value']

    def __setitem__(self, obj, val):
        self.conf['items'][self._obj[obj]]['value'] = val

class TablePlugin(Plugin):
    def __iter__(self):
        pass
