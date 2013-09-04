import re
import time

def camel_case(key):
    return ''.join(i[0].upper() + i[1:].lower() for i in key.split('_'))

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

def config_mib(plugin):
    name = camel_case(plugin.name)
    part = '''
        snmpy{name} OBJECT IDENTIFIER ::= {{ snmpyMIB {oid} }}

        snmpy{name}Items OBJECT IDENTIFIER ::= {{ snmpy{name} 0 }}
        snmpy{name}Table OBJECT IDENTIFIER ::= {{ snmpy{name} 1 }}
    '''.format(name=name, oid=plugin.conf['snmpy_index'])

    if 'items' in plugin.conf:
        for oid in xrange(len(plugin.conf['items'])):
            item, conf = plugin.conf['items'][oid].items().pop()
            part += '''
                snmpy{name}Items{part} OBJECT-TYPE
                    SYNTAX      {val}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "snmpy{name}Items{part}"
                    ::= {{ snmpy{name}Items {oid} }}
            '''.format(name=name, part=camel_case(item), val=get_syntax(conf['type']), oid=oid+1)

    if 'table' in plugin.conf:
        for oid in xrange(len(plugin.conf['table'])):
            item, conf = plugin.conf['table'][oid].items().pop()
            types = []
            parts = ''

            for col in xrange(len(conf)):
                col_key, col_val = conf[col].items().pop()

                types.append(
                    '''
                        snmpy{name}Table{part}{key} {val}
                    '''.format(name=name, part=camel_case(item), key=camel_case(col_key), val=get_syntax(col_val))
                )
                parts += '''
                    snmpy{name}Table{part}{key} OBJECT-TYPE
                    SYNTAX      {val}
                    MAX-ACCESS  read-only
                    STATUS      current
                    DESCRIPTION "snmpy{name}Table{part}{key}"
                    ::= {{ snmpy{name}Table{part}Entry {oid} }}
                '''.format(name=name, part=camel_case(item), key=camel_case(col_key), val=get_syntax(col_val), oid=col+2)

            part += '''
                snmpy{name}Table{key} OBJECT IDENTIFIER ::= {{ snmpy{name}Table {oid} }}
                Snmpy{name}Table{key}Entry ::= SEQUENCE {{
                    snmpy{name}Table{key}Index Integer32,
                    {types}
                }}
                snmpy{name}Table{key}Table OBJECT-TYPE
                    SYNTAX      SEQUENCE OF Snmpy{name}Table{key}Entry
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "snmpy{name}Table{key}Table"
                    ::= {{ snmpy{name}Table{key} 1 }}
                snmpy{name}Table{key}Entry OBJECT-TYPE
                    SYNTAX      Snmpy{name}Table{key}Entry
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "snmpy{name}Table{key}Entry"
                    INDEX       {{ snmpy{name}Table{key}Index }}
                    ::= {{ snmpy{name}Table{key}Table 1 }}
                snmpy{name}Table{key}Index OBJECT-TYPE
                    SYNTAX      Integer32 (0..2147483647)
                    MAX-ACCESS  not-accessible
                    STATUS      current
                    DESCRIPTION "snmpy{name}Table{key}Index"
                    ::= {{ snmpy{name}Table{key}Entry 1 }}
                {parts}
            '''.format(name=name, key=camel_case(item), types=',\n'.join(types), parts=parts, oid=oid+1)

    return part

def create_mib(conf, plugins):
    mib_args = {
        'date':   time.strftime('%Y%m%d%H%MZ'),
        'parts':  ''.join(config_mib(p) for p in plugins.values() if p.name != 'snmpy_info'),
        'parent': conf['snmpy_global']['parent_root'],
        'system': conf['snmpy_global']['system_root'],
    }
    mib_text = '''
        SNMPY-MIB DEFINITIONS ::= BEGIN

        IMPORTS
            MODULE-IDENTITY, OBJECT-TYPE, Integer32, Counter32, Counter64   FROM SNMPv2-SMI
            DisplayString                                                   FROM SNMPv2-TC
            enterprises                                                     FROM SNMPv2-SMI
            agentxObjects                                                   FROM AGENTX-MIB
            ucdavis                                                         FROM UCD-SNMP-MIB
            ;

        snmpyMIB MODULE-IDENTITY
            LAST-UPDATED "{date}"
            ORGANIZATION "N/A"
            CONTACT-INFO "Editor: Max Kalika Email: max.kalika+projects@gmail.com"
            DESCRIPTION  "snmpy mib"
            REVISION     "{date}"
            DESCRIPTION  "autogenerated mib"
            ::= {{ {parent} {system} }}

        {parts}

        END
    '''.format(**mib_args)

    '''
        snmpyInfo OBJECT IDENTIFIER ::= {{ snmpyMIB 0 }}
        snmpyModules OBJECT IDENTIFIER ::= {{ snmpyMIB 1 }}

        snmpyInfoVersion OBJECT-TYPE
            SYNTAX      DisplayString
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "snmpyInfoVersion"
            ::= {{ snmpyInfo 1 }}

        SnmpyInfoModulesEntry ::= SEQUENCE {{
            snmpyInfoModulesIndex Integer32,
            snmpyInfoModulesName  DisplayString
        }}

        snmpyInfoModulesTable OBJECT-TYPE
            SYNTAX      SEQUENCE OF SnmpyInfoModulesEntry
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "snmpyInfoModulesTable"
            ::= {{ snmpyInfo 2 }}

        snmpyInfoModulesEntry OBJECT-TYPE
            SYNTAX      SnmpyInfoModulesEntry
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "snmpyInfoModulesEntry"
            INDEX       {{ snmpyInfoModulesIndex }}
            ::= {{ snmpyInfoModulesTable 1 }}

        snmpyInfoModulesIndex OBJECT-TYPE
            SYNTAX      Integer32 (0..2147483647)
            MAX-ACCESS  not-accessible
            STATUS      current
            DESCRIPTION "snmpyInfoModulesIndex"
            ::= {{ snmpyInfoModulesEntry 1 }}

        snmpyInfoModulesName OBJECT-TYPE
            SYNTAX      DisplayString
            MAX-ACCESS  read-only
            STATUS      current
            DESCRIPTION "snmpyInfoModulesName"
            ::= {{ snmpyInfoModulesEntry 2 }}

        {parts}

        END
    '''

    text = ''
    sect = False
    for line in re.sub(r'^\s*(.*)$', r'\1', mib_text, flags=re.MULTILINE).splitlines(True):
        if line.strip().startswith('}'):
            sect = False
        if re.match(r'(?:import|snmpy|end|})', line, flags=re.IGNORECASE) and not sect:
            text += line
        else:
            text += line.rjust(len(line) + 4)
        if line.strip().endswith('SEQUENCE {'):
            sect = True

    return text
