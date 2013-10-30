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

    if hasattr('regex', item):
        find = re.findall(item.regex, text)

        if find:
            if item.cdef in cdef:
                return cdef[item.cdef](item.native(i) for i in find)
            else:
                return item.native(item.join.join(find))

    logging.warning('no new value found for %s', item.oidstr)
    return item.value

def parse_table(text, cols):
    pass
