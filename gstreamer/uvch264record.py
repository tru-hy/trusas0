#!/usr/bin/env python
"""
An application to record from UVC cameras supporting h264 encoding with
UTC timestamping for global synchronization.
"""
import sys
import argh

import pygst; pygst.require("0.10")
# Pygst loves to grab the argv, so give the
# greedy bastard nothing
args, sys.argv = sys.argv, []; import gst; sys.argv = args
import gobject
#from trusas0.utils import sh
import logging; log = logging.getLogger(__name__)
import time
import datetime

def ts_to_srt(stamp):
	t = datetime.timedelta(seconds=stamp)
	return str(t)

"""
class TimestampSource(gst.BaseSrc):
	__gsttemplates__ = (
		gst.PadTemplate("src",
			gst.PAD_SRC,
			gst.PAD_ALWAYS,
			gst.caps_from_string("text/plain; text/x-raw")),
    		)

	__gstdetails__ = ("ts_txt_src", "Subtitle/Source",
		"Gives out current timestamp as text",
		"Jami Pekkanen <jami.pekkanen@helsinki.fi>")

	def __init__(self):
		self.__gobject_init__()
		#self.set_live(True)
		self.set_format(gst.FORMAT_TIME)
		self.sample_duration = 1000*gst.MSECOND
		self._should_stop = False
		self.latency = 0
		self.set_blocksize(1)

	def is_seekable(self): return False
	
	def check_get_range(self): return False

	def do_stop(self):
		self._should_stop = True
		return True
	
	def do_event(self, event):
		if event.type == gst.EVENT_LATENCY:
			self.latency = event.parse_latency()
		

	def do_send_event(self, event):
		if event.type == gst.EVENT_EOS:
			self._should_stop = True
	
	def do_unlock(self):
		# What to do here?
		self.warning("UNLOCKING")
		#self._should_stop = True
		self.set_locked_state(True)

	def do_unlock_stop(self):
		# What to do here?
		self.warning("UNLOCK_STOPPING")

	
	#def do_get_times(self, buf):
	#	# Should we account for latency here?
	#	return buf.timestamp - self.latency, buf.timestamp + buf.duration - self.latency
	
	def do_create(self, *args):
		# Create doesn't get called after the EOS is sent.
		# How to tell the BaseSrc/pipeline that we want to
		# EOS?
		#
		# Can I somehow instruct BaseSrc to call this only when
		# the previous buffer's timestamp + duration is about to
		# approach? Now it seems to send a "burst" of queries every
		# interval and we have no way to not send a buffer.
		
		
		if self._should_stop:
			return gst.FLOW_UNEXPECTED
		
		clock = self.get_clock()
		
		if not clock:
			buf = gst.Buffer("")
			buf.timestamp = 0
			buf.duration = self.sample_duration
			return gst.FLOW_OK, buf

		abstime = clock.get_time() - self.latency
		running_time = abstime - self.get_base_time()
		
		gmt = time.gmtime(int(abstime/float(gst.SECOND)))
		abstime_str = time.strftime("%Y-%m-%d %H:%M:%S", gmt)
		abstime_str += "." + str(abstime%gst.SECOND)

		runtime_s = running_time/float(gst.SECOND)
		sub_str = "%s\n%s"%(abstime_str, ts_to_srt(runtime_s))
		
		buf = gst.Buffer(sub_str)
		buf.timestamp = running_time
		buf.duration = self.sample_duration
		
		
		return gst.FLOW_OK, buf
"""


from threading import Thread, Condition
class TimestampSource(gst.Element):
	__gsttemplates__ = (
		gst.PadTemplate("src",
			gst.PAD_SRC,
			gst.PAD_ALWAYS,
			gst.caps_from_string("text/plain")),
    		)

	__gstdetails__ = ("ts_txt_src", "Subtitle/Source",
		"Gives out current timestamp as text",
		"Jami Pekkanen <jami.pekkanen@helsinki.fi>")

	def __init__(self):
		self.__gobject_init__()
		self.sample_duration = 50*gst.MSECOND
		self._should_stop = False
		
		self.create_all_pads()
		self.pad = self.get_pad("src")
		self.pad.set_event_function(self.do_event_handler)
		
		self.task = Thread(target=self._send_buffers)
		self._runlock = Condition()
		self._runlock.acquire()
		self.task.start()

	def do_send_event(self, event):
		print "EVENT!!"	
	
	def send_event(self, event):
		print "EVENT!!"	

	def do_event_handler(self, *args):
		print "EVENT!!"

	def _send_buffers(self):
		sleeptime = self.sample_duration/float(gst.SECOND)
		while True:
			self._runlock.acquire()
			while True:
				#if not self.get_clock(): continue
				self._runlock.wait(sleeptime)
				state, buf = self.do_create()
				result = self.pad.push(buf)
				#print result
				
		
	def do_change_state(self, tr):
		print tr
		if tr == gst.STATE_CHANGE_READY_TO_PAUSED:
			return gst.STATE_CHANGE_NO_PREROLL
		elif tr == gst.STATE_CHANGE_PAUSED_TO_PLAYING:
			self._runlock.release()

		return gst.STATE_CHANGE_SUCCESS

	def do_create(self, *args):
		# Create doesn't get called after the EOS is sent.
		# How to tell the BaseSrc/pipeline that we want to
		# EOS?
		#
		# Can I somehow instruct BaseSrc to call this only when
		# the previous buffer's timestamp + duration is about to
		# approach? Now it seems to send a "burst" of queries every
		# interval and we have no way to not send a buffer.
		
		if self._should_stop:
			return gst.FLOW_UNEXPECTED

		clock = self.get_clock()

		abstime = clock.get_time()
		running_time = abstime - self.get_base_time()
		
		gmt = time.gmtime(int(abstime/float(gst.SECOND)))
		abstime_str = time.strftime("%Y-%m-%d %H:%M:%S", gmt)
		abstime_str += "." + str(abstime%gst.SECOND)

		runtime_s = running_time/float(gst.SECOND)
		sub_str = "%s\n%s"%(abstime_str, ts_to_srt(runtime_s))
		
		buf = gst.Buffer(sub_str)
		buf.timestamp = running_time
		buf.duration = self.sample_duration
		
		return gst.FLOW_OK, buf

