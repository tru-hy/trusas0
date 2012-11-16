#!/usr/bin/env python2

import sys
import gobject
from trusas0.utils import get_logger; log = get_logger()

import argh
import os

@argh.command
def preview(udp_port, window_name=None):
	if window_name is not None:
		import procname
		# This is a hack to set the window title so we can embed it later.
		# A nicer way would be probably to create a new window and provide
		# the id when xvimagesink asks for it, but I'm feeling too lazy.
		# The procname has to be set before gst is imported
		procname.setprocname(window_name)
	
	# Pygst loves to grab the argv, so give the
	# greedy bastard nothing
	args, sys.argv = sys.argv, []; import gst; sys.argv = args

	# TODO: Fall back to (reduced quality) software decoding if VDPAU
	# if is unavailable or broken
	pipe_str = "udpsrc uri=udp://0.0.0.0:%i "\
        	'caps="application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264" !' \
        "rtph264depay ! queue ! ffdec_h264 skip-frame=1 ! "\
        "xvimagesink sync=false"%int(udp_port)

	pipeline = gst.parse_launch(pipe_str)
	pipeline.set_state(gst.STATE_PLAYING)
	
	try:
		gobject.MainLoop().run()
	except KeyboardInterrupt:
		pass
	pipeline.set_state(gst.STATE_NULL)

	
def main(argv):
	parser = argh.ArghParser()
	subparser = parser.add_commands([argh.alias('')(preview)])
	parser.dispatch(argv=['']+argv)
	
if __name__ == '__main__':
	main(sys.argv[1:])


