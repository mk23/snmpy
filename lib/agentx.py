#!/usr/bin/python

import ctypes.util

lib_nsh = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmphelpers'))
lib_nsa = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmpagent'))
lib_ns  = ctypes.cdll.LoadLibrary(ctypes.util.find_library('netsnmp'))

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

lib_ns.init_snmp.restype  = ctypes.c_int
lib_ns.init_snmp.argtypes = (
    ctypes.c_char_p,    # type
)

lib_ns.snmp_varlist_add_variable.restype  = ctypes.POINTER(netsnmp_variable_list)
lib_ns.snmp_varlist_add_variable.argtypes = (
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
lib_nsh.netsnmp_handler_registration_create.argtypes = (
    ctypes.c_char_p,    # name
    ctypes.c_void_p,    # unused arg ptr: netsnmp_mib_handler *handler
    ctypes.POINTER(ctypes.c_ulong), # reg_oid
    ctypes.c_size_t,    # reg_oid_len
    ctypes.c_int,       # modes
)

# From net-snmp/agent/snmp_agent.h
lib_nsa.agent_check_and_process.restype  = ctypes.c_int
lib_nsa.agent_check_and_process.argtypes = (
    ctypes.c_int,       # block
)

# From net-snmp/agent/snmp_vars.h
lib_nsa.init_agent.restype  = ctypes.c_int
lib_nsa.init_agent.argtypes = (
    ctypes.c_char_p,    # app
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

# agentx.py constants
MAX_STR_LEN = 1024

class WatchedInstance(object):
    def __init__(self):
        self.watcher = lib_nsh.netsnmp_create_watcher_info(
            self.reference(),
            self.data_size(),
            self._type,
            self._flags
        )
        self.watcher.contents.max_size = self._max_size

    def reference(self):
        return ctypes.byref(self._data)

    def data_size(self):
        return ctypes.sizeof(self._data)

    def get_value(self):
        return self._data.value

    def set_value(self, data):
        self._data.value = data
        self.watcher.contents.data_size = self.data_size()

class OctetString(WatchedInstance):
    def __init__(self, data=''):
        self._data     = ctypes.create_string_buffer(data, MAX_STR_LEN)
        self._type     = ASN_OCTET_STR
        self._flags    = WATCHER_MAX_SIZE
        self._max_size = MAX_STR_LEN
        super(self.__class__, self).__init__()

    def data_size(self):
        return len(self._data.value)

class Counter64(WatchedInstance):
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

class Integer32(WatchedInstance):
    def __init__(self, data=0):
        self._data     = ctypes.c_int(data)
        self._type     = ASN_INTEGER
        self._flags    = WATCHER_FIXED_SIZE
        self._max_size = ctypes.sizeof(ctypes.c_int)
        super(self.__class__, self).__init__()

class AgentX(object):
    def __init__(self, name):
        lib_nsa.netsnmp_enable_subagent()
        lib_nsa.init_agent(name)
        lib_ns.init_snmp(name)

    def create_handler(self, oid):
        root_len = ctypes.c_size_t(MAX_OID_LEN)
        root_oid = (ctypes.c_ulong * MAX_OID_LEN)()
        lib_nsh.read_objid(oid, root_oid, ctypes.byref(root_len))

        return lib_nsh.netsnmp_create_handler_registration(oid, None, root_oid, root_len, 0)

    def register_value(self, obj, oid):
        lib_nsh.netsnmp_register_watched_instance(self.create_handler(oid), obj.watcher)

    def check_and_process(self):
        lib_nsa.agent_check_and_process(1)


if __name__ == '__main__':
    a = AgentX('agentx')

    s = OctetString('foo')
    i = Integer32(1)
    c = Counter64(1)

    a.register_value(s, '.1.3.6.1.4.1.2021.1123.1')
    a.register_value(i, '.1.3.6.1.4.1.2021.1123.2')
    a.register_value(c, '.1.3.6.1.4.1.2021.1123.3')

    s.set_value('blah')

    stop = False
    while not stop:
        try:
            a.check_and_process()
            i.set_value(i.get_value() + 1)
            c.set_value(c.get_value() + 1000)
        except KeyboardInterrupt:
            stop = True

