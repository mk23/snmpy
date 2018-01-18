#!/usr/bin/env python2.7

import glob

from setuptools import setup
from lib.snmpy import __version__

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
        version=__version__,
        scripts=['snmpy'] + glob.glob('scripts/*'),
        packages=['snmpy', 'snmpy.module'],
        package_dir={'snmpy': 'lib/snmpy'},
        data_files=confs.items(),
        license='LICENSE.txt',
        install_requires=['yaml', 'setuptools']
    )
