import re
import snmpy.module


class raid_info(snmpy.module.TableModule):
    def __init__(self, conf):
        conf['table'] = [
            {'type':       'string'},
            {'controller': 'string'},
            {'volume':     'string'},
            {'level':      'integer'},
            {'state':      'string'},
            {'extra':      'string'},
            {'device':     'string'},
            {'status':     'string'},
        ]

        if type(conf['type']) in (str, unicode):
            conf['type'] = [conf['type']]

        snmpy.module.TableModule.__init__(self, conf)

    def update(self):
        for kind in self.conf['type']:
            getattr(self, '_fetch_%s' % kind)()

    def _fetch_mdadm(self, patt={}):
        raid = {}

        if not patt:
            patt.update({
                'raid_volume': re.compile(r'(?P<NAME>.+?) : (?P<STATE>.+?) raid(?P<LEVEL>\d+) (?P<DISKS>.+)'),
                'raid_status': re.compile(r'[\s\[\]\.\=\>]+(?P<STATE>resync|recovery)\s*=\s*(?:\(\d+\/\d+\))?\s*(?P<EXTRA>.*)'),
                'disk_device': re.compile(r'\s*(?P<DEV>.+?)\[(?P<IDX>\d+)\][^\s]*'),
                'disk_status': re.compile(r'\[(?P<STATUS>[U_]+)\]$'),
            })

        for line in open('/proc/mdstat'):
            find = patt['raid_volume'].match(line)
            if find:
                name = find.group('NAME')
                raid[name] = {
                    'state': 'ONLINE' if find.group('STATE') == 'active' else 'OFFLINE',
                    'level': find.group('LEVEL'),
                    'extra': '-',
                    'disks': {},
                }
                for disk, indx in patt['disk_device'].findall(find.group('DISKS')):
                    raid[name]['disks'][int(indx)] = {
                        'member': disk,
                        'status': 'UNKNOWN',
                    }

            find = patt['disk_status'].search(line)
            if find:
                for indx, stat in enumerate(list(find.group('STATUS'))):
                    if stat == '_':
                        if indx not in raid[name]['disks']:
                            raid[name]['disks'][indx] = {
                                'member': '(missing)',
                                'status': 'MISSING',
                            }
                        else:
                            raid[name]['disks'][indx]['status'] = 'FAILED'
                    elif stat == 'U':
                        raid[name]['disks'][indx]['status'] = 'ACTIVE'

            find = patt['raid_status'].match(line)
            if find:
                raid[name]['state'] = 'REBUILD'
                raid[name]['extra'] = find.group('EXTRA')


        for name, data in sorted(raid.items()):
            for indx, disk in sorted(data['disks'].items()):
                self.append([
                    'mdadm',
                    '-',
                    name,
                    data['level'],
                    data['state'],
                    data['extra'],
                    disk['member'],
                    disk['status'],
                ])
