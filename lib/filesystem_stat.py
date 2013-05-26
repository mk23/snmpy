import os
import snmpy
import stat
import time

class filesystem_stat(snmpy.plugin):
    def s_type(self, obj):
        if stat.S_ISDIR(obj):
            return 'directory'
        if stat.S_ISCHR(obj):
            return 'character special device'
        if stat.S_ISBLK(obj):
            return 'block special device'
        if stat.S_ISREG(obj):
            return 'regular file'
        if stat.S_ISFIFO(obj):
            return 'named pipe'
        if stat.S_ISLNK(obj):
            return 'symbolic link'
        if stat.S_ISSOCK(obj):
            return 'socket'

        return 'unknown'

    def gather(self, obj):
        item = self.stat[obj.split('.')[-1]]
        try:
            info = os.lstat(self.conf['object'])
            self.data[obj] = item[1](getattr(info, 'st_%s' % item[0], info.st_mode))
        except Exception as e:
            snmpy.log_error(e, '%s: os.stat() error' % self.conf['object'])
            self.data[obj] = item[2]

    def create(self):
        self.stat = {
            '1':  ('name',  lambda: self.conf['object'], self.conf['object']),
            '2':  ('type',  self.s_type, 'missing'),
            '3':  ('mode',  lambda x: '%04o' % stat.S_IMODE(x), 'missing'),
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
