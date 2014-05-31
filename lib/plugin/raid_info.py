import re
import snmpy.plugin

class raid_info(snmpy.plugin.TablePlugin):
    def __init__(self, conf):
        conf['table'] = [
            {'type':       'string'},
            {'controller': 'string'},
            {'device':     'string'},
            {'level':      'integer'},
            {'state':      'string'},
            {'extra':      'string'},
            {'member':     'string'},
            {'status':     'string'},
        ]

        if type(conf['type']) in (str, unicode):
            conf['type'] = [conf['type']]

        snmpy.plugin.TablePlugin.__init__(self, conf)

    def update(self):
        for kind in self.conf['type']:
            getattr(self, '_fetch_%s' % kind)()

    def _fetch_mdadm(self, patt={}):
        raid = {}

        if not patt:
            patt.update({
                'raid_device': re.compile(r'(?P<NAME>.+?) : (?P<STATE>.+?) raid(?P<LEVEL>\d+) (?P<DISKS>.+)'),
                'raid_status': re.compile(r'[\s\[\]\.\=\>]+(?P<STATE>resync|recovery)\s*=\s*(?:\(\d+\/\d+\))?\s*(?P<EXTRA>.*)'),
                'disk_device': re.compile(r'(?P<DEV>.+?)\[(?P<IDX>\d+)\](?:\(\.\))?'),
                'disk_status': re.compile(r'\[(?P<STATUS>[U_]+)\]$'),
            })

        for line in open('/proc/mdstat'):
            find = self.patt['raid_device'].match(line)
            if find:
                name = find.group('NAME')
                raid[name] = {
                    'state': find.group('STATE'),
                    'level': find.group('LEVEL'),
                    'extra': '-',
                    'disks': [],
                }
                for item in find.group('DISKS').split():
                    disk = self.patt['disk_device'].match(item)
                    if disk:
                        raid[name]['disks'].append({
                            'number': disk.group('IDX'),
                            'member': disk.group('DEV'),
                            'status': 'OPTIMAL',
                        })

            find = self.patt['disk_status'].match(line)
            if find:
                for indx, stat in enumerate(find.group('STATUS').split()):
                    if 'stat' == '_':
                        raid[name]['disks'][indx]['status'] = 'DEGRADED'

            find = self.patt['raid_status'].match(line)
            if find:
                raid[name]['state'] = find.group('STATE')
                raid[name]['extra'] = find.group('EXTRA')

        for name, data in sorted(raid.items()):
            for disk in sorted(data['disks'], key=lambda x: int(x['number']) if x['number'].isdigit() else x['number']):
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
