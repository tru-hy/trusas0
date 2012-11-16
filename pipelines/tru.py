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
NEXUS_PIN = 0115

BASE_SESSION_DIR=os.getenv("TRUSAS_BASE_DIR")

if BASE_SESSION_DIR is None:
	BASE_SESSION_DIR=sh("zenity --title \\\"Base directory for sessions.\\\" --file-selection --directory").std_out.strip()

mypath=path.dirname(path.realpath(__file__))

s = ServiceSpec()

s['nexus'] = ROOT+'/nexus/physiology.py -p %i %s'%(NEXUS_PIN, NEXUS_ADDR)

s.add(name='front_video',
	command=ROOT+'/gstreamer/uvch264record.py -u %i -v "%s"'%(5000, "/dev/video0"),
	outfile="%(session_dir)s/%(name)s.mkv")
s.add(name='in_video',
	command=ROOT+'/gstreamer/uvch264record.py -u %i -v "%s"'%(5010, "/dev/video1"),
	outfile="%(session_dir)s/%(name)s.mkv")


s['location'] = ROOT+'/android/location.py'
s['sensors'] = ROOT+'/android/sensors.py'


run_ui(spec=s,
	base_dir=BASE_SESSION_DIR,
	content=open(path.join(mypath, 'tru.html')).read()
	)

