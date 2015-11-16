#!/usr/bin/env python2

# Doing * imports from Qt as they have the Q/Qwt namespace prefix
from PyQt4.Qt import *
from PyQt4.Qwt5 import *
import numpy as np
import time
import sys
import argh


class SignalPlot(QwtPlot):
	def __init__(self, parent=None, x_visible=10):
		QwtPlot.__init__(self, parent)
		self.x_visible = x_visible
		self.curves = {}

	def add_datum(self, x, fields):
		"""Add a measurement to the plot
		
		Adds the values x and y to their respective axes.
		Doesn't refresh the plot, use refresh() for that.
		
		NOTE: x has to be be monotonically increasing or weird things will happen!
		
		:todo: Check for monotonicity of the x-axis
		:todo: This is probably the most inefficient way to append to an array!
			The numpy arrays should be incrementally resized by
			ndarray.resize or something else a lot faster than copying
			all the stuff every time

		"""
	
		for name, value in fields.iteritems():
			if name not in self.curves:
				curve = QwtPlotCurve()
				curve.attach(self)
				self.curves[name] = [curve, [], []]
			
			stuff = self.curves[name]
			stuff[1].append(x)
			stuff[2].append(value)

		
	def refresh(self):
		"""Redraw the plot
		
		Redraws the plot with the current data so that the last self.window_size
		of x-axis is visible. Autoscales the plot to fit the whole y-axis.
		
		:todo: Allow interactive changing of the window size and navigating over time
		:todo: Qwt seems to allow some kind of incremental rendering for better performance
		:todo: Implementing the buffering stuff here is quite awful design
		"""
		if len(self.curves) == 0: return
		
		max_x = max((c[1][-1] for c in self.curves.itervalues()))
	
		start_x = max_x - self.x_visible
		
		for c, x, y in self.curves.itervalues():
			while len(x) > 0 and x[0] < start_x:
				del x[0]
				del y[0]

		for curve, x, y in self.curves.itervalues():
			# I guess this probably copies stuff, more
			# efficient way would of course to use a
			# ringbuffer, but I couldn't find a ready made
			# implementation and am too busy for doing things
			# right.
			curve.setData(x, y)
		
		# The autoscale likes to hang on to integers without
		# this
		self.setAxisScale(self.xBottom, start_x, max_x)
		self.replot()

def main(window_title=None, quit_on_eof=False):
	from trusas0.packing import default_unpacker, AsyncIter

	import sys
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = QApplication([])
	input = AsyncIter(default_unpacker())
	window = QMainWindow()
	plot = SignalPlot(parent=window)
	window.setCentralWidget(plot)
	if window_title:
		window.setWindowTitle(window_title)

	# TODO: Take from argument/environment
	base_ts = time.time()

	def consume():
		try:
			for header, obj in input:
				ts = header['ts']-base_ts
				plot.add_datum(ts, obj)
			plot.refresh()
		except EOFError:
			timer.stop()
			if quit_on_eof: app.quit()

	update_rate = 30
	timer = QTimer(); timer.timeout.connect(consume)
	timer.start(1/float(update_rate)*1000)
	
	window.show()
	app.exec_()

if __name__ == '__main__':
        argh.dispatch_command(main)
	
