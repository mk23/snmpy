import re
import time

MIB_MODULE  = 'SNMPY-MIB'
KEY_PREFIX  = 'snmpy'
VERSION_KEY = 'info_version'
PLUGINS_KEY = 'info_plugins'

def camel_case(key):
    return ''.join(i[0].upper() + i[1:].lower() for i in key.split('_'))

def get_oidstr(*args):
    return '%s::%s%s' % (MIB_MODULE, KEY_PREFIX, camel_case('_'.join(args)))

def get_syntax(key, default='DisplayString', type_map={}):
    if not type_map:
        type_map.update({
            'Integer32': re.compile(r'int(?:eger)?(?:32)?'),
            'Counter32': re.compile(r'count(?:er)?(?:32)?'),
            'Counter64': re.compile(r'(?:long|int(?:eger)?64|count(?:er)?64)'),
            'DisplayString': re.compile(r'(?:display)?str(?:ing)?'),
        })

    for name, patt in type_map.items():
        if patt.match(key):
            return name

    return default

def get_default(key, type_map={}):
    if not type_map:
        type_map.update({
            'Integer32':     0,
            'Counter32':     0,
            'Counter64':     0,
            'DisplayString': '',
        })

    return type_map[get_syntax(key)]

def config_mib(plugin):
    name = camel_case(plugin.name)
    part = '''
        {prefix}{name} OBJECT IDENTIFIER ::= {{ {prefix}MIB {oid} }}
    '''.format(prefix=KEY_PREFIX, name=name, oid=plugin.conf['snmpy_index'])

    if 'items' in plugin.conf:
        for item, conf in plugin:
            part += '''
                {prefix}{name}{part} OBJECT-TYPE
                    SYNTAX      {syntax}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{part}"
                    ::= {{ {prefix}{name} {oid} }}
            '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=conf['syntax'], oid=conf['oidnum'])
    elif 'table' in plugin.conf:
        for oid in xrange(len(plugin.conf['table'])):
            item, conf = plugin.conf['table'][oid].items().pop()
            types = []
            parts = ''

            for col in xrange(len(conf)):
                col_key, col_val = conf[col].items().pop()

                types.append(
                    '''
                        {prefix}{name}{part}{key} {syntax}
                    '''.format(prefix=KEY_PREFIX, syntax=get_syntax(col_val), name=name, part=camel_case(item), key=camel_case(col_key))
                )
                parts += '''
                    {prefix}{name}{part}{key} OBJECT-TYPE
                    SYNTAX      {syntax}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{part}{key}"
                    ::= {{ {prefix}{name}{part}Entry {oid} }}
                '''.format(prefix=KEY_PREFIX, syntax=get_syntax(col_val), name=name, part=camel_case(item), key=camel_case(col_key), oid=col+2)

            part += '''
                {prefix}{name}{key} OBJECT IDENTIFIER ::= {{ {prefix}{name}Table {oid} }}
                {Prefix}{name}{key}Entry ::= SEQUENCE {{
                    {prefix}{name}{key}Index Integer32,
                    {types}
                }}
                {prefix}{name}{key}Table OBJECT-TYPE
                    SYNTAX      SEQUENCE OF {Prefix}{name}{key}Entry
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{key}Table"
                    ::= {{ {prefix}{name}{key} 1 }}
                {prefix}{name}{key}Entry OBJECT-TYPE
                    SYNTAX      {Prefix}{name}{key}Entry
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{key}Entry"
                    INDEX       {{ {prefix}{name}{key}Index }}
                    ::= {{ {prefix}{name}{key}Table 1 }}
                {prefix}{name}{key}Index OBJECT-TYPE
                    SYNTAX      Integer32 (0..2147483647)
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{key}Index"
                    ::= {{ {prefix}{name}{key}Entry 1 }}
                {parts}
            '''.format(prefix=KEY_PREFIX, Prefix=camel_case(KEY_PREFIX), name=name, key=camel_case(item), types=',\n'.join(types), parts=parts, oid=oid+1)

    return part

def create_mib(conf, plugins):
    mib_args = {
        'date':    time.strftime('%Y%m%d%H%MZ'),
        'parts':   ''.join(config_mib(p) for p in plugins.values() if p.name != 'snmpy_info'),
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
            MODULE-IDENTITY, OBJECT-TYPE, Integer32, Counter32, Counter64   FROM SNMPv2-SMI
            DisplayString                                                   FROM SNMPv2-TC
            enterprises                                                     FROM SNMPv2-SMI
            agentxObjects                                                   FROM AGENTX-MIB
            ucdavis                                                         FROM UCD-SNMP-MIB
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
            SYNTAX      DisplayString
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "{prefix}{version}"
            ::= {{ {prefix}Info 0 }}

        {Prefix}{plugins}Entry ::= SEQUENCE {{
            {prefix}{plugins}Index Integer32,
            {prefix}{plugins}Name  DisplayString
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

        {prefix}{plugins}Index OBJECT-TYPE
            SYNTAX      Integer32 (0..2147483647)
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "{prefix}{plugins}Index"
            ::= {{ {prefix}{plugins}Entry 1 }}

        {prefix}{plugins}Name OBJECT-TYPE
            SYNTAX      DisplayString
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "{prefix}{plugins}Name"
            ::= {{ {prefix}{plugins}Entry 2 }}
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

    return text
