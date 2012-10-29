#!/bin/bash
set -e

DST=$1
NEXUS_ADDR="00:A0:96:2F:A8:A6"

mkdir $DST

./sensors.sh $DST/sensors.repr &
./location.sh $DST/location.repr &
./nexus.sh $NEXUS_ADDR $DST/physiology.repr &
../gstreamer/uvch264record.py -v /dev/video0 $DST/video.mkv
