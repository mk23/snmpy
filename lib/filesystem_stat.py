import os
import snmpy
import stat
import time

class filesystem_stat(snmpy.plugin):
    def gather(self, obj):
        item = self.stat[obj.split('.')[-1]]
        try:
            info = os.lstat(self.conf['object'])
            self.data[obj] = item[1](getattr(info, 'st_%s' % item[0], info.st_mode))
        except Exception as e:
            snmpy.log_error(e, '%s: os.stat() error' % self.conf['object'])
            self.data[obj] = item[2]

    def create(self):
        self.kind = {
            stat.S_IFDIR:  'directory',
            stat.S_IFCHR:  'character device',
            stat.S_IFBLK:  'block device',
            stat.S_IFREG:  'regular file',
            stat.S_IFIFO:  'named pipe',
            stat.S_IFLNK:  'symbolic link',
            stat.S_IFSOCK: 'socket',
        }

        self.stat = {
            '1':  ('name',  lambda x: self.conf['object'], self.conf['object']),
            '2':  ('type',  lambda x: self.kind.get(stat.S_IFMT(x), 'unknown'), 'unknown'),
            '3':  ('mode',  lambda x: '%04o' % stat.S_IMODE(x), 'unknown'),
            '4':  ('atime', lambda x: int(time.time() - x), -1),
            '5':  ('mtime', lambda x: int(time.time() - x), -1),
            '6':  ('ctime', lambda x: int(time.time() - x), -1),
            '7':  ('nlink', lambda x: x, -1),
            '8':  ('size',  lambda x: x, -1),
            '9':  ('ino',   lambda x: x, -1),
            '10': ('uid',   lambda x: x, -1),
            '11': ('gid',   lambda x: x, -1),
        }

        for k, v in self.stat.items():
            snmp_type = 'integer' if type(v[2]) == int else 'string'
            self.data['1.%s' % k] = 'string', v[0]
            self.data['2.%s' % k] = snmp_type, v[2], {'run': self.gather}
