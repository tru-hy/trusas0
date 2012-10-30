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
import logging; log = logging.getLogger(__name__)
import time
import datetime
import signal

def ts_to_srt(stamp):
	t = datetime.timedelta(seconds=stamp)
	return str(t)

class TimestampSource(gst.Element):
	_sinkpadtemplate = gst.PadTemplate("sink",
					gst.PAD_SINK,
					gst.PAD_ALWAYS,
					gst.caps_new_any())
	
	_srcpadtemplate = gst.PadTemplate("src",
					gst.PAD_SRC,
					gst.PAD_ALWAYS,
					gst.caps_new_any())

	__gsttemplates__ = (gst.PadTemplate("text_src%d",
					gst.PAD_SRC,
					gst.PAD_REQUEST,
					gst.caps_from_string("text/plain")),)


	__gstdetails__ = ("ts_txt_src", "Subtitle/Source",
		"Gives out current timestamp as text",
		"Jami Pekkanen <jami.pekkanen@helsinki.fi>")


	def __init__(self):
		gst.Element.__init__(self)

		self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
		self.sinkpad.set_chain_function(self.chainfunc)
		self.sinkpad.set_event_function(self.eventfunc)
		self.add_pad(self.sinkpad)

		self.srcpad = gst.Pad(self._srcpadtemplate, "src")
		self.srcpad.set_event_function(self.srceventfunc)
		self.srcpad.set_query_function(self.srcqueryfunc)
		self.add_pad(self.srcpad)

		self.text_pads = []

	def chainfunc(self, pad, buffer):
		self.push_timestamp(buffer)
		return self.srcpad.push(buffer)
	
	def do_request_new_pad(self, template, name):
		pad = gst.Pad(template, name)
		self.add_pad(pad)
		self.text_pads.append(pad)
		return pad

	def push_timestamp(self, buffer):
		
		running_time = buffer.timestamp
		abstime = running_time + self.get_base_time()
		
		gmt = time.gmtime(int(abstime/float(gst.SECOND)))
		abstime_str = time.strftime("%Y-%m-%d %H:%M:%S", gmt)
		abstime_str += "." + str(abstime%gst.SECOND)

		runtime_s = running_time/float(gst.SECOND)
		sub_str = "%s\n%s"%(abstime_str, ts_to_srt(runtime_s))
		
		buf = gst.Buffer(sub_str)
		buf.timestamp = buffer.timestamp
		buf.duration = buffer.duration
		
		for pad in self.text_pads:
			pad.push(buf)

	def eventfunc(self, pad, event):
		return self.srcpad.push_event(event)
		
	def srcqueryfunc (self, pad, query):
		return self.sinkpad.query(query)
	def srceventfunc (self, pad, event):
		return self.sinkpad.push_event(event)

gobject.type_register(TimestampSource)
gst.element_register(TimestampSource, "ts_src", 0)

@argh.command
def record(output_file, video_device=None, audio_device=None):
	"""Record from uvch264 device"""
	pipe_str = ""
	pipe_str = \
		'matroskamux name=mux ! queue ! ' \
			'filesink location="%(output_file)s" ' \
		%{'output_file': output_file}
	
	pipe_str += 'textoverlay name=preview halignment=left line-alignment=left ! colorspace ! ' \
		'xvimagesink force-aspect-ratio=true sync=false '
	pipe_str += 'ts_src.text_src0 ! text/plain ! queue ! mux. ' 
	pipe_str += 'ts_src.text_src1 ! text/plain ! queue ! preview.text_sink ' 
	pipe_str += 'ts_src name=ts_src ts_src.src ! queue ! preview. '
	

	if not video_device:
		pipe_str += "videotestsrc name=video_src ! ts_src.sink "
		pipe_str += "videotestsrc ! mux. "
	else:
		from trusas0.utils import sh
		# Disable autofocus
		sh("v4l2-ctl -d /dev/video0 -c focus_auto=0")
		sh("v4l2-ctl -d /dev/video0 -c focus_absolute=0")
		
		pipe_str += \
		' uvch264_src device=%(video_device)s auto-start=true name=video_src ' \
			'fixed-framerate=true initial-bitrate=50000000 ' \
			'video_src.vidsrc ! video/x-h264,width=1920,height=1080,framerate=30/1 ! h264parse ! tee name=vidtee ' \
			'vidtee.src0 ! queue ! mux. ' \
		'vidtee.src1 ! queue ! vdpauh264dec ! video/x-raw-yuv ! ts_src.sink ' \
		% {'video_device': video_device}
	
	
	#pipe_str += 'ts_tee. ! preview.text_sink '
	#pipe_str += 'ts_src. ! preview.text_sink '
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
		# This should work:
		# pipeline.send_event(gst.event_new_eos())
		# But because the gstreamer EOS stuff seems to be FUBAR,
		# force the EOS to all pads
		for element in pipeline.recurse():
			for pad in element.pads():
				if pad.get_property("direction") != gst.PAD_SINK:
					continue
				pad.send_event(gst.event_new_eos())

	
	def on_error(bus, error):
		shutdown()

	def on_eos(bus, eos):
		mainloop.quit()

	
	bus = pipeline.get_bus()
	bus.add_signal_watch()
	bus.connect("message", on_message)
	bus.connect("message::error", on_error)
	bus.connect("message::eos", on_eos)
	

	gobject.threads_init()
	pipeline.set_state(gst.STATE_PLAYING)
	try:
		mainloop.run()
	except KeyboardInterrupt:
		shutdown()

	pipeline.set_state(gst.STATE_NULL)


def main(argv):
	parser = argh.ArghParser()
	
	# Hacking to disable the subcommand stuff.
	# See: https://bitbucket.org/neithere/argh/issue/13/
	subparser = parser.add_commands([argh.alias('')(record)])
	parser.dispatch(argv=['']+argv)

if __name__ == '__main__':
	logging.basicConfig(level=logging.WARNING)
	main(sys.argv[1:])
	
