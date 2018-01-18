#!/bin/bash

PATH=/bin:/sbin:/usr/bin:/usr/sbin

for IF in $(ls -1 "/sys/class/net/${1}/brif/" 2>/dev/null) ; do
        [ "$(ethtool -i "${IF}" | grep driver: | cut -d' ' -f2)" != "tun" ] && exec ethtool ${IF}
done

exec ethtool "${1}"
