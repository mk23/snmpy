import hashlib
import logging
import os
import snmpy.module
import snmpy.parser
import stat


class file_value(snmpy.module.ValueModule):
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
                {'file_name':  {'type': 'string',    'func': lambda x: self.conf['object'].format(**self.conf['snmpy_extra'])}},
                {'file_type':  {'type': 'string',    'func': lambda x: self.kind[stat.S_IFMT(x)]}},
                {'file_mode':  {'type': 'string',    'func': lambda x: '%04o' % stat.S_IMODE(x)}},
                {'file_atime': {'type': 'integer64', 'func': lambda x: int(x)}},
                {'file_mtime': {'type': 'integer64', 'func': lambda x: int(x)}},
                {'file_ctime': {'type': 'integer64', 'func': lambda x: int(x)}},
                {'file_nlink': {'type': 'integer',   'func': lambda x: x}},
                {'file_size':  {'type': 'integer',   'func': lambda x: x}},
                {'file_ino':   {'type': 'integer',   'func': lambda x: x}},
                {'file_uid':   {'type': 'integer',   'func': lambda x: x}},
                {'file_gid':   {'type': 'integer',   'func': lambda x: x}},
            ] + conf.get('items', [])
        if conf.get('use_hash'):
            conf['items'].append({'file_md5': {'type': 'string'}})
            conf['items'].append({'md5_span': {'type': 'string'}})


        snmpy.module.ValueModule.__init__(self, conf)

    def md5sum(self, size):
        num = 0

        tmp = self.conf['use_hash']
        if isinstance(tmp, bool):
            lim = slice(size)
        elif isinstance(tmp, int):
            lim = slice(min(tmp, size))
        else:
            lim = slice(*(min(int(i), size) for i in tmp.split(':', 1)))

        md5 = hashlib.md5()
        with open(self.conf['object'].format(**self.conf['snmpy_extra']), 'rb') as f:
            f.seek(lim.start or 0)
            for part in iter(lambda: f.read(1024 * md5.block_size), b''):
                blob = part[:lim.stop - num]

                md5.update(blob)
                num += len(blob)

                if num >= lim.stop:
                    break

        return '%d:%d' % (lim.start or 0, lim.stop), md5.hexdigest()

    def update(self):
        text = part = hash = None
        name = self.conf['object'].format(**self.conf['snmpy_extra'])
        info = os.lstat(name)

        if self.conf.get('use_text'):
            text = open(name).read()
            logging.debug('%s: read %d bytes', name, len(text))
        if self.conf.get('use_hash'):
            part, hash = self.md5sum(info.st_size)
            logging.debug('%s: computed md5sum: %s', name, hash)

        for item in self:
            if hasattr(self[item], 'func') and info:
                self[item] = self[item].func(getattr(info, 'st_%s' % item[5:], info.st_mode))
            elif item == 'file_md5':
                self[item] = hash
            elif item == 'md5_span':
                self[item] = part
            elif text:
                self[item] = snmpy.parser.parse_value(text, self[item])
