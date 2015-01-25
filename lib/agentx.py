#!/usr/bin/python

import ctypes.util
import sys

lib_c   = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))
lib_nsh = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmphelpers'))
lib_nsa = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmpagent'))
chk_fun = [
    'netsnmp_create_watcher_info',
    'netsnmp_register_watched_instance',
    'netsnmp_create_handler_registration',
    'netsnmp_create_table_data_set',
    'netsnmp_table_dataset_add_index',
    'netsnmp_table_dataset_add_row',
    'netsnmp_table_set_add_default_row',
    'netsnmp_register_table_data_set',
    'netsnmp_table_data_set_create_row_from_defaults',
    'netsnmp_set_row_column',
    'netsnmp_table_dataset_remove_and_delete_row',
    'netsnmp_check_outstanding_agent_requests',
    'snmp_select_info',
    'snmp_read',
    'snmp_timeout',
    'snmp_store_if_needed',
    'run_alarms',
]

if not hasattr(lib_nsh, 'read_objid'):
    lib_nsh = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmp'))

for f in chk_fun:
    if not hasattr(lib_nsh, f):
            setattr(lib_nsh, f, getattr(lib_nsa, f))

# From sys/time.h
class timeval(ctypes.Structure):
    pass
timeval._fields_ = (
    ('tv_sec', ctypes.c_long),
    ('tv_usec', ctypes.c_long),
)

# From sys/select.h
FD_SETSIZE      = 1024

class fd_set(ctypes.Structure):
    pass
fd_set._fields_ = (
    ('fds_bits', ctypes.c_long * (FD_SETSIZE / (8 * ctypes.sizeof(ctypes.c_long)))),
)

lib_c.select.restype  = ctypes.c_int
lib_c.select.argtypes = (
    ctypes.c_int,               # nfds
    ctypes.POINTER(fd_set),     # readfds
    ctypes.POINTER(fd_set),     # writefds
    ctypes.POINTER(fd_set),     # exceptfds
    ctypes.POINTER(timeval),    # timeout
)

# From net-snmp/library/asn1.h and net-snmp/snmp_impl.h
ASN_BOOLEAN     = 0x01
ASN_INTEGER     = 0x02
ASN_BIT_STR     = 0x03
ASN_OCTET_STR   = 0x04
ASN_NULL        = 0x05
ASN_OBJECT_ID   = 0x06
ASN_SEQUENCE    = 0x10
ASN_SET         = 0x11

ASN_UNIVERSAL   = 0x00
ASN_APPLICATION = 0x40
ASN_CONTEXT     = 0x80
ASN_PRIVATE     = 0xC0

ASN_IPADDRESS   = ASN_APPLICATION | 0
ASN_COUNTER     = ASN_APPLICATION | 1
ASN_GAUGE       = ASN_APPLICATION | 2
ASN_UNSIGNED    = ASN_APPLICATION | 2
ASN_TIMETICKS   = ASN_APPLICATION | 3
ASN_OPAQUE      = ASN_APPLICATION | 4
ASN_COUNTER64   = ASN_APPLICATION | 6
ASN_FLOAT       = ASN_APPLICATION | 8
ASN_DOUBLE      = ASN_APPLICATION | 9
ASN_INTEGER64   = ASN_APPLICATION | 10
ASN_UNSIGNED64  = ASN_APPLICATION | 11

MAX_OID_LEN     = 128

class counter64(ctypes.Structure):
    pass
counter64._fields_ = (
    ('high', ctypes.c_ulong),
    ('low',  ctypes.c_ulong),
)

# From net-snmp/library/parse.h
lib_nsa.netsnmp_init_mib.restype  = None
lib_nsa.netsnmp_init_mib.argtypes = (
)

lib_nsa.read_mib.restype  = ctypes.c_void_p  # unsed ret val: struct tree *
lib_nsa.read_mib.argtypes = (
    ctypes.c_char_p,    # filename
)

