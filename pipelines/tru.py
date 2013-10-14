#!/usr/bin/env python2

from os import path
import sys

from trusas0.script import sh
from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import run_ui
import logging
import os


NEXUS_ADDR = "00:A0:96:2F:A8:A6"
# This is no big secret as it's broadcasted
# in the device name
NEXUS_PIN = "0115"

BASE_SESSION_DIR=None
BASE_CACHE='/tmp/tru_basedir.txt'
try:
	with open(BASE_CACHE) as f:
		BASE_SESSION_DIR=f.read().strip()
except IOError:
	pass

if BASE_SESSION_DIR is None:
	BASE_SESSION_DIR=sh("zenity --title \\\"Base directory for sessions.\\\" --file-selection --directory").std_out.strip()

if not BASE_SESSION_DIR:
	os.exit(1)

try:
	with open(BASE_CACHE, 'w') as f:
		f.write(BASE_SESSION_DIR)
except IOError:
	pass

mypath=path.dirname(path.realpath(__file__))

s = ServiceSpec()

s['nexus'] = ROOT+'/nexus/physiology.py -p %s %s'%(NEXUS_PIN, NEXUS_ADDR)

# TODO: Find a nicer way to find the devices! This configuration working
#	 may be purely luck.
s.add(name='front_video',
	command=ROOT+'/gstreamer/uvch264record.py -u %i -v "%s" -a "%s"'%(5000, "/dev/video0", "hw:0,0"),
	outfile="%(session_dir)s/%(name)s.mkv")
s.add(name='in_video',
	command=ROOT+'/gstreamer/uvch264record.py -u %i -v "%s" -a "%s"'%(5010, "/dev/video1", "hw:1,0"),
	outfile="%(session_dir)s/%(name)s.mkv")


s['location'] = ROOT+'/android/location.py'
s['sensors'] = ROOT+'/android/sensors.py'


run_ui(spec=s,
	base_dir=BASE_SESSION_DIR,
	content=open(path.join(mypath, 'tru.html')).read()
	)

