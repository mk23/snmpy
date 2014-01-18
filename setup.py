#!/usr/bin/env python2.7

import glob

from setuptools import setup
from lib import VERSION

if __name__ == '__main__':
    confs = {
        '/etc/snmpy':            ['snmpy.yml'],
        '/etc/snmpy/conf.d':     [],
        '/etc/snmpy/examples.d': glob.glob('examples/*.y*ml'),
    }

    setup(
        author='Max Kalika',
        author_email='max.kalika+projects@gmail.com',
        url='https://github.com/mk23/snmpy',

        name='snmpy',
        version=VERSION,
        scripts=['snmpy'],
        packages=['snmpy', 'snmpy.plugin'],
        package_dir={'snmpy': 'lib'},
        data_files=confs.items(),
        install_requires=['yaml', 'setuptools']
    )
