#!/bin/sh
grep -hioE '([0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}|srv[a-zA-Z0-9.]*):/[a-zA-Z0-9_/-]*' /etc/fstab /etc/auto.* /etc/mtab | sort -u

