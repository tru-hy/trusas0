from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import SessionUi
from trusas0.utils import Hook, sh
import logging
import subprocess


NEXUS_ADDR = "00:A0:96:2F:A8:A6"
VIDEO_DEVICE = "/dev/video0"


s = ServiceSpec()

#s['nexus'] = ROOT+'/nexus/physiology.py %s'%NEXUS_ADDR	
s['front_video'] =\
	 ROOT+'/gstreamer/uvch264record.py -v "%s" "%%(session_dir)s/%%(name)s.mkv"'%VIDEO_DEVICE
s['front_video'].extra_env['PROCNAME_HACK'] = 'trusas_front_video'

s['location'] = ROOT+'/android/location.py'

ui = SessionUi(s, '/home/jampekka/tmp/sessions')
ui.swallow['trusas_front_video'] = "Front video"


#start_hook = s.start_service = Hook(s.start_service)

def hook_manager(manager, *args, **kwargs):
	print "Hooking manager"
	manager.start_service = Hook(manager.start_service)
	manager.start_service.after.connect(
		lambda pid, name: start_visualization(manager, name))

visualizations = {
	'location': (
		'trusas_map',
		"tail -f %(outfile)s |%(ROOT)s/plot/location_plotter.py -w trusas_map",
		'Location')
	}

def start_visualization(manager, name):
	if name not in visualizations:
		return

	win_name, command, human_name = visualizations[name]
	ui.swallow[win_name] = human_name
	command = command%dict(outfile=manager.services[name].outfile, ROOT=ROOT)
	subprocess.Popen(command, shell=True)

def swallow_visualization(manager, name):
	if name not in visualizations:
		return
	win_name, command, human_name = visualizations[name]
	ui.swallow[win_name]

s.instance = Hook(s.instance)
s.instance.after.connect(hook_manager)

logging.basicConfig(loglevel=logging.INFO)
ui.run()
	