gobject.type_register(TimestampSource)
gst.element_register(TimestampSource, "ts_src", 0)

@argh.command
def record(output_file, video_device=None, audio_device=None):
	"""Record from uvch264 device"""
	pipe_str = \
		'matroskamux name=mux ! queue ! ' \
			'filesink location="%(output_file)s" ' \
		%{'output_file': output_file}
	
	pipe_str += 'ts_src name=ts_src ! queue ! tee name=ts_tee ts_tee. ! text/plain ! mux. '
	pipe_str += 'textoverlay name=preview halignment=left line-alignment=left ! xvimagesink '
	
	if not video_device:
		pipe_str += "videotestsrc ! preview. "
	else:
		# Disable autofocus
		#sh("v4l2-ctl -d /dev/video0 -c focus_auto=0")
		#sh("v4l2-ctl -d /dev/video0 -c focus_absolute=0")
		
		pipe_str += \
		' uvch264_src device=%(video_device)s auto-start=true name=src ' \
			'fixed-framerate=true initial-bitrate=5000000 ' \
			'src.vidsrc ! video/x-h264,width=1920,height=1080,framerate=30/1 ! ' \
			'queue ! h264parse ! mux. ' \
		'src.vfsrc ! video/x-raw-yuv,framerate=30/1 ! queue ! preview. ' \
		% {'video_device': video_device}
	
	pipe_str += 'ts_tee. ! preview.text_sink '
	# TODO: Audio disabled to get a system clock
	#if audio_device:
	#	pipe_str += ' alsasrc device="%s" ! queue ! voaacenc !  mux.'%audio_device
	
	logging.info("Launching pipeline %s"%pipe_str)
	pipeline = gst.parse_launch(pipe_str)
	clock = pipeline.get_clock()
	clock.set_property("clock-type", 0) # Set to gst.CLOCK_TYPE_REALTIME
	mainloop = gobject.MainLoop()
	
	ts_src = pipeline.get_by_name('ts_src')

	#print ts_src
	#print "\n".join(dir(ts_src))

	log_level_map = {
		gst.MESSAGE_EOS: log.info,
		gst.MESSAGE_INFO: log.info,
		gst.MESSAGE_STATE_CHANGED: log.info,
		gst.MESSAGE_WARNING: log.warning,
		gst.MESSAGE_ERROR: log.error,
		}
	

	def on_message(bus, message):
		t = message.type
		log_func = log_level_map.get(t,
			lambda obj: log.debug("Unknown gstreamer message: %s"%obj))
		log_func(message)
		
	def shutdown():
		pipeline.send_event(gst.event_new_eos())
	
	def on_error(bus, error):
		shutdown()

	def on_eos(bus, eos):
		mainloop.quit()

	
	bus = pipeline.get_bus()
	bus.add_signal_watch()
	bus.connect("message", on_message)
	bus.connect("message::error", on_error)
	bus.connect("message::eos", on_eos)

	def start():	
		#pipeline.set_state(gst.STATE_READY)
		#pipeline.set_state(gst.STATE_PAUSED)
		pipeline.set_state(gst.STATE_PLAYING)
		return False

	gobject.threads_init()
	gobject.idle_add(start)
	mainloop.run()
	pipeline.set_state(gst.STATE_NULL)


def main(argv):
	import signal; signal.signal(signal.SIGINT, signal.SIG_DFL)
	parser = argh.ArghParser()
	
	# Hacking to disable the subcommand stuff.
	# See: https://bitbucket.org/neithere/argh/issue/13/
	subparser = parser.add_commands([argh.alias('')(record)])
	parser.dispatch(argv=['']+argv)

if __name__ == '__main__':
	logging.basicConfig(level=logging.WARNING)
	main(sys.argv[1:])
	
