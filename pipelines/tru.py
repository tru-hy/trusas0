#!/usr/bin/env python2

from os import path
import sys
# TODO: A hack
sys.path.append(path.realpath("/home/jampekka/pro"))

import trusas0.script
from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import run_ui
import logging


NEXUS_ADDR = "00:A0:96:2F:A8:A6"
VIDEO_DEVICE = "/dev/video0"
UDP_PREVIEW_PORT=5000
BASE_SESSION_DIR='/home/jampekka/tmp/sessions'

mypath=path.dirname(path.realpath(__file__))

s = ServiceSpec()

s['nexus'] = ROOT+'/nexus/physiology.py %s'%NEXUS_ADDR	
s.add(name='front_video',
	command=ROOT+'/gstreamer/uvch264record.py -u %i -v "%s"'%(UDP_PREVIEW_PORT, VIDEO_DEVICE),
	outfile="%(session_dir)s/%(name)s.mkv")

s['location'] = ROOT+'/android/location.py'
s['sensors'] = ROOT+'/android/sensors.py'


run_ui(spec=s,
	base_dir=BASE_SESSION_DIR,
	content=open(path.join(mypath, 'tru.html')).read()
	)

