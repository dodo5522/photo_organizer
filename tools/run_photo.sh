#!/usr/bin/env bash
set -eu
sudo -u systemd-network python3 main.py -s /mnt/local/disk0/pictures/photos_new -e /usr/bin/exiftool -m

