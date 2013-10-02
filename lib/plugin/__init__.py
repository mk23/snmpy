import collections
import snmpy.mibgen

class Plugin(object):
    def __init__(self, conf):
        self.conf = conf
        self.name = conf['name']

    def update(self):
        raise(NotImplementedError('plugin module is missing update() method'))

class ValuePlugin(Plugin):
    class Item(object):
        def __init__(self, oidnum, oidstr, syntax, native, value, **kwargs):
            self.__dict__.update(kwargs)
            self.oidnum = oidnum
            self.oidstr = oidstr
            self.syntax = syntax
            self.native = native
            self.value  = value

    def __init__(self, conf):
        Plugin.__init__(self, conf)

        self.items = collections.OrderedDict()
        for oid in xrange(len(self.conf['items'])):
            obj, cfg = self.conf['items'][oid].items().pop()
            self.items[obj] = ValuePlugin.Item(oid + 1, snmpy.mibgen.get_oidstr(conf['name'], obj), *snmpy.mibgen.get_syntax(cfg['type']), **cfg)

    def __iter__(self):
        return (obj for obj in self.items.keys())

    def __getitem__(self, obj):
        if type(obj) == slice:
            return getattr(self.items[obj.start], obj.stop, obj.step)
        else:
            return self.items[obj]

    def __setitem__(self, obj, val):
        self.items[obj].value = val

class TablePlugin(Plugin):
    def __iter__(self):
        pass
