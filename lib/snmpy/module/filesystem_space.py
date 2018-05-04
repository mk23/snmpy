import logging
import os
import re
import snmpy.module

LOG = logging.getLogger()


class filesystem_space(snmpy.module.TableModule):
    def __init__(self, conf):
        conf['table'] = [
            {'devnum': 'integer'},
            {'source': 'string'},
            {'target': 'string'},
            {'fstype': 'string'},
            {'space_size': 'integer64'},
            {'space_used': 'integer64'},
            {'space_free': 'integer64'},
            {'inode_size': 'integer64'},
            {'inode_used': 'integer64'},
            {'inode_free': 'integer64'},
        ]

        snmpy.module.TableModule.__init__(self, conf)

    def _unescape_path(self, path):
		return re.sub(r'(\\[0-3][0-7][0-7])', lambda x: chr((ord(x.group(0)[1]) - 48) * 64 + (ord(x.group(0)[2]) - 48) * 8 + (ord(x.group(0)[3]) - 48)), path)

    def update(self):
        seen = set()

        for line in open('/proc/self/mountinfo'):
            ((m_id, p_id, d_id, root, path, opts), (kind, dev, args)) = tuple(i.split(None, 7) for i in line.split('- '))

            dev  = self._unescape_path(dev)
            path = self._unescape_path(path)

            if kind in self.conf.get('exclude', []):
                LOG.debug('discovered excluded filesystem type: %s -> %s (%s)', dev, path, kind)
                continue
            if dev in seen:
                LOG.debug('discovered overlay/duplicate mount: %s -> %s (%s)', dev, path, kind)
                continue
            else:
                seen.add(dev)

            try:
                stat = None
                stat = os.statvfs(path)
            except Exception as e:
                snmpy.log_error(e)

            if getattr(stat, 'f_blocks', 0) > 0 and '/' in dev:
                LOG.debug('discovered real filesystem: %s -> %s', dev, path)

                self.append([
                    int(''.join('%02x' % int(i, 16) for i in d_id.split(':')), 16),
                    dev,
                    path,
                    kind,
                    stat.f_blocks * stat.f_bsize / 1024,
                    (stat.f_blocks - stat.f_bfree) * stat.f_bsize / 1024,
                    stat.f_bfree * stat.f_bsize / 1024,
                    stat.f_files,
                    stat.f_files - stat.f_ffree,
                    stat.f_ffree,
                ])