# From net-snmp/library/mib_api.h
lib_nsh.read_objid.restype  = ctypes.c_int
lib_nsh.read_objid.argtypes = (
    ctypes.c_char_p,    # argv
    ctypes.POINTER(ctypes.c_ulong),     # root
    ctypes.POINTER(ctypes.c_size_t),    # rootlen
)

# From net-snmp/library/snmp_api.h
class netsnmp_vardata(ctypes.Union):
    pass
netsnmp_vardata._fields_ = (
    ('voidp',     ctypes.c_void_p),
    ('integer',   ctypes.POINTER(ctypes.c_long)),
    ('string',    ctypes.POINTER(ctypes.c_ubyte)),
    ('objid',     ctypes.POINTER(ctypes.c_ulong)),
    ('bitstring', ctypes.POINTER(ctypes.c_ubyte)),
    ('counter64', ctypes.POINTER(counter64)),
)

class netsnmp_variable_list(ctypes.Structure):
    pass
netsnmp_variable_list._fields_ = (
   ('next_variable', ctypes.POINTER(netsnmp_variable_list)),
   ('name',          ctypes.POINTER(ctypes.c_ulong)),
   ('name_length',   ctypes.c_size_t),
   ('type',          ctypes.c_ubyte),
   ('val',           netsnmp_vardata),
   ('val_len',       ctypes.c_size_t),
   ('oid',           ctypes.c_ulong * MAX_OID_LEN),
   ('buf',           ctypes.c_ubyte * 40),
   ('data',          ctypes.c_void_p),
   ('dataFreeHook',  ctypes.c_void_p), # unused fun ptr: void (*dataFreeHook)(void *)
   ('index',         ctypes.c_int),
)

lib_nsa.init_snmp.restype  = ctypes.c_int
lib_nsa.init_snmp.argtypes = (
    ctypes.c_char_p,    # type
)

lib_nsa.snmp_varlist_add_variable.restype  = ctypes.POINTER(netsnmp_variable_list)
lib_nsa.snmp_varlist_add_variable.argtypes = (
    ctypes.POINTER(ctypes.POINTER(netsnmp_variable_list)),  # varlist
    ctypes.POINTER(ctypes.c_ulong),                         # name
    ctypes.c_size_t,    # name_length
    ctypes.c_ubyte,     # type
    ctypes.c_void_p,    # value
    ctypes.c_size_t,    # len
)

# From net-snmp/agent/agent_handler.h
class netsnmp_mib_handler(ctypes.Structure):
    pass
netsnmp_mib_handler._fields_ = (
    ('handler_name',   ctypes.c_char_p),
    ('myvoid',         ctypes.c_void_p),
    ('flags',          ctypes.c_int),
    ('access_method',  ctypes.c_void_p), # unused fun ptr: int (*access_method) (struct netsnmp_mib_handler_s *, struct netsnmp_handler_registration_s *, struct netsnmp_agent_request_info_s *, struct netsnmp_request_info_s *);
    ('data_free',      ctypes.c_void_p), # unused fun ptr: void (*data_free)(void *myvoid);
    ('next',           ctypes.POINTER(netsnmp_mib_handler)),
    ('prev',           ctypes.POINTER(netsnmp_mib_handler)),
)

class netsnmp_handler_registration(ctypes.Structure):
    pass
netsnmp_handler_registration._fields_ = (
    ('handlerName',    ctypes.c_char_p),
    ('contextName',    ctypes.c_char_p),
    ('rootoid',        ctypes.POINTER(ctypes.c_ulong)),
    ('rootoid_len',    ctypes.c_size_t),
    ('handler',        ctypes.POINTER(netsnmp_mib_handler)),
    ('modes',          ctypes.c_int),
    ('priority',       ctypes.c_int),
    ('range_subid',    ctypes.c_int),
    ('range_ubound',   ctypes.c_ulong),
    ('timeout',        ctypes.c_int),
    ('global_cacheid', ctypes.c_int),
    ('my_reg_void',    ctypes.c_void_p),
)

