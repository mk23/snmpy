import re
import snmpy.module
import subprocess


class raid_info(snmpy.module.TableModule):
    def __init__(self, conf):
        conf['table'] = [
            {'controller':   'string'},
            {'volume_label': 'string'},
            {'volume_bytes': 'integer64'},
            {'volume_level': 'integer'},
            {'volume_state': 'string'},
            {'volume_extra': 'string'},
            {'member_label': 'string'},
            {'member_state': 'string'},
        ]

        if type(conf['type']) in (str, str):
            conf['type'] = [conf['type']]

        snmpy.module.TableModule.__init__(self, conf)

    def update(self):
        for kind in self.conf['type']:
            getattr(self, '_fetch_%s' % kind)()

    def _fetch_mdadm(self, patt={}):
        raid = {}

        patt = {
            'label': re.compile(r'(?P<LABEL>[\w\./_]+):$'),
            'attrs': {
                'bytes': re.compile(r'Array Size : (?P<BYTES>\d+)'),
                'level': re.compile(r'Raid Level : raid(?P<LEVEL>\d+)'),
                'state': re.compile(r'State : (?P<STATE>[\w ,]+)'),
                'extra': re.compile(r'Re(?:build|sync) Status : (?P<EXTRA>.+)'),
            },
            'disks': re.compile(r'^(?:\s+\d+){4}\s+(?P<STATE>\w+(?:\s+\w+)?)(?:\s+(?P<LABEL>[\w\./_]+))?'),
        }

        def volume_state(kind):
            if 'recovering' in kind or 'resyncing' in kind:
                return 'RECOVERING'
            if 'degraded' in kind:
                return 'DEGRADED'
            if 'clean' in kind or 'active' in kind:
                return 'ONLINE'

        def member_state(kind):
            if 'removed' in kind:
                return 'REMOVED'
            if 'rebuilding' in kind:
                return 'REBUILDING'
            if 'spare' in kind:
                return 'SPARE'
            if 'active' in kind:
                return 'ACTIVE'

        try:
            for line in subprocess.check_output('/sbin/mdadm --detail --scan --verbose --verbose'.split()).decode('ascii').split('\n'):
                find = patt['label'].match(line)
                if find:
                    name = find.group('LABEL')
                    raid[name] = {
                        'disks': [],
                    }
                    continue

                for attr, rexp in list(patt['attrs'].items()):
                    find = rexp.search(line)
                    if find:
                        raid[name][attr] = find.group(attr.upper())
                        break
                else:
                    find = patt['disks'].search(line)
                    if find:
                        raid[name]['disks'].append(
                            (find.group('LABEL') or '(missing)', find.group('STATE')),
                        )
        except subprocess.CalledProcessError as e:
            snmpy.log_error(e)


        for volume, data in sorted(raid.items()):
            for member in data['disks']:
                self.append([
                    'mdadm',
                    volume,
                    int(data['bytes']) * 1024,
                    data['level'],
                    volume_state(data['state']) or 'UNKNOWN',
                    data.get('extra', ''),
                    member[0],
                    member_state(member[1]) or 'UNKNOWN',
                ])
