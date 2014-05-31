#!/bin/bash -e

cd $(dirname $(readlink -e $0))
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "${BRANCH}" = "HEAD" ] ; then
	echo "Cannot release on detached HEAD.  Please switch to a branch."
	exit 1
fi

read -p "Would you like to commit ${BRANCH} branch? [y/N] " -r
if [[ $REPLY =~ ^[Yy]$ ]] ; then
	COMMIT=--commit
fi

echo
/usr/bin/curl -L -s https://raw.github.com/mk23/sandbox/master/misc/release.py | exec /usr/bin/env python2.7 - ${COMMIT} --release stable -e lib/__init__.py "VERSION = '{version}'" $@

if [ -n "${COMMIT}" ] ; then
	echo
	TAG=$(git describe --abbrev=0 --tags)
	echo "Created tag ${TAG}"

	read -p "Would you like to push? [y/N] " -r
	if [[ $REPLY =~ ^[Yy]$ ]] ; then
	    git push origin $BRANCH
	    git push origin $TAG
	fi
fi
