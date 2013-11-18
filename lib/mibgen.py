import re
import snmpy.plugin
import time

MIB_MODULE  = 'SNMPY-MIB'
KEY_PREFIX  = 'snmpy'
VERSION_KEY = 'info_version'
PLUGINS_KEY = 'info_plugins'

def camel_case(key):
    return ''.join(i[0].upper() + i[1:].lower() for i in key.split('_'))

def get_oidstr(*args):
    return '%s::%s%s' % (MIB_MODULE, KEY_PREFIX, camel_case('_'.join(args)))

def get_syntax(key, type_map={}):
    if not type_map:
        type_map.update({
            'Integer32':     (re.compile(r'int(?:eger)?(?:32)?'),                     int, 0),
            'Counter32':     (re.compile(r'count(?:er)?(?:32)?'),                     int, 0),
            'Counter64':     (re.compile(r'(?:long|int(?:eger)?64|count(?:er)?64)'),  int, 0),
#            'DisplayString': (re.compile(r'(?:display)?str(?:ing)?'),                 str, ''),
        })

    for name, info in type_map.items():
        if info[0].match(key):
            return name, info[1], info[2]

    return 'DisplayString', str, ''

def config_mib(plugin):
    name = camel_case(plugin.name)
    part = '''
        {prefix}{name} OBJECT IDENTIFIER ::= {{ {prefix}MIB {oid} }}
    '''.format(prefix=KEY_PREFIX, name=name, oid=plugin.conf['snmpy_index'])

    if isinstance(plugin, snmpy.plugin.ValuePlugin):
        for item in plugin:
            part += '''
                {prefix}{name}{part} OBJECT-TYPE
                    SYNTAX      {syntax}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "{prefix}{name}{part}"
                    ::= {{ {prefix}{name} {oid} }}
            '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin[item].syntax, oid=plugin[item].oidnum)
    elif isinstance(plugin, snmpy.plugin.TablePlugin):
        types = []
        parts = ''

        for item in plugin.cols:
            types.append(
                '''
                    {prefix}{name}{part} {syntax}
                '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin.cols[item].syntax).rstrip()
            )
            parts += '''
                {prefix}{name}{part} OBJECT-TYPE
                SYNTAX      {syntax}
                MAX-ACCESS  read-only
                STATUS      current
                DESCRIPTION "{prefix}{name}{part}"
                ::= {{ {prefix}{name}Entry {oid} }}
            '''.format(prefix=KEY_PREFIX, name=name, part=camel_case(item), syntax=plugin.cols[item].syntax, oid=plugin.cols[item].oidnum)

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
            {prefix}{name}Index OBJECT-TYPE
                SYNTAX      Integer32 (0..2147483647)
                MAX-ACCESS  not-accessible
                STATUS      current
                DESCRIPTION "{prefix}{name}Index"
                ::= {{ {prefix}{name}Entry 1 }}
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

    create_mib.text = text
    return create_mib.text