lib_nsh.netsnmp_create_handler_registration.restype = ctypes.POINTER(netsnmp_handler_registration)
lib_nsh.netsnmp_create_handler_registration.argtypes = (
    ctypes.c_char_p,    # name
    ctypes.c_void_p,    # unused arg ptr: Netsnmp_Node_Handler *handler_access_method
    ctypes.POINTER(ctypes.c_ulong), # reg_oid
    ctypes.c_size_t,    # reg_oid_len
    ctypes.c_int,       # modes
)

# From net-snmp/agent/snmp_vars.h
lib_nsa.init_agent.restype  = ctypes.c_int
lib_nsa.init_agent.argtypes = (
    ctypes.c_char_p,    # app
)

# From net-snmp/agent/table_data.h
class netsnmp_table_row(ctypes.Structure):
    pass
netsnmp_table_row._fields_ = (
    ('indexes',       ctypes.POINTER(netsnmp_variable_list)),
    ('index_oid',     ctypes.POINTER(ctypes.c_ulong)),
    ('index_oid_len', ctypes.c_size_t),
    ('data',          ctypes.c_void_p),
    ('next',          ctypes.POINTER(netsnmp_table_row)),
    ('prev',          ctypes.POINTER(netsnmp_table_row)),
)

class netsnmp_table_data(ctypes.Structure):
    pass
netsnmp_table_data._fields_ = (
    ('indexes_template', ctypes.POINTER(netsnmp_variable_list)),
    ('name',             ctypes.c_char_p),
    ('flags',            ctypes.c_int),
    ('store_indexes',    ctypes.c_int),
    ('first_row',        ctypes.POINTER(netsnmp_table_row)),
    ('last_row',         ctypes.POINTER(netsnmp_table_row)),
)

# From net-snmp/agent/table_dataset.h
class netsnmp_table_data_storage(ctypes.Structure):
    pass
netsnmp_table_data_storage._fields_ = (
    ('column',         ctypes.c_uint),
    ('writable',       ctypes.c_char),
    ('change_ok_fn',   ctypes.c_void_p), # unused fun ptr: typedef int (Netsnmp_Value_Change_Ok) (char *old_value, size_t old_value_len, char *new_value, size_t new_value_len, void *mydata);
    ('my_change_data', ctypes.c_void_p),
    ('type',           ctypes.c_ubyte),
    ('data',           netsnmp_vardata),
    ('data_len',       ctypes.c_ulong),
    ('next',           ctypes.POINTER(netsnmp_table_data_storage)),
)

class netsnmp_table_data_set(ctypes.Structure):
    pass
netsnmp_table_data_set._fields_ = (
    ('table',            ctypes.POINTER(netsnmp_table_data)),
    ('default_row',      ctypes.POINTER(netsnmp_table_data_storage)),
    ('allow_creation',   ctypes.c_int),
    ('rowstatus_column', ctypes.c_uint),
)

lib_nsh.netsnmp_create_table_data_set.restype  = ctypes.POINTER(netsnmp_table_data_set)
lib_nsh.netsnmp_create_table_data_set.argtypes = (
    ctypes.c_char_p,    # table_name
)

lib_nsh.netsnmp_table_dataset_add_index.restype  = None
lib_nsh.netsnmp_table_dataset_add_index.argtypes = (
    ctypes.POINTER(netsnmp_table_data_set), # table
    ctypes.c_ubyte,     # type
)

lib_nsh.netsnmp_table_dataset_add_row.restype  = None
lib_nsh.netsnmp_table_dataset_add_row.argtypes = (
    ctypes.POINTER(netsnmp_table_data_set), # table
    ctypes.POINTER(netsnmp_table_row),      # row
)

