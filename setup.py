#!/usr/bin/env python2.7

import subprocess, sys
from distutils.core import setup

def run_setup():
    try:
        git_tag = subprocess.check_output(['git', 'describe', '--tags'], stderr=open('/dev/null', 'w')).strip()
        version = git_tag.partition('snmpy.')[-1]
        if not git_tag.startswith('snmpy.') or not version:
            raise
    except Exception as e:
        print 'cannot determine version: no tags detected: %s', e
        sys.exit(1)

    try:
        vsn_lib = open('lib/__version__.py', 'w')
        vsn_lib.write("__version__ = '%s'\n" % version)
        vsn_lib.close()
    except Exception as e:
        print 'cannot write to version file: %s', e
        sys.exit(1)

    print 'setting up snmpy version %s' % version
    setup(
        author='Max Kalika',
        author_email='max@topsy.com',

        name='snmpy',
        version=version,
        scripts=['snmpy'],
        packages=['snmpy'],
        package_dir={'snmpy': 'lib'},
        data_files=[('/etc/snmpy', ['snmpy.cfg'])]
    )

if __name__ == '__main__':
    run_setup()
