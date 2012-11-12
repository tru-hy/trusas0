#!/usr/bin/env python

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

mypath=path.dirname(path.realpath(__file__))

s = ServiceSpec()

s['nexus'] = ROOT+'/nexus/physiology.py %s'%NEXUS_ADDR	
s.add(name='front_video',
	command=ROOT+'/gstreamer/uvch264record.py -v "%s"'%VIDEO_DEVICE,
	outfile="%(session_dir)s/%(name)s.mkv")
s['front_video'].extra_env['PROCNAME_HACK'] = 'trusas_front_video'

s['location'] = ROOT+'/android/location.py'
s['sensors'] = ROOT+'/android/sensors.py'


run_ui(spec=s,
	base_dir='/home/jampekka/tmp/sessions',
	content=open(path.join(mypath, 'tru.html')).read()
	)

