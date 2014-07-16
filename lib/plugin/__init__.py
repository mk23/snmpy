import collections
import logging
import pickle
import snmpy.mibgen

LOG = logging.getLogger()


class Meta(type):
    @staticmethod
    def wrapper(func):
        def wrapped(self):
            self.clear()
            func(self)
            self.dump()

        return wrapped

    def __new__(cls, name, bases, attrs):
        if 'update' in attrs:
            attrs['update'] = cls.wrapper(attrs['update'])

        return super(Meta, cls).__new__(cls, name, bases, attrs)


class Plugin(object):
    __metaclass__ = Meta

    def __init__(self, conf):
        self.conf = conf
        self.name = conf['name']

    def clear(self):
        pass

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

            LOG.debug('initialized item: %s (%s)', oidstr, syntax[0])

        self.load()

    def __iter__(self):
        return self.items.__iter__()

    def __getitem__(self, obj):
        return self.items[obj]

    def __setitem__(self, obj, val):
        self.items[obj].value = val


    def load(self):
        if not self.conf['save']:
            return

        try:
            for key, val in pickle.load(open(self.conf['save'])):
                self[key] = val
                LOG.debug('%s: loaded from %s: %s', self.name, self.conf['save'], key)
        except IOError as e:
            snmpy.log_error(e)

    def dump(self):
        if not self.conf['save']:
            return

        try:
            pickle.dump([(k, self[k].value) for k in self], open(self.conf['save'], 'w'))
            LOG.debug('%s: dumped to %s', self.name, self.conf['save'])
        except IOError as e:
            snmpy.log_error(e)


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
            LOG.debug('initialized column: %s (%s)', oidstr, syntax[0])

        self.load()

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

    def load(self):
        if not self.conf['save']:
            return

        try:
            self.rows = pickle.load(open(self.conf['save']))
            LOG.debug('%s: loaded from %s', self.name, self.conf['save'])
        except IOError as e:
            snmpy.log_error(e)

    def dump(self):
        if not self.conf['save']:
            return

        try:
            pickle.dump(self.rows, open(self.conf['save'], 'w'))
            LOG.debug('%s: saved state to %s', self.name, self.conf['save'])
        except IOError as e:
            snmpy.log_error(e)
