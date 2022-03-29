import collections
import re
import snmpy.module
import time

MIB_MODULE  = 'SNMPY-MIB'
KEY_PREFIX  = 'snmpy'
VERSION_KEY = 'info_version'
PLUGINS_KEY = 'info_plugins'

object_syntax = collections.namedtuple('object_syntax', ('mib_type', 'object_type', 'native_type'))

def camel_case(key):
    return ''.join(i[0].upper() + i[1:].lower() for i in key.split('_'))

def get_oidstr(*args):
    return '%s::%s%s' % (MIB_MODULE, KEY_PREFIX, camel_case('_'.join(args)))

def get_syntax(key, type_map=collections.OrderedDict()):
    if not type_map:
        type_map['Counter64'] = re.compile(r'(?:long|int(?:eger)?64|count(?:er)?64)')
        type_map['Integer32'] = re.compile(r'(?:int(?:eger)?|count)(?:32)?')

    for name, info in list(type_map.items()):
        if info.match(key):
            return object_syntax(name, name, int)

    return object_syntax('OCTET STRING', 'OctetString', str)

def config_mib(plugin):
    name = camel_case(plugin.name)
    part = '''
        {prefix}{name} OBJECT IDENTIFIER ::= {{ {prefix}MIB {oid} }}
    '''.format(prefix=KEY_PREFIX, name=name, oid=plugin.conf['snmpy_index'])

    if isinstance(plugin, snmpy.module.ValueModule):
        for item in plugin:
            part += '''
                {prefix}{name}{part} OBJECT-TYPE
                    SYNTAX      {syntax}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{part}"
                    ::= {{ {prefix}{name} {oid} }}
            '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin[item].syntax.mib_type, oid=plugin[item].oidnum)
    elif isinstance(plugin, snmpy.module.TableModule):
        types = []
        parts = ''

        for item in plugin.cols:
            types.append(
                '''
                    {prefix}{name}{part} {syntax}
                '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin.cols[item].syntax.mib_type).rstrip()
            )
            parts += '''
                {prefix}{name}{part} OBJECT-TYPE
                SYNTAX      {syntax}
                MAX-ACCESS  read-only
                STATUS      current
                DESCRIPTION "{prefix}{name}{part}"
                ::= {{ {prefix}{name}Entry {oid} }}
            '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin.cols[item].syntax.mib_type, oid=plugin.cols[item].oidnum)

        part += '''
            {Prefix}{name}Entry ::= SEQUENCE {{
                {prefix}{name}Index Integer32,
                {types}
            }}
            {prefix}{name}Table OBJECT-TYPE
                SYNTAX      SEQUENCE OF {Prefix}{name}Entry
                MAX-ACCESS  not-accessible
                STATUS      current
                DESCRIPTION "{prefix}{name}Table"
                ::= {{ {prefix}{name} 1 }}
            {prefix}{name}Entry OBJECT-TYPE
                SYNTAX      {Prefix}{name}Entry
                MAX-ACCESS  not-accessible
                STATUS      current
                DESCRIPTION "{prefix}{name}Entry"
                INDEX       {{ {prefix}{name}Index }}
                ::= {{ {prefix}{name}Table 1 }}
            {parts}
        '''.format(prefix=KEY_PREFIX, Prefix=camel_case(KEY_PREFIX), name=name, types=',\n'.join(types), parts=parts)

    return part

def create_mib(conf, plugins):
    if hasattr(create_mib, 'text'):
        return create_mib.text

    mib_args = {
        'date':    time.strftime('%Y%m%d%H%MZ'),
        'parts':   ''.join(config_mib(p) for p in plugins if p.name != 'snmpy_info'),
        'parent':  conf['snmpy_global']['parent_root'],
        'system':  conf['snmpy_global']['system_root'],
        'module':  MIB_MODULE,
        'prefix':  KEY_PREFIX,
        'Prefix':  camel_case(KEY_PREFIX),
        'version': camel_case(VERSION_KEY),
        'plugins': camel_case(PLUGINS_KEY),
    }
    mib_text = '''
        {module} DEFINITIONS ::= BEGIN

        IMPORTS
            MODULE-IDENTITY, OBJECT-TYPE, Integer32, Counter64   FROM SNMPv2-SMI
            enterprises                                          FROM SNMPv2-SMI
            agentxObjects                                        FROM AGENTX-MIB
            ucdavis                                              FROM UCD-SNMP-MIB
            ;

        {prefix}MIB MODULE-IDENTITY
            LAST-UPDATED "{date}"
            ORGANIZATION "N/A"
            CONTACT-INFO "Editor: Max Kalika Email: max.kalika+projects@gmail.com"
            DESCRIPTION  "{module}"
            REVISION     "{date}"
            DESCRIPTION  "autogenerated mib"
            ::= {{ {parent} {system} }}

        {prefix}Info OBJECT IDENTIFIER ::= {{ {prefix}MIB 0 }}

        {prefix}{version} OBJECT-TYPE
            SYNTAX      OCTET STRING
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "{prefix}{version}"
            ::= {{ {prefix}Info 0 }}

        {Prefix}{plugins}Entry ::= SEQUENCE {{
            {prefix}{plugins}Index Integer32,
            {prefix}{plugins}Name  OCTET STRING
        }}

        {prefix}{plugins}Table OBJECT-TYPE
            SYNTAX      SEQUENCE OF {Prefix}{plugins}Entry
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "{prefix}{plugins}Table"
            ::= {{ {prefix}Info 1 }}

        {prefix}{plugins}Entry OBJECT-TYPE
            SYNTAX      {Prefix}{plugins}Entry
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "{prefix}{plugins}Entry"
            INDEX       {{ {prefix}{plugins}Index }}
            ::= {{ {prefix}{plugins}Table 1 }}

        {prefix}{plugins}Name OBJECT-TYPE
            SYNTAX      OCTET STRING
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "{prefix}{plugins}Name"
            ::= {{ {prefix}{plugins}Entry 1 }}
        {parts}

        END
    '''.format(**mib_args)

    text = ''
    sect = False
    for line in re.sub(r'^\s*(.*)$', r'\1', mib_text, flags=re.MULTILINE).splitlines(True):
        if line.strip().startswith('}'):
            sect = False
        if re.match(r'(?:import|%s|end|})' % KEY_PREFIX, line, flags=re.IGNORECASE) and not sect:
            text += line
        else:
            text += line.rjust(len(line) + 4)
        if line.strip().endswith('SEQUENCE {'):
            sect = True

    create_mib.text = text
    return create_mib.text
