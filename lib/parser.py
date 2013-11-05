import logging
import re

def parse_value(text, item, cdef={}):
    if not cdef:
        cdef.update({
            'min': min,
            'max': max,
            'len': len,
            'sum': sum,
            'len': len,
            'avg': lambda l: 0 if len(l) == 0 else sum(l) / len(l),
        })

    if hasattr(item, 'regex'):
        find = re.findall(item.regex, text, re.DOTALL | re.MULTILINE)

        if find:
            if item.cdef in cdef:
                return cdef[item.cdef](item.native(i) for i in find)
            else:
                return item.native(item.join.join(find))

    logging.warning('no new value found for %s', item.oidstr)
    return item.value

def parse_table(parser, text):
    if 'type' not in parser or parser['type'] not in ['regex']:
        logging.warn('invalid or missing parser type: %s', parser.get('path'))
        yield
    if 'path' not in parser or type(parser['path']) not in (str, unicode, list, tuple):
        logging.warn('invalid or missing parser path: %s', parser.get('path'))
        yield

    if parser['type'] == 'regex':
        if type(parser['path']) in (str, unicode):
            patt = parser['path']
        elif type(parser['path']) in (list, tuple):
            patt = '.*?'.join(parser['path'])

        for find in re.finditer(patt, text, re.DOTALL):
            yield find.groupdict()
