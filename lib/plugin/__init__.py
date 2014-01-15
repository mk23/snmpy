import collections
import logging
import snmpy.mibgen

class Plugin(object):
    def __init__(self, conf):
        self.conf = conf
        self.name = conf['name']

    def update(self):
        raise(NotImplementedError('plugin module is missing update() method'))


class PluginItem(object):
    def __init__(self, oidnum, oidstr, syntax, **kwargs):
        self.__dict__.update(kwargs)
        self.oidnum = oidnum
        self.oidstr = oidstr
        self.syntax = syntax
        self.value  = None


class ValuePlugin(Plugin):
    def __init__(self, conf):
        Plugin.__init__(self, conf)

        self.items = collections.OrderedDict()
        self.attrs = getattr(self, 'attrs', {})

        self.attrs['cdef'] = self.attrs.get('cdef', None)
        self.attrs['join'] = self.attrs.get('join', '')
        for oid in range(len(self.conf['items'])):
            obj, cfg = self.conf['items'][oid].items().pop()

            oidstr = snmpy.mibgen.get_oidstr(self.name, obj)
            syntax = snmpy.mibgen.get_syntax(cfg['type'])
            config = self.attrs.copy()
            config.update(cfg)

            self.items[obj] = PluginItem(oid + 1, oidstr, syntax, **config)

            logging.debug('initialized item: %s (%s)', oidstr, syntax[0])

    def __iter__(self):
        return self.items.__iter__()

    def __getitem__(self, obj):
        return self.items[obj]

    def __setitem__(self, obj, val):
        self.items[obj].value = val


class TablePlugin(Plugin):
    def __init__(self, conf):
        Plugin.__init__(self, conf)

        self.rows = []
        self.cols = collections.OrderedDict()
        for oid in range(len(self.conf['table'])):
            obj, cfg = self.conf['table'][oid].items().pop()

            if not isinstance(cfg, dict):
                cfg = {'type': cfg}

            oidstr = snmpy.mibgen.get_oidstr(self.name, obj)
            syntax = snmpy.mibgen.get_syntax(cfg['type'])

            self.cols[obj] = PluginItem(oid + 1, oidstr, syntax, **cfg)
            logging.debug('initialized column: %s (%s)', oidstr, syntax[0])

    def __iter__(self):
        return self.rows.__iter__()

    def clear(self):
        self.rows = []

    def append(self, data):
        self.rows.append([])
        if type(data) in (list, tuple):
            for col in self.cols.values():
                self.rows[-1].append(col.syntax.native_type(data[col.oidnum - 1]))
        elif isinstance(data, dict):
            for key, col in self.cols.items():
                self.rows[-1].append(col.syntax.native_type(data[key]))