lib_nsh.netsnmp_table_set_add_default_row.restype  = ctypes.c_int
lib_nsh.netsnmp_table_set_add_default_row.argtypes = (
    ctypes.POINTER(netsnmp_table_data_set), # table_set
    ctypes.c_uint,      # column
    ctypes.c_int,       # type
    ctypes.c_int,       # writable
    ctypes.c_void_p,    # default_value
    ctypes.c_size_t,    # default_value_len
)

lib_nsh.netsnmp_register_table_data_set.restype  = ctypes.c_int
lib_nsh.netsnmp_register_table_data_set.argtypes = (
    ctypes.POINTER(netsnmp_handler_registration),   # reginfo
    ctypes.POINTER(netsnmp_table_data_set),         # data_set
    ctypes.c_void_p,    # unused arg ptr: netsnmp_table_registration_info * table_info
)

lib_nsh.netsnmp_table_data_set_create_row_from_defaults.restype  = ctypes.POINTER(netsnmp_table_row)
lib_nsh.netsnmp_table_data_set_create_row_from_defaults.argtypes = (
    ctypes.POINTER(netsnmp_table_data_storage), # defrow
)

lib_nsh.netsnmp_set_row_column.restype  = ctypes.c_int
lib_nsh.netsnmp_set_row_column.argtypes = (
    ctypes.POINTER(netsnmp_table_row),  # row
    ctypes.c_uint,      # column
    ctypes.c_int,       # type
    ctypes.c_void_p,    # value
    ctypes.c_size_t,    # value_len
)

lib_nsh.netsnmp_table_dataset_remove_and_delete_row.restype  = None
lib_nsh.netsnmp_table_dataset_remove_and_delete_row.argtypes = (
    ctypes.POINTER(netsnmp_table_data_set),         # data_set
    ctypes.POINTER(netsnmp_table_row),  # row
)

# From net-snmp/agent/watcher.h
WATCHER_FIXED_SIZE  = 0x01
WATCHER_MAX_SIZE    = 0x02
WATCHER_SIZE_IS_PTR = 0x04
WATCHER_SIZE_STRLEN = 0x08

class netsnmp_watcher_info(ctypes.Structure):
    pass
netsnmp_watcher_info._fields_ = (
    ('data',        ctypes.c_void_p),
    ('data_size',   ctypes.c_size_t),
    ('max_size',    ctypes.c_size_t),
    ('type',        ctypes.c_ubyte),
    ('flags',       ctypes.c_int),
    ('data_size_p', ctypes.POINTER(ctypes.c_size_t)),
)

lib_nsh.netsnmp_create_watcher_info.restype  = ctypes.POINTER(netsnmp_watcher_info)
lib_nsh.netsnmp_create_watcher_info.argtypes = (
    ctypes.c_void_p,    # data
    ctypes.c_size_t,    # size
    ctypes.c_ubyte,     # type
    ctypes.c_int,       # flags
)

lib_nsh.netsnmp_register_watched_instance.restype  = ctypes.c_int
lib_nsh.netsnmp_register_watched_instance.argtypes = (
    ctypes.POINTER(netsnmp_handler_registration),   # reginfo
    ctypes.POINTER(netsnmp_watcher_info),           # watchinfo
)

# From net-snmp/session_api.h
lib_nsh.snmp_select_info.restype  = ctypes.c_int
lib_nsh.snmp_select_info.argtypes = (
    ctypes.POINTER(ctypes.c_int),   # numfds
    ctypes.POINTER(fd_set),         # fdset
    ctypes.POINTER(timeval),        # timeout
    ctypes.POINTER(ctypes.c_int),   # block
)

lib_nsh.snmp_read.restype  = None
lib_nsh.snmp_read.argtypes = (
    ctypes.POINTER(fd_set), # fdset
)

# agentx.py constants
MAX_STR_LEN = 1024

