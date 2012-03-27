#!/usr/bin/env python2.7

import re, subprocess, sys
from distutils.core import setup

def run_setup():
    try:
        version = subprocess.check_output(['git', 'describe', '--tags'], stderr=open('/dev/null', 'w')).strip()
    except:
        print 'cannot determine version: no tags detected'
        sys.exit(1)

    setup(
        author='Max Kalika',
        author_email='max@topsy.com',

        name='snmpy',
        version=re.search(r'(?P<version>[0-9]+(?:\.[0-9]*)*)$', version).group('version'),
        scripts=['snmpy'],
        packages=['snmpy'],
        package_dir={'snmpy': 'lib'},
        data_files=[('/etc/snmpy', ['snmpy.cfg'])]
    )

if __name__ == '__main__':
    run_setup()
