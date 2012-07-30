import os
import stat
import snmpy
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

    def s_time(self, obj):
        return int(time.time() - obj)

    def s_pass(self, obj):
        return obj

    def gather(self, obj):
        try:
            info = os.lstat(self.name)
            for k, v in self.stat.items():
                self.data['2.%s' % k] = v[2](info.getattr('st_%s' % v[0], info.st_mode))
        except:
            for k, v in self.stat.items():
                self.data['2.%s' % k] = v[1]

    def create(self):
        self.stat = {
            '1':  ('name', self.name, self.s_pass),
            '2':  ('type', 'missing', self.s_type),
            '3':  ('atime', -1,       self.s_time),
            '4':  ('mtime', -1,       self.s_time),
            '5':  ('ctime', -1,       self.s_time),
            '6':  ('nlink', -1,       self.s_pass),
            '7':  ('size',  -1,       self.s_pass),
            '8':  ('ino',   -1,       self.s_pass),
            '9':  ('uid',   -1,       self.s_pass),
            '10': ('gid',   -1,       self.s_pass),
        }

        for k, v in self.stat.items():
            snmp_type = 'integer' if type(v[1]) == int else 'string'

            self.data['1.%s' % k] = 'string', v[0]
            if k == '1':
                self.data['2.%s' % k] = snmp_type, v[1]
            else:
                self.data['2.%s' % k] = snmp_type, v[1], {'run': self.gather}