class ASNType(object):
    def __init__(self):
        if object in self.__class__.__bases__:
            raise TypeError('%s is a pure abstract class' % self.__class__.__name__)

    def reference(self):
        return ctypes.byref(self._data)

    def data_size(self):
        return ctypes.sizeof(self._data)

    def get_value(self):
        return self._data.value

    def set_value(self, data):
        self._data.value = data
        if hasattr(self, '_watcher'):
            self._watcher.contents.data_size = self.data_size()

    def get_watch(self):
        if not hasattr(self, '_watcher'):
            self._watcher = lib_nsh.netsnmp_create_watcher_info(
                self.reference(),
                self.data_size(),
                self._type,
                self._flags
            )
            self._watcher.contents.max_size = self._max_size

        return self._watcher

class OctetString(ASNType):
    def __init__(self, data=''):
        self._data     = ctypes.create_string_buffer(data, MAX_STR_LEN)
        self._type     = ASN_OCTET_STR
        self._flags    = WATCHER_MAX_SIZE
        self._max_size = MAX_STR_LEN
        super(self.__class__, self).__init__()

    def data_size(self):
        return len(self._data.value)

class Counter64(ASNType):
    def __init__(self, data=0):
        self._data     = counter64(*self.split_int(data))
        self._type     = ASN_COUNTER64
        self._flags    = WATCHER_FIXED_SIZE
        self._max_size = ctypes.sizeof(counter64)
        super(self.__class__, self).__init__()

    def get_value(self):
        return (self._data.high << 32) + self._data.low

    def set_value(self, data):
        self._data.high, self._data.low = self.split_int(data)

    def split_int(self, data):
        return data >> 32, data & 0xFFFFFFFF

class Integer32(ASNType):
    def __init__(self, data=0):
        self._data     = ctypes.c_int(data)
        self._type     = ASN_INTEGER
        self._flags    = WATCHER_FIXED_SIZE
        self._max_size = ctypes.sizeof(ctypes.c_int)
        super(self.__class__, self).__init__()

class Table(object):
    def __init__(self, *cols):
        self.types = []
        self.index = Integer32()
        self.table = lib_nsh.netsnmp_create_table_data_set(None)
        lib_nsh.netsnmp_table_dataset_add_index(self.table, self.index._type)

        for c in range(len(cols)):
            self.types.append(cols[c].__class__)
            lib_nsh.netsnmp_table_set_add_default_row(self.table, c + 1, cols[c]._type, 0, cols[c].reference(), cols[c].data_size())

    def append(self, *vals):
        if len(vals) == len(self.types) + 1:
            idx, row = vals[0], vals[1:]
        else:
            idx, row = self.index.get_value() + 1, vals

        self.index.set_value(idx)
        tmp_table_row = lib_nsh.netsnmp_table_data_set_create_row_from_defaults(self.table.contents.default_row)

        lib_nsa.snmp_varlist_add_variable(ctypes.byref(tmp_table_row.contents.indexes), None, 0, self.index._type, self.index.reference(), self.index.data_size())

        for col in range(len(row)):
            val = self.types[col](row[col])
            lib_nsh.netsnmp_set_row_column(tmp_table_row, col + 1, val._type, val.reference(), val.data_size())

        lib_nsh.netsnmp_table_dataset_add_row(self.table, tmp_table_row)

    def clear(self):
        self.index.set_value(0)

        row_iter = self.table.contents.table.contents.first_row
        while bool(row_iter):
            row_next = row_iter.contents.next
            lib_nsh.netsnmp_table_dataset_remove_and_delete_row(self.table, row_iter)
            row_iter = row_next

