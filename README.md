SNMPY [![Downloads](https://img.shields.io/github/downloads/mk23/snmpy/total.svg)](https://img.shields.io/github/downloads/mk23/snmpy/total.svg) [![Release](https://img.shields.io/github/release/mk23/snmpy.svg)](https://img.shields.io/github/release/mk23/snmpy.svg) [![License](https://img.shields.io/github/license/mk23/snmpy.svg)](https://img.shields.io/github/license/mk23/snmpy.svg)
=====

SNMPy extends a running [net-snmp](http://www.net-snmp.org) agent with a custom subtree made out of configurable plugins. It makes extensive use of `libnetsnmp` C library to implement an AgentX subagent.

Table of Contents
-----------------
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Administration](#administration)
* [Configuration](#configuration)
  * [plugin settings](#plugin-settings)
* [Modules](#modules)
  * [`exec_table`](#exec_table)
  * [`exec_value`](#exec_value)
  * [`file_table`](#file_table)
  * [`file_value`](#file_value)
  * [`log_processor`](#log_processor)
  * [`filesystem_space`](#filesystem_space)
  * [`process_info`](#process_info)
  * [`raid_info`](#raid_info)
  * [`disk_utilization`](#disk_utilization)
* [Development](#development)
  * [value modules](#value-modules)
  * [table modules](#table-modules)
  * [parser](#parser)
    * [`parse_value(...)`](#parse_valuetext-item-ignorefalse)
    * [`parse_table(...)`](#parse_tableparser-text)
* [License](#license)

Prerequisites
-------------

* Python 2.7+
* Python [yaml](http://pyyaml.org) module
* Working [net-snmp](http://www.net-snmp.org) agent
* [AgentX](http://net-snmp.sourceforge.net/docs/README.agentx.html) enabled

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

SNMPy can be run in foreground or as a backgrounded daemon.  It supports logging directly to console, file, or syslog.

```
usage: snmpy [-h] [-f CONFIG_FILE] [-i INCLUDE_DIR] [-t PERSIST_DIR]
           [-r PARENT_ROOT] [-s SYSTEM_ROOT] [-l LOGGER_DEST] [-w HTTPD_PORT]
           [-p [PID_FILE]] [-m [MIB_FILE]] [-e KEY VAL] [-c]

Modular SNMP AgentX system

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIG_FILE, --config-file CONFIG_FILE
                        system configuration file
  -i INCLUDE_DIR, --include-dir INCLUDE_DIR
                        plugin configuration path
  -t PERSIST_DIR, --persist-dir PERSIST_DIR
                        plugin state persistence path
  -r PARENT_ROOT, --parent-root PARENT_ROOT
                        parent root class name
  -s SYSTEM_ROOT, --system-root SYSTEM_ROOT
                        system root object id
  -l LOGGER_DEST, --logger-dest LOGGER_DEST
                        logger destination url
  -w HTTPD_PORT, --httpd-port HTTPD_PORT
                        httpd server listens on this port
  -p [PID_FILE], --create-pid [PID_FILE]
                        daemonize and write pidfile
  -m [MIB_FILE], --create-mib [MIB_FILE]
                        display generated mib file and exit
  -e KEY VAL, --extra-data KEY VAL
                        extra key/val data for plugins
  -c, --compile-bc      compile bytecode for custom modules

supported logger formats:
  console://?level=LEVEL
  file://PATH?level=LEVEL
  syslog+tcp://HOST:PORT/?facility=FACILITY&level=LEVEL
  syslog+udp://HOST:PORT/?facility=FACILITY&level=LEVEL
  syslog+unix://PATH?facility=FACILITY&level=LEVEL
```

The system starts by reading the global configuration file. Any options provided on the command-line override the config.

* If `-m | --create-mib` was specified, it writes the generated MIB to the specified file (or `stdout` if not set or set to `-`) and exits.
* If `-p | --create-pid` was specified, it daemonizes and writes the PID to the specified file (or `/var/run/snmpy.pid` if not set) and exits.
* It then loads all plugins located in the directory specified by `-i | --include-dir` and builds an SNMP tree, initializes the agent, and enters an update loop.
* It also creates an HTTP server that currently only answers to `/mib` GET requests upon which, it will deliver the generated run-time MIB file contents.

Configuration
-------------

SNMPy configuration is [yaml](http://yaml.org) formatted.  It consists of one main file, specified by `-f | --config-file` on the command-line parameter, and many plugin configuration files located in the directory specified by `-i | --include-dir` command-line parameter or `include_dir` global setting.  These are explained below.

### global settings ###
All command-line parameters, shown above in the help screenshot, have a corresponding global setting.  For example `--parent-root` command-line parameter is `parent_root` global setting and so on.  The main configuration file must have any global settings under the `snmpy_global` top-level item in order to be recognized. i.e.

```yaml
snmpy_global:
    include_dir: '/etc/snmpy/conf.d'
    persist_dir: '/var/lib/snmpy'
    parent_root: 'ucdavis'          # .1.3.6.1.4.1.2021
    system_root: '1123'             # .1.3.6.1.4.1.2021.1123
    logger_dest: 'syslog+unix:///dev/log?facility=local1&level=DEBUG'
    create_pid:  '/var/run/snmpy.pid'
    httpd_port:  1123
    compile_bc:  True
```

* `include_dir`: location for plugin configuration files (see plugin settings below).
* `persist_dir`: location for plugin persistence data files.
* `parent_root`: SNMP object under which to install the SNMPy subtree.
* `system_root`: SNMP OID where the SNMPy subtree starts. `SNMPY-MIB::snmpyMIB` is rooted here, which can be walked to retreive all data that it manages.
* `logger_dest`: Destination for the SNMPy log. The help screen epilog provides available formats. The file destination is a watched handler so it can be safely rotated without restarting the system.
* `httpd_port`: Port to listen for http requests.  This is also used to make sure only one SNMPy process is running on a system.
* `create_pid`: Location of the PID file.  If this is specified, SNMPy will daemonize and run in the background.
* `create_mib`: This shouldn't be speicified in the config file because SNMPy will just write a MIB file and exit.  If a MIB file is needed, use the `-m | --create-mib` command-line parameter, or simply download from a running agent via HTTP.
* `compile_bc`: Enable compiling bytecode (`*.pyc`) for modules specified by absolute path (those not shipping with SNMPy itself).

        curl -s http://localhost:1123/mib # where 1123 is the configured httpd_port

### plugin settings ###
SNMPy plugin configuration begins with the filename which must meet these criteria:

1. config file names begin with a system-unique and 0-padded 4 digit number followed by underscore
1. config file names are used for subtree MIB object names
1. config file names end with `.yml` or `.yaml`

For example, with a global config above and a plugin file `/etc/snmpy/conf.d/0023_dmidecode_system.yml`, SNMP data will be made available via:

* Numeric OID: `.1.3.6.1.4.1.2021.1123.23`
* Symbolic OID: `SNMPY-MIB::snmpyDmidecodeSystem`

Every plugin configuration file must specify which module to use and how often, in minutes, to update.  Optionally, extra module-dependant configuration settings may be provided.  These are described below for each currently supported module.  At a minimum a plugin configuration file must contain these lines:

```yaml
module: # one of the modules described below
period: # refresh time in minutes or "once" for startup collection only
```

Optionally every plugin may request its state be saved between SNMPy restarts by adding a top-level `retain` boolean key:

```yaml
retain: # true | false
```

Note: retain setting is ignored if `-r | --persist-dir` command-line parameter or `persist_dir` global configuration item is disabled.

Modules
-------

SNMPy ships with several modules ready for use, some of which are generic and can be applied toward many different use cases.  Several example configuration plugins are available to demonstrate functionality.

### exec_table ###
The `exec_table` module provides tabular data from the output results of an executable command. Configuration items which must be specified are:

```yaml
module: exec_table
period: 5

object: '/path/to/command'
parser:
    type: 'regex'
    path:
        - 'First Item Pattern:\s+(?P<item_one>[^\n]+)'
        - 'Second Item Pattern:\s+(?P<item_two>[^\n]+)'
        - '(?P<other_item>(?:true|false) other item)'

table:
    - item_one:   'integer'
    - item_two:   'string'
    - other_item: 'string'
```

* `object`: Full path to executable command to run and parse output from.
* `parser`: Text parser to invoke for this plugin.
    * `type`: Currently the only type supported is `regex`, but `xml` and `json` may be supported in the future.
    * `path`: List of one or more Python [regular expressions](http://docs.python.org/3/library/re.html) that capture named groups which match column definitions (described below). Multiple matches become rows in the resulting SNMP table.
* `table`: defines the columns for this plugin.
    * item names: List of one or more columns each, specifying its type.

See [`interface_info.yml`](https://github.com/mk23/snmpy/blob/master/examples/interface_info.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyInterfaceInfo
    SNMPY-MIB::snmpyInterfaceInfoInterface.1 = STRING: "eth0"
    SNMPY-MIB::snmpyInterfaceInfoInterface.2 = STRING: "eth1"
    SNMPY-MIB::snmpyInterfaceInfoSwitchName.1 = STRING: "sw-r07-03c"
    SNMPY-MIB::snmpyInterfaceInfoSwitchName.2 = STRING: "sw-r07-03c"
    SNMPY-MIB::snmpyInterfaceInfoSwitchPort.1 = STRING: "Gi1/0/28"
    SNMPY-MIB::snmpyInterfaceInfoSwitchPort.2 = STRING: "Gi1/0/42"
    SNMPY-MIB::snmpyInterfaceInfoLinkAuto.1 = STRING: "supported/enabled"
    SNMPY-MIB::snmpyInterfaceInfoLinkAuto.2 = STRING: "supported/enabled"
    SNMPY-MIB::snmpyInterfaceInfoLinkSpeed.1 = INTEGER: 1000
    SNMPY-MIB::snmpyInterfaceInfoLinkSpeed.2 = INTEGER: 1000
    SNMPY-MIB::snmpyInterfaceInfoLinkDuplex.1 = STRING: "full duplex mode"
    SNMPY-MIB::snmpyInterfaceInfoLinkDuplex.2 = STRING: "full duplex mode"

### exec_value ###
The `exec_value` module provides simple key-value data from the output results of an executable command.  Configuration items which must be specified are:

```yaml
module: exec_value
period: 5

object: '/path/to/command'

items:
    - item_one:
          type:  'integer'
          regex: 'First Item Pattern:\s+(.+?)$'
    - item_two:
          type:  'string'
          regex: 'Second Item Pattern:\s+(.+?)$'
    - other_item:
          type:  'string'
          regex: '((?:true|false) other item)'
```

* `object`: Full path to executable command to run and parse output from.
* `items`: defines key-value pairs for this plugin.
    * item names: List of one or more item definitions.
        * `type`: SNMP type for this item
        * `regex`: Python [regular expressions](http://docs.python.org/3/library/re.html) that captures a group for this item.

See [`dmidecode_bios.yml`](https://github.com/mk23/snmpy/blob/master/examples/dmidecode_bios.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyDmidecodeBios
    SNMPY-MIB::snmpyDmidecodeBiosVendor = STRING: "innotek GmbH"
    SNMPY-MIB::snmpyDmidecodeBiosVersion = STRING: "VirtualBox"
    SNMPY-MIB::snmpyDmidecodeBiosRelease = STRING: "12/01/2006"

### file_table ###
The `file_table` module provides tabular data from the contents of a file and behaves just like the `exec_table` module except the object parameter refers to a file instead of a command.  Configuration items which must be specified are:

```yaml
module: file_table
period: 5

object: '/path/to/file'
parser:
    type: 'regex'
    path:
        - 'First Item Pattern:\s+(?P<item_one>[^\n]+)'
        - 'Second Item Pattern:\s+(?P<item_two>[^\n]+)'
        - '(?P<other_item>(?:true|false) other item)'

table:
    - item_one:   'integer'
    - item_two:   'string'
    - other_item: 'string'
```

* `object`: Full path to a file to read and parse.
* `parser`: Text parser to invoke for this plugin.
    * `type`: Currently the only type supported is `regex`, but `xml` and `json` may be supported in the future.
    * `path`: List of one or more Python [regular expressions](http://docs.python.org/3/library/re.html) that capture named groups which match column definitions (described below). Multiple matches become rows in the resulting SNMP table.
* `table`: defines the columns for this plugin.
    * item names: List of one or more columns each, specifying its type.

See [`debian_packages.yml`](https://github.com/mk23/snmpy/blob/master/examples/debian_packages.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyDmidecodeBios | grep '\.[12] ='
    SNMPY-MIB::snmpyDebianPackagesPackage.1 = STRING: "libndr0"
    SNMPY-MIB::snmpyDebianPackagesPackage.2 = STRING: "libxml-libxml-perl"
    SNMPY-MIB::snmpyDebianPackagesStatus.1 = STRING: "install"
    SNMPY-MIB::snmpyDebianPackagesStatus.2 = STRING: "install"
    SNMPY-MIB::snmpyDebianPackagesSize.1 = INTEGER: 136
    SNMPY-MIB::snmpyDebianPackagesSize.2 = INTEGER: 1005
    SNMPY-MIB::snmpyDebianPackagesArch.1 = STRING: "amd64"
    SNMPY-MIB::snmpyDebianPackagesArch.2 = STRING: "amd64"
    SNMPY-MIB::snmpyDebianPackagesVersion.1 = STRING: "4.0.3+dfsg1-0.1ubuntu1"
    SNMPY-MIB::snmpyDebianPackagesVersion.2 = STRING: "2.0010+dfsg-1"
    SNMPY-MIB::snmpyDebianPackagesDepends.1 = STRING: "libc6 (>= 2.14), libsamba-util0, libtalloc2 (>= 2.0.4~git20101213)"
    SNMPY-MIB::snmpyDebianPackagesDepends.2 = STRING: "libc6 (>= 2.14), libxml2 (>= 2.7.4), perl (>= 5.14.2-15), perlapi-5.14.2, libxml-namespacesupport-perl, libxml-sax-perl"
    SNMPY-MIB::snmpyDebianPackagesDescription.1 = STRING: "NDR marshalling library"
    SNMPY-MIB::snmpyDebianPackagesDescription.2 = STRING: "Perl interface to the libxml2 library"

### file_value ###
The `file_value` module provides simple key-value data from the contents of a file and behaves similarly to the `exec_value` module except the object parameter refers to a file instead of a command and optionally enables file metadata.  Configuration items which must be specified are:

```yaml
module: file_value
period: 5

object: '/path/to/file'
use_stat: True # or False
use_text: True # or False
use_hash: True # or False or bytes or start:bytes

items:
    - item_one:
          type:  'integer'
          regex: 'First Item Pattern:\s+(.+?)$'
    - item_two:
          type:  'string'
          regex: 'Second Item Pattern:\s+(.+?)$'
    - other_item:
          type:  'string'
          regex: '((?:true|false) other item)'
```

* `object`: Full path to a file to read and parse.
* `use_stat`: Toggles file metadata (size, dates, permissions) in the results.
* `use_hash`: Toggles file hash (md5sum) and the byte span in the results. Optionally specified by number of bytes to read or start position and number of bytes to read separated by colon.
* `use_text`: Toggles content parsing. If disabled, `items` section below is ignored.
* `items`: defines key-value pairs for this plugin.
    * item names: List of one or more item definitions.
        * `type`: SNMP type for this item
        * `regex`: Python [regular expressions](http://docs.python.org/3/library/re.html) that captures a group for this item.

See [`puppet_status.yml`](https://github.com/mk23/snmpy/blob/master/examples/puppet_status.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyPuppetStatus
    SNMPY-MIB::snmpyPuppetStatusFileName = STRING: "/var/lib/puppet/state/last_run_summary.yaml"
    SNMPY-MIB::snmpyPuppetStatusFileType = STRING: "regular file"
    SNMPY-MIB::snmpyPuppetStatusFileMode = STRING: "0644"
    SNMPY-MIB::snmpyPuppetStatusFileAtime = Counter64: 1430727085
    SNMPY-MIB::snmpyPuppetStatusFileMtime = Counter64: 1391621198
    SNMPY-MIB::snmpyPuppetStatusFileCtime = Counter64: 1401639435
    SNMPY-MIB::snmpyPuppetStatusFileNlink = INTEGER: 1
    SNMPY-MIB::snmpyPuppetStatusFileSize = INTEGER: 574
    SNMPY-MIB::snmpyPuppetStatusFileIno = INTEGER: 290787
    SNMPY-MIB::snmpyPuppetStatusFileUid = INTEGER: 1000
    SNMPY-MIB::snmpyPuppetStatusFileGid = INTEGER: 1000
    SNMPY-MIB::snmpyPuppetStatusRuntime = INTEGER: 27
    SNMPY-MIB::snmpyPuppetStatusSuccess = INTEGER: 1
    SNMPY-MIB::snmpyPuppetStatusFailure = INTEGER: 0
    SNMPY-MIB::snmpyPuppetStatusVersion = Counter64: 1391616446
    SNMPY-MIB::snmpyPuppetStatusLastRun = Counter64: 1391618985

### log_processor ###
The `log_processor` module provides simple key-value data from the contents of a constantly-appended log file, and behaves similarly to the `file_value` module except it is able to immediately react to new data as well as rotation events.  Configuration items which must be specified are:

```yaml
module: log_processor
period: 1

object: '/path/to/file'

items:
    - item_one:
          type:  'integer'
          regex: 'First Item Pattern:\s+(.+?)$'
    - item_two:
          type:  'string'
          regex: 'Second Item Pattern:\s+(.+?)$'
    - other_item:
          type:  'string'
          regex: '((?:true|false) other item)'
```

* `object`: Full path to a file to tail and parse.
* `items`: defines key-value pairs for this plugin.
    * item names: List of one or more item definitions.
        * `type`: SNMP type for this item
        * `regex`: Python [regular expressions](http://docs.python.org/3/library/re.html) that captures a group for this item.

See [`hbase_balancer.yml`](https://github.com/mk23/snmpy/blob/master/examples/hbase_balancer.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyHbaseBalancer
    SNMPY-MIB::snmpyHbaseBalancerEnabled = "true"
    $ echo '[ignored text] BalanceSwitch=false [ignored text]' >> /var/log/hbase/hbase-hbase-master-localhost.log
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyHbaseBalancer
    SNMPY-MIB::snmpyHbaseBalancerEnabled = STRING: "false"

### filesystem_space ###
The `filesystem_space` module provides per-mount point information (target path, filesystem type, source device, device id, space and inodes free, used, and total).  It optionally takes a list of filesystem types to exclude.

```yaml
module: filesystem_space
period: 1

exclude:
    - tmpfs
    - devtmpfs
```

See [`filesystem_space.yml`](https://github.com/mk23/snmpy/blob/master/examples/filesystem_space.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyFilesystemSpace | grep '\.1 ='
    SNMPY-MIB::snmpyFilesystemSpaceSource.1 = STRING: "/dev/sda1"
    SNMPY-MIB::snmpyFilesystemSpaceTarget.1 = STRING: "/"
    SNMPY-MIB::snmpyFilesystemSpaceFstype.1 = STRING: "ext4"
    SNMPY-MIB::snmpyFilesystemSpaceSpaceSize.1 = Counter64: 64891708
    SNMPY-MIB::snmpyFilesystemSpaceSpaceUsed.1 = Counter64: 12635768
    SNMPY-MIB::snmpyFilesystemSpaceSpaceFree.1 = Counter64: 48936596
    SNMPY-MIB::snmpyFilesystemSpaceInodeSize.1 = Counter64: 4128768
    SNMPY-MIB::snmpyFilesystemSpaceInodeUsed.1 = Counter64: 515662
    SNMPY-MIB::snmpyFilesystemSpaceInodeFree.1 = Counter64: 3613106

### process_info ###
The `process_info` module provides per-process information (open files, running threads, consumed memory) on the running system.  It does not need any extra configuration other than module name and refresh period:

```yaml
module: process_info
period: 1
```

See [`process_info.yml`](https://github.com/mk23/snmpy/blob/master/examples/process_info.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyProcessInfo | grep '\.1 ='
    SNMPY-MIB::snmpyProcessInfoPid.1 = INTEGER: 1
    SNMPY-MIB::snmpyProcessInfoPpid.1 = INTEGER: 0
    SNMPY-MIB::snmpyProcessInfoName.1 = STRING: "init"
    SNMPY-MIB::snmpyProcessInfoArgs.1 = STRING: "/sbin/init"
    SNMPY-MIB::snmpyProcessInfoStartTime.1 = INTEGER: 1430546101
    SNMPY-MIB::snmpyProcessInfoFdOpen.1 = INTEGER: 14
    SNMPY-MIB::snmpyProcessInfoFdLimitSoft.1 = INTEGER: 1024
    SNMPY-MIB::snmpyProcessInfoFdLimitHard.1 = INTEGER: 4096
    SNMPY-MIB::snmpyProcessInfoThrRunning.1 = INTEGER: 1
    SNMPY-MIB::snmpyProcessInfoMemResident.1 = Counter64: 1908
    SNMPY-MIB::snmpyProcessInfoMemSwap.1 = Counter64: 248
    SNMPY-MIB::snmpyProcessInfoCtxVoluntary.1 = Counter64: 8504
    SNMPY-MIB::snmpyProcessInfoCtxInvoluntary.1 = Counter64: 11167

### raid_info ###
The `raid_info` module provides per-disk information on attached RAID devices.  Besides the module name and refresh period, it requires specification for the types of RAID controllers to probe:

```yaml
module: raid_info
period: 1

type:
    - mdadm
```

Currently, only `mdadm` RAID type is supported, but `megaraid` and others may be implemented in the future.

See [`raid_info.yml`](https://github.com/mk23/snmpy/blob/master/examples/raid_info.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyRaidInfo | grep '\.[34] ='
    SNMPY-MIB::snmpyRaidInfoController.3 = STRING: "mdadm"
    SNMPY-MIB::snmpyRaidInfoController.4 = STRING: "mdadm"
    SNMPY-MIB::snmpyRaidInfoVolumeLabel.3 = STRING: "/dev/md/1"
    SNMPY-MIB::snmpyRaidInfoVolumeLabel.4 = STRING: "/dev/md/1"
    SNMPY-MIB::snmpyRaidInfoVolumeBytes.3 = Counter64: 2983016792064
    SNMPY-MIB::snmpyRaidInfoVolumeBytes.4 = Counter64: 2983016792064
    SNMPY-MIB::snmpyRaidInfoVolumeLevel.3 = INTEGER: 10
    SNMPY-MIB::snmpyRaidInfoVolumeLevel.4 = INTEGER: 10
    SNMPY-MIB::snmpyRaidInfoVolumeState.3 = STRING: "RECOVERING"
    SNMPY-MIB::snmpyRaidInfoVolumeState.4 = STRING: "RECOVERING"
    SNMPY-MIB::snmpyRaidInfoVolumeExtra.3 = STRING: "20% complete"
    SNMPY-MIB::snmpyRaidInfoVolumeExtra.4 = STRING: "20% complete"
    SNMPY-MIB::snmpyRaidInfoMemberLabel.3 = STRING: "/dev/sda3"
    SNMPY-MIB::snmpyRaidInfoMemberLabel.4 = STRING: "/dev/sdb3"
    SNMPY-MIB::snmpyRaidInfoMemberState.3 = STRING: "REBUILDING"
    SNMPY-MIB::snmpyRaidInfoMemberState.4 = STRING: "ACTIVE"

### disk_utilization ###
The `disk_utilization` module provides per-disk device utilization as a percentage as reported by the [`sar`](http://sebastien.godard.pagesperso-orange.fr/man_sar.html) command from the [`sysstat`](http://sebastien.godard.pagesperso-orange.fr) package and requires collections to be operational.  It has two optional parameters that specify the location of the command and the path to the database:

```yaml
module: disk_utilization
period: 15

sar_command: '/usr/bin/sar'
sysstat_log: '/var/log/sysstat/sa%02d'
```

See [`disk_utilization.yml`](https://github.com/mk23/snmpy/blob/master/examples/disk_utilization.yml) example plugin:

    $ curl -s -o snmpy.mib http://localhost:1123/mib
    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyDiskUtilization | grep '\.3 ='
    SNMPY-MIB::snmpyDiskUtilizationDev.3 = STRING: "sda1"
    SNMPY-MIB::snmpyDiskUtilizationWait.3 = INTEGER: 0
    SNMPY-MIB::snmpyDiskUtilizationUtil.3 = INTEGER: 0

Development
-----------

Custom module development requires subclassing either `snmpy.module.ValueModule` or `snmpy.module.TableModule` and, at a minimum, implementing the `update()` method.  There are several provided utilities for logging and text parsing that are also available to use. Both table and value classes inherit from a base `snmpy.module.Module` class that handles saving plugin state on update if requested by configuration.  They also handle all the low-level SNMP and AgentX object tracking so the higher level modules can focus on simply collecting the requisite data.

### value modules ###

The most basic value module, named `example_value_module.py`, must start with this skeleton code located in the system's `module` directory:

```python
import snmpy.module

class example_value_module(snmpy.module.ValueModule): # class name must match file name
    def update(self):
        pass
```

This starting point will allow a MIB to be generated and the system to start, but otherwise, no data will be collected or returned.  The module may define its own items or allow the end user to specify them in the config (see [`exec_value`](#exec_value) documentation above for an example of config-supplied items).

For this example, lets implement a module that simply counts the number of times it has been updated, and also calculates the estimated runtime as an integer and as a human-readable string.  Configuration for this module will be very simple since items will be defined in code rather than config and no retention is needed:

```yaml
module: example_value_module
period: 1
```

First, we need to override the `__init__()` method to define our items and start the counter.  The system initializer passes the plugin configuration as the only parameter when instantiating the module class.  Our method must extend the plugin configuration with items we want the system to expose, call the superclass initializer, and start the counter.  The parent class handles creating all the necessary SNMP hooks and implements methods that allow us to just assign values to `self` by using the standard `dict` key accessors.

```python
    def __init__(self, conf):
        conf['items'] = [
            {'update_counter': {'type': 'integer'}},
            {'uptime_minutes': {'type': 'integer'}},
            {'uptime_verbose': {'type': 'string'}},
        ]

        snmpy.module.ValueModule.__init__(self, conf)
        self['update_counter'] = 0
```

Next we implement the `update()` method to update our internal data for the system to expose to SNMP requests. There is a call to `self.format()` which is implemented in the full example below.

```python
    def update(self):
        self['update_counter'] = self['update_counter'].value + 1
        self['uptime_minutes'] = self['update_counter'].value * self.conf['period']
        self['uptime_verbose'] = self.format()
```

Once the module is created and the configuration file installed, we can see it in action.

    $ curl -s -o snmpy.mib http://localhost:1123/mib

    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyExampleValueModule
    SNMPY-MIB::snmpyExampleValueModuleUpdateCounter = INTEGER: 1
    SNMPY-MIB::snmpyExampleValueModuleUptimeMinutes = INTEGER: 1
    SNMPY-MIB::snmpyExampleValueModuleUptimeVerbose = STRING: "0 years, 0 days, 0 hours, 1 minute"

    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyExampleValueModule
    SNMPY-MIB::snmpyExampleValueModuleUpdateCounter = INTEGER: 4
    SNMPY-MIB::snmpyExampleValueModuleUptimeMinutes = INTEGER: 4
    SNMPY-MIB::snmpyExampleValueModuleUptimeVerbose = STRING: "0 years, 0 days, 0 hours, 4 minutes"

    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyExampleValueModule
    SNMPY-MIB::snmpyExampleValueModuleUpdateCounter = INTEGER: 36
    SNMPY-MIB::snmpyExampleValueModuleUptimeMinutes = INTEGER: 36
    SNMPY-MIB::snmpyExampleValueModuleUptimeVerbose = STRING: "0 years, 0 days, 0 hours, 36 minutes"

And here is the final full version of our new example value module.

```python
import snmpy.module

class example_value_module(snmpy.module.ValueModule):
    def __init__(self, conf):
        conf['items'] = [
            {'update_counter': {'type': 'integer'}},
            {'uptime_minutes': {'type': 'integer'}},
            {'uptime_verbose': {'type': 'string'}},
        ]

        snmpy.module.ValueModule.__init__(self, conf)
        self['update_counter'] = 0

    def update(self):
        self['update_counter'] = self['update_counter'].value + 1
        self['uptime_minutes'] = self['update_counter'].value * self.conf['period']
        self['uptime_verbose'] = self.format()

    def format(self):
        m = self['uptime_minutes'].value

        y, m = divmod(m, 525949)
        d, m = divmod(m, 1440)
        h, m = divmod(m, 60)

        return '%d year%s, %d day%s, %d hour%s, %d minute%s' % (
            y, 's' if y != 1 else '',
            d, 's' if d != 1 else '',
            h, 's' if h != 1 else '',
            m, 's' if m != 1 else ''
        )
```

### table modules ###

The most basic table module, named `example_table_module.py`, must start with this skeleton code located in the system's `module` directory:

```python
import snmpy.module

class example_table_module(snmpy.module.TableModule): # class name must match file name
    def update(self):
        pass
```

This starting point will allow a MIB to be generated and the system to start, but otherwise no data will be collected or returned.  The module may define its own column types or allow the end user to specify them in the config (see [`exec_table`](#exec_table) documenation above for an example of config-supplied table).

For this example, lets implement a module that reaches out to a url, collects all HTML tag names as column one and their occurance counts on the page as column two.  Configuration for this module will be mostly basic, but also allow the user to specify a URL to fetch and parse.

```yaml
module: example_table_module
period: 1

object: http://github.com/mk23/snmpy
```

Besides the basic import we'll need a few extra utilities for fetching, parsing, and counting:

```python
import collections
import re
import requests
```

On to actual code.  First, we need to override the `__init__()` method to define our table.  The system initializer passes the plugin configuration as the only parameter when instantiating the module class.  Our method must extend the plugin configuration with the table we want to expose and call the superclass initializer.  The parent class handles creating all necessary SNMP hooks and implements methods that allow us to call `self.append(row)` where row is a list of values corresponding to the columns defined in the initializer.  There are two ways to define a table

1. A list of dictionaries specifying a mapping of column name to column type.  i.e. `[ {'col': 'integer'} ]`
2. A list of dictionaries specifying a mapping of column name to a dictionary of attributes, one of which is `type`.  i.e. `[ {'col': {'type': 'string', 'attr': 'info'}} ]`

For this module we'll choose the simple method:

```python
    def __init__(self, conf):
        conf['table'] = [
            {'tag':   'string'},
            {'count': 'integer'},
        ]

        snmpy.module.TableModule.__init__(self, conf)
```

Next we implement the `update()` method to update our internal data for the system to expose to SNMP requests.  In this method, we fetch the contents of the configured URL, parse it via simple regex, and count using a python [`collections.Counter`](https://docs.python.org/2/library/collections.html#collections.Counter) library.  The results are then appended as rows one at a time.

```python
    def update(self):
        data = requests.get(self.conf['object'])
        data.raise_for_status()

        find = re.findall(r'<(?P<tag>[a-z]+).+?>', data.content, re.I)
        if find:
            for item in sorted(collections.Counter(find).items()):
                self.append(item)
```

Once the module is created and the configuration file installed, we can see it in action.

    $ curl -s -o snmpy.mib http://localhost:1123/mib

    $ snmpwalk -m +./snmpy.mib -v2c -cpublic localhost SNMPY-MIB::snmpyExampleTableModule | grep '\.[1-5] ='
    SNMPY-MIB::snmpyExampleTableModuleTag.1 = STRING: "a"
    SNMPY-MIB::snmpyExampleTableModuleTag.2 = STRING: "body"
    SNMPY-MIB::snmpyExampleTableModuleTag.3 = STRING: "div"
    SNMPY-MIB::snmpyExampleTableModuleTag.4 = STRING: "form"
    SNMPY-MIB::snmpyExampleTableModuleTag.5 = STRING: "h"
    SNMPY-MIB::snmpyExampleTableModuleCount.1 = INTEGER: 44
    SNMPY-MIB::snmpyExampleTableModuleCount.2 = INTEGER: 1
    SNMPY-MIB::snmpyExampleTableModuleCount.3 = INTEGER: 80
    SNMPY-MIB::snmpyExampleTableModuleCount.4 = INTEGER: 2
    SNMPY-MIB::snmpyExampleTableModuleCount.5 = INTEGER: 3

And here is the final full version of our new example table module.

```python
import collections
import re
import requests
import snmpy.module

class example_table_module(snmpy.module.TableModule):
    def __init__(self, conf):
        conf['table'] = [
            {'tag':   'string'},
            {'count': 'integer'},
        ]

        snmpy.module.TableModule.__init__(self, conf)

    def update(self):
        data = requests.get(self.conf['object'])
        data.raise_for_status()

        find = re.findall(r'<(?P<tag>[a-z]+).+?>', data.content, re.I)
        if find:
            for item in sorted(collections.Counter(find).items()):
                self.append(item)
```

### parser ###

The `snmpy.parser` module is a collection of two utility functions to make text parsing into native values easier.  Based on standard configuration for values and tables, custom modules make calls to `parse_value` or `parse_table` to extract configured elements into internal data representation. Examples of these standard configuration items are described above in [`exec_value`](#exec_value) and [`exec_table`](#exec_table) built-in module documentation.

#### `parse_value(text, item, ignore=False)` ####

Method for extracting and returning a single element from `text`.  The `item` to be extracted, an instance of `snmpy.module.ModuleItem` class, has attributes describing its identifying regex, its native type to convert to, and optionally a consolidation function (cdef) if more than one result is found in text.  If multiple results are found, but no cdef is specified, the results are joined using the value of the item's join attribute.

Supported cdefs:

* min: return minimum of extracted results
* max: return maximum of extracted results
* len: return number of extracted results
* sum: return summation of extracted results
* avg: return average of extracted results

#### `parse_table(parser, text)` ####

Generator for extracting and yielding dictionaries from `text`, one per row where the keys are the associated column names.  The `parser` itself is a dictionary that specifies the type and path of the elements to extract.  Currently the only type supported is `regex`, but `xml` and `json` may be supported in the future.  The path is either a single regex string containing patterns of all columns to extract, or a list of regexes that are used together.

License
-------
[MIT](http://mk23.mit-license.org/2011-2018/license.html)
