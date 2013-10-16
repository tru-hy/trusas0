#!/usr/bin/env python2

import gst
import sys
import json
from time import strptime
from calendar import timegm
import re
import ujson as json

pipe_str = 'filesrc location="%s" ! matroskademux name=mux '\
	'mux.subtitle_00 ! appsink name=app'%sys.argv[1]

pipeline = gst.parse_launch(pipe_str)
appsink = pipeline.get_by_name('app')
pipeline.set_state(gst.STATE_PAUSED)
appsink.set_state(gst.STATE_PLAYING)
#appsink.emit('pull-preroll')

time_parse = re.compile(r"(\d+):(\d+):([\d\.]+)")

start_time = None
while True:
	frame = appsink.emit('pull-buffer')
	utc, stream = frame.data.split('\n')
	
	utc_time, utc_frac = utc.split('.')
	seconds = timegm(strptime(utc_time, "%Y-%m-%d %H:%M:%S"))
	seconds += int(utc_frac)/float(gst.SECOND)
	if start_time is None:
		start_time = seconds
	m = time_parse.match(stream).groups()
	stream = int(m[0])*60*60 + int(m[1])*60 + float(m[2])
	
	print json.dumps(({'ts': seconds}, {'stream_ts': stream}))
