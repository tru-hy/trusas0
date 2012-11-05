#!/usr/bin/env python

from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import SessionUi
from trusas0.utils import Hook, sh
import logging
from os import path


NEXUS_ADDR = "00:A0:96:2F:A8:A6"
VIDEO_DEVICE = "/dev/video0"


s = ServiceSpec()

#s['nexus'] = ROOT+'/nexus/physiology.py %s'%NEXUS_ADDR	
s['front_video'] =\
	 ROOT+'/gstreamer/uvch264record.py -v "%s" "%%(session_dir)s/%%(name)s.mkv"'%VIDEO_DEVICE
s['front_video'].extra_env['PROCNAME_HACK'] = 'trusas_front_video'

s['location'] = ROOT+'/android/location.py'
s['sensors'] = ROOT+'/android/sensors.py'


ui = SessionUi(spec=s,
	base_dir='/home/jampekka/tmp/sessions',
	content=open(path.join(path.dirname(__file__), 'tru.html')).read()
	)

logging.basicConfig(loglevel=logging.INFO)
ui.run()
	
