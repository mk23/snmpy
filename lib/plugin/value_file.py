import os
import snmpy.parser
import snmpy.plugin
import stat
import time

class value_file(snmpy.plugin.ValuePlugin):
    kind = {
        stat.S_IFDIR:  'directory',
        stat.S_IFCHR:  'character device',
        stat.S_IFBLK:  'block device',
        stat.S_IFREG:  'regular file',
        stat.S_IFIFO:  'named pipe',
        stat.S_IFLNK:  'symbolic link',
        stat.S_IFSOCK: 'socket',
    }


    def __init__(self, conf):
        if conf.get('use_stat'):
            conf['items'] = [
                {'file_name':  {'type': 'string',  'func': lambda x: self.conf['object']}},
                {'file_type':  {'type': 'string',  'func': lambda x: self.kind[stat.S_IFMT(x)]}},
                {'file_mode':  {'type': 'string',  'func': lambda x: '%04o' % stat.S_IMODE(x)}},
                {'file_atime': {'type': 'integer', 'func': lambda x: int(time.time() - x)}},
                {'file_mtime': {'type': 'integer', 'func': lambda x: int(time.time() - x)}},
                {'file_ctime': {'type': 'integer', 'func': lambda x: int(time.time() - x)}},
                {'file_nlink': {'type': 'integer', 'func': lambda x: x}},
                {'file_size':  {'type': 'integer', 'func': lambda x: x}},
                {'file_ino':   {'type': 'integer', 'func': lambda x: x}},
                {'file_uid':   {'type': 'integer', 'func': lambda x: x}},
                {'file_gid':   {'type': 'integer', 'func': lambda x: x}},
            ] + conf.get('items', [])

        snmpy.plugin.ValuePlugin.__init__(self, conf)

    def update(self):
        info = text = None

        try:
            if self.conf.get('use_stat'):
                info = os.lstat(self.conf['object'])
            if self.conf.get('use_text'):
                text = open(self.conf['object']).read()

            for item in self:
                if hasattr(self[item], 'func') and info:
                    self[item] = self[item].func(getattr(info, 'st_%s' % item[5:], info.st_mode))
                elif text:
                    self[item] = snmpy.parser.parse_value(text, self[item])
        except IOError as e:
            snmpy.log_error(e)
