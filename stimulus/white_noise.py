#!/usr/bin/env python2

import time
import random
from threading import Thread, Lock

import gst
from PyQt4.Qt import *
from PyQt4.QtGui import *

from trusas0.packing import default_packer
from trusas0.utils import get_logger

log = get_logger()

NOTIFICATION_STIMULUS='sine'
STIMULUS='gaussian-noise'

class StimulusPlayer:
	def __init__(self, stimulus='gaussian-noise'):
		# Gives 84.7dbA of white noise on Jami's system
		pipe_str = "audiotestsrc wave=%s volume=0.15 ! autoaudiosink"%(stimulus,)
		log.info("Created stimulus player: %s"%pipe_str)
		self.stimulus = stimulus
		self.pipeline = gst.parse_launch(pipe_str)
		self.pipeline.set_state(gst.STATE_PAUSED)
		self.playcount = 0
		self.state_lock = Lock()
	
	def __enter__(self):
		return self
	
	def __exit__(self, type, value, traceback):
		self.close()
	
	def play(self):
		with self.state_lock:
			log.info("Playing stimulus %s"%self.stimulus)
			if self.playcount == 0:
				self.pipeline.set_state(gst.STATE_PLAYING)

			self.playcount += 1
	
	def pause(self):
		with self.state_lock:
			log.info("Pausing stimulus %s"%self.stimulus)
			if self.playcount == 0:
				return

			self.playcount -= 1
			if self.playcount == 0:
				self.pipeline.set_state(gst.STATE_PAUSED)
	
	def play_blocking(self, duration=1.0):
		log.info("Playing stimulus %s for %f seconds"%(self.stimulus, duration))
		self.pipeline.set_state(gst.STATE_PLAYING)
		time.sleep(duration)
		self.pipeline.set_state(gst.STATE_PAUSED)
	
	def close(self):
		with self.state_lock:
			self.pipeline.set_state(gst.STATE_NULL)

def play_stimulus_once(stimulus, duration=1.0):
	with StimulusPlayer(stimulus) as player:
		player.play_blocking(duration)

def run_noise_sequence(output, duration, n_stimuli, stim_duration=1.0, pause_duration=10.0, on_done=lambda: None):
	
	seq = [0] + sorted(random.random()*duration for i in range(n_stimuli))
	delays = (seq[i] - seq[i-1] for i in range(1, len(seq)))

	
	play_stimulus_once(NOTIFICATION_STIMULUS)
	time.sleep(pause_duration)
	
	player = StimulusPlayer(STIMULUS)
	def play_once():
		player.play()
		time.sleep(stim_duration)
		player.pause()

	
	for delay in delays:
		time.sleep(delay)
		output.send({'event': "stimulus"})
		Thread(target=play_once).start()
	
	time.sleep(pause_duration)
	player.close()
	
	play_stimulus_once(NOTIFICATION_STIMULUS)
	time.sleep(pause_duration)

	on_done()

def bg_run(func):
	def runit(*args, **kwargs):
		Thread(target=lambda: func(*args, **kwargs)).start()
	
	return runit

appscopehack = None
def run_ui(*args, **kwargs):
	global appscopehack
	app = QApplication([])
	appscopehack = app
	window = QWidget()
	layout = QGridLayout(window)
	window.setLayout(layout)

	
	beeper = QPushButton("Preview beep")
	beeper.clicked.connect(lambda *args: bg_run(play_stimulus_once)(NOTIFICATION_STIMULUS))
	noiser = QPushButton("Preview noise")
	noiser.clicked.connect(lambda *args: bg_run(play_stimulus_once)(STIMULUS))
	
	cancel = QPushButton("Cancel experiment")

	layout.addWidget(beeper, 0, 0)
	layout.addWidget(noiser, 0, 1)
	
	class ThreadSyncHack(QObject):
		on_done = pyqtSignal()
	
	hack = ThreadSyncHack()
	control = QPushButton("Start experiment")

	def on_done(*args):
		output.send({'event': "experiment-end"})
		control.setText("DONE! Restart experiment")
		layout.addWidget(control, 1, 0, 1, 2)
		beeper.setDisabled(False)
		noiser.setDisabled(False)
		control.setDisabled(False)

	hack.on_done.connect(on_done)

	output = default_packer()
	def start(*args):
		duration = 15*60.0
		#duration = 10.0
		frequency = 1.0/10.0
		
		beeper.setDisabled(True)
		noiser.setDisabled(True)
		control.setDisabled(True)
		control.setText("Experiment running")
		output.send({'event': "experiment-start"})
		bg_run(run_noise_sequence)(output, duration, int(duration*frequency),
			on_done=lambda: hack.on_done.emit())

		#layout.addWidget(cancel, 1, 0, 1, 2)
		
	
	control.clicked.connect(start)
	layout.addWidget(control, 1, 0, 1, 2)

	window.show()
	app.exec_()


if __name__ == '__main__':
	run_ui()

#duration = 5*60.0
#frequency = 1.0/10.0
#run_noise_sequence(duration, int(duration*frequency))

#with NoisePlayer() as player:
#	player.play_blocking()
