SNMPY
=====

SNMPy extends a running [net-snmp](http://www.net-snmp.org) agent with a custom subtree made out of configurable plugin modules.

Installation
------------

Install SNMPy as a Debian package by building a `deb`:

    dpkg-buildpackage
    # or
    pdebuild

Install SNMPy using the standard `setuptools` script:

    python setup.py install


Administration
--------------

Configuration
-------------

### global settings ###
### module settings ###

#### `exec_table` ####
#### `exec_value` ####
#### `file_table` ####
#### `file_value` ####
#### `log_processor` ####
#### `process_info` ####
#### `disk_utilization` ####


Plugins
-------

SNMPy ships with several plugins ready for use, some of which are generic and can be applied toward many different use cases.  Several example configuration modules are available to demonstrate functionality.

Development
-----------

### table plugins ###

### value plugins ###

License
-------
[MIT](http://mk23.mit-license.org/2011-2014/license.html)
