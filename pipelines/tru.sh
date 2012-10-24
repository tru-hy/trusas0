#!/bin/bash
set -e

DST=$1

mkdir $DST

./sensors.sh $DST/sensors.repr &
./location.sh $DST/location.repr &
../gstreamer/uvch264record.py -v /dev/video0 $DST/video.mkv
