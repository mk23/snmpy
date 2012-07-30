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

    def s_name(self, obj):
        return self.conf['file_name']

    def gather(self, obj):
        item = self.stat[obj.split('.')[-1]]
        try:
            info = os.lstat(self.conf['file_name'])
            self.data[obj] = item[1](getattr(info, 'st_%s' % item[0], info.st_mode))
        except Exception as e:
            snmpy.log_exc(e, '%s: os.stat() error' % self.conf['file_name'])
            self.data[obj] = item[2]

    def create(self):
        self.stat = {
            '1':  ('name',  self.s_name, self.conf['file_name']),
            '2':  ('type',  self.s_type, 'missing'),
            '3':  ('atime', self.s_time, -1),
            '4':  ('mtime', self.s_time, -1),
            '5':  ('ctime', self.s_time, -1),
            '6':  ('nlink', self.s_pass, -1),
            '7':  ('size',  self.s_pass, -1),
            '8':  ('ino',   self.s_pass, -1),
            '9':  ('uid',   self.s_pass, -1),
            '10': ('gid',   self.s_pass, -1),
        }

        for k, v in self.stat.items():
            snmp_type = 'integer' if type(v[2]) == int else 'string'
            self.data['1.%s' % k] = 'string', v[0]
            self.data['2.%s' % k] = snmp_type, v[2], {'run': self.gather}
