#!/usr/bin/env python2
"""
An application to record from UVC cameras supporting h264 encoding with
UTC timestamping for global synchronization.

:todo: The uvch264_src crashes when using the viewfinder. The current workaround
	is not to take the viewfinder data at all, but to decode the h264 stream
	on the fly (with VDPAU not to kill the whole system).
:todo: As a workaround to a problem in above workaround, the vdpausink crashes
	due to some X threading stuff, so we have to use an xvimagesink, which
	of course drains about half a core in my system.
:todo: v4l2src also allows getting the h264 stream, but it doesn't seem to work with
	vdpauh264dec due to some profile problems, so we are for now stuck with
	uvch264_src and thus Gstreamer 0.10. A sad cascade of hacks and workarounds.
	Update: Gstreamer 1.0's v4l2src won't output h264 at all :(
:todo: See if there's a nice way to separate the recording from the output, as
	the current implementation is against the trusas-principle of separation
	between recording and visualization. A perhaps feasible solution would
	be to use v4l2loopback or somehow convice v4l2 to get the preview-stream
	from an another process. The most principled method would be to stream
	from the output file, but this will probably cause problems, at least
	because the matroska mux/demux-pair isn't very friendly for playing
	unfinished files.
:todo: Switch back to mpegts and store the sync externally. All these problems
	just aren't worth it.
"""
import sys
import argh
import os

import pygst; pygst.require("0.10")

# Pygst loves to grab the argv, so give the
# greedy bastard nothing
args, sys.argv = sys.argv, []; import gst; sys.argv = args
import gobject
from trusas0.utils import get_logger; log = get_logger()
import time
import datetime
import signal

def ts_to_srt(stamp):
	t = datetime.timedelta(seconds=stamp)
	return str(t)

class TimestampSource(gst.Element):
	"""
	TODO: The architecture is ugly like this because
		a lot of confusion about gstreamer's event
		propagation. Using the request templates isn't
		probably necessary as tee would do the same trick.
	"""
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
def record(output_file="/dev/stdout", udp_h264_port=None, video_device=None, audio_device=None):
	"""
	Record from uvch264 device

	TODO: /dev/stdout may not be the most portable way for outputting
		to stdout

	TODO: There are some overlapping timestamps on playback on many players,
		which is a bit annoying. It may be because the ts_src is hooked to
		the decoded stuff, which probably also increases the latency/jitter
		of the timestamps? Shouldn't be too hard to fix.
	"""

		
	pipe_str = ""
	pipe_str = \
		'matroskamux name=mux ! queue ! ' \
			'filesink location="%(output_file)s" ' \
		%{'output_file': output_file}
	
	pipe_str += 'ts_src name=ts_src '
	pipe_str += 'ts_src.text_src0 ! text/plain ! queue ! mux. ' 
	

	if not video_device:
		pipe_str += "videotestsrc name=video_src ! ts_src.sink "
		pipe_str += "videotestsrc ! mux. "
	else:
		from trusas0.utils import sh
		# Disable autofocus
		sh("v4l2-ctl -d %s -c focus_auto=0"%video_device)
		sh("v4l2-ctl -d %s -c focus_absolute=0"%video_device)
		
		pipe_str += \
		' uvch264_src device=%(video_device)s auto-start=true name=video_src ' \
			'fixed-framerate=true initial-bitrate=50000000 profile=baseline ' \
			'video_src.vidsrc ! video/x-h264,width=1280,height=720,framerate=30/1 ! ts_src.sink '\
			'ts_src.src ! h264parse ! tee name=vidtee ' \
			'vidtee.src0 ! queue ! mux. ' \
		% {'video_device': video_device}

	# Gstreamer doesn't a nice way to create a proper
	# SDP/RTP-stream, so let's just dump out the raw video
	if udp_h264_port:
		pipe_str += 'vidtee.src1 ! queue ! rtph264pay ! udpsink sync=false host=127.0.0.1 port=%i '%int(udp_h264_port)
	
	
	if audio_device:
		pipe_str += ' alsasrc device="%s" ! queue ! voaacenc !  mux.'%audio_device
	
	log.info("Launching pipeline %s"%pipe_str)
	pipeline = gst.parse_launch(pipe_str)
	
	# Make sure we have an EPOCH clock
	clock = gst.system_clock_obtain()
	clock.set_property("clock-type", 0) # Set to gst.CLOCK_TYPE_REALTIME
	pipeline.use_clock(clock)
	
	mainloop = gobject.MainLoop()
	
	ts_src = pipeline.get_by_name('ts_src')
	#print ts_src
	#print "\n".join(dir(ts_src))

	log_level_map = {
		#gst.MESSAGE_EOS: log.info,
		#gst.MESSAGE_INFO: log.info,
		#gst.MESSAGE_STATE_CHANGED: log.info,
		gst.MESSAGE_WARNING: log.warning,
		gst.MESSAGE_ERROR: log.error,
		}
	

	def on_message(bus, message):
		t = message.type
		log_func = log_level_map.get(t,
			#lambda obj: log.debug("Unknown gstreamer message: %s"%obj))
			lambda obj: None) # Gstreamer spams like crazy
		log_func(message)
		
	def shutdown():
		# This should work:
		#pipeline.send_event(gst.event_new_eos())
		# But because the gstreamer EOS stuff seems to be FUBAR,
		# force the EOS to all pads
		# TODO: THIS DOESN'T SEEM TO ALWAYS PROVIDE A CLEAN
		#	SHUTDOWN
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
	
	signal.signal(signal.SIGTERM, lambda *args: shutdown())
	signal.signal(signal.SIGINT, lambda *args: shutdown())	

	gobject.threads_init()
	pipeline.set_state(gst.STATE_PLAYING)
	mainloop.run()
	pipeline.set_state(gst.STATE_NULL)


def main(argv):
	parser = argh.ArghParser()
	
	# Hacking to disable the subcommand stuff.
	# See: https://bitbucket.org/neithere/argh/issue/13/
	subparser = parser.add_commands([argh.alias('')(record)])
	parser.dispatch(argv=['']+argv)

if __name__ == '__main__':
	main(sys.argv[1:])
	