class AgentX(object):
    def __init__(self, name=None, mib=None):
        self.name = name if name is not None else self.__class__.__name__
        self.data = {}

        lib_nsa.netsnmp_enable_subagent()
        lib_nsa.init_agent(self.name)

        lib_nsa.netsnmp_init_mib()
        if mib is not None:
            lib_nsa.read_mib(mib)

    def ObjectFactory(func):
        def wrapped(self, val=None, oid=None):
            obj = getattr(sys.modules[__name__], func.__name__)()
            if val is not None:
                obj.set_value(val)
            if oid is not None:
                self.register_value(obj, oid)
            return obj
        return wrapped

    @ObjectFactory
    def OctetString(self, val=None, oid=None):
        pass

    @ObjectFactory
    def Integer32(self, val=None, oid=None):
        pass

    @ObjectFactory
    def Counter64(self, val=None, oid=None):
        pass

    def Table(self, oid=None, *cols):
        tbl = Table(*cols)
        if oid is not None:
            self.register_table(tbl, oid)
        return tbl

    def start_subagent(self):
        lib_nsa.init_snmp(self.name)

    def create_handler(self, oid):
        root_len = ctypes.c_size_t(MAX_OID_LEN)
        root_oid = (ctypes.c_ulong * MAX_OID_LEN)()
        lib_nsh.read_objid(oid, root_oid, ctypes.byref(root_len))

        return lib_nsh.netsnmp_create_handler_registration(oid, None, root_oid, root_len, 0)

    def register_value(self, obj, oid):
        if oid not in self.data:
            self.data[oid] = obj
            lib_nsh.netsnmp_register_watched_instance(self.create_handler(oid), obj.get_watch())
        else:
            raise ValueError('%s: already registered' % oid)

    def register_table(self, tbl, oid):
        if oid not in self.data:
            self.data[oid] = tbl
            lib_nsh.netsnmp_register_table_data_set(self.create_handler(oid), tbl.table, None)
        else:
            raise ValueError('%s: already registered' % oid)

    def replace_value(self, oid, val):
        if oid in self.data:
            self.data[oid].set_value(val)
        else:
            raise ValueError('%s is not a registered value oid' % oid)

    def replace_table(self, oid, *rows):
        if oid in self.data:
            self.data[oid].clear()
            for row in rows:
                self.data[oid].append(*row)
        else:
            raise ValueError('%s is not a registered table oid' % oid)

    def check_and_process(self, lock=None):
        block = ctypes.c_int(0)
        num_fds = ctypes.c_int(0)
        readers = fd_set()
        timeout = timeval(sys.maxint, 0)

        lib_nsh.snmp_select_info(ctypes.byref(num_fds), ctypes.byref(readers), ctypes.byref(timeout), ctypes.byref(block))
        count = lib_c.select(num_fds, ctypes.byref(readers), None, None, ctypes.byref(timeout) if not block else None)

        if count > 0:
            if lock:
                lock.acquire()

            lib_nsh.snmp_read(ctypes.byref(readers))

            if lock:
                lock.release()
        elif count == 0:
            lib_nsh.snmp_timeout()
        else:
            return

        if lock:
            lock.acquire()

        lib_nsh.snmp_store_if_needed()
        lib_nsh.run_alarms()
        lib_nsh.netsnmp_check_outstanding_agent_requests()

        if lock:
            lock.release()


if __name__ == '__main__':
    import os
    a = AgentX('agentx', '%s/agentx.mib' % os.path.dirname(os.path.realpath(sys.argv[0])))

    s = a.OctetString('foo', 'AGENTX-TEST-MIB::agentxTestString')
    i = a.Integer32(1, 'AGENTX-TEST-MIB::agentxTestInteger')
    c = a.Counter64(1, 'AGENTX-TEST-MIB::agentxTestCounter')
    t = a.Table('AGENTX-TEST-MIB::agentxTestTable', OctetString(), Integer32(), Counter64())
    t.append('clr', 77, 23)

    a.replace_value('AGENTX-TEST-MIB::agentxTestString', 'fum')
    a.replace_table('AGENTX-TEST-MIB::agentxTestTable', ('boo', 1, 2), ('bee', 11, 12), (2323, 'bah', 21, 22), ('bai', 31, 32))

    a.start_subagent()

    stop = False
    while not stop:
        try:
            a.check_and_process()
            i.set_value(i.get_value() + 1)
            c.set_value(c.get_value() + 100)
        except KeyboardInterrupt:
            stop = True
