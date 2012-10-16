#!/usr/bin/env python

# Doing * imports from Qt as they have the Q/Qwt namespace prefix
from PyQt4.Qt import *
from PyQt4.Qwt5 import *
import numpy as np


class SignalPlot(QwtPlot):
	def __init__(self, window_size=10):
		QwtPlot.__init__(self)
		self.x = np.empty(0)
		self.y = np.empty(0)
		self.window_size = window_size
		self.curve = QwtPlotCurve()
		self.curve.attach(self)

	def add_datum(self, x, y):
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
		self.x = np.append(self.x, x)
		self.y = np.append(self.y, y)

		
	def refresh(self):
		"""Redraw the plot
		
		Redraws the plot with the current data so that the last self.window_size
		of x-axis is visible. Autoscales the plot to fit the whole y-axis.
	
		:todo: The searchsorted doesn't really have to be done every time. Also
			Qwt may be sane enough to have a "autoscale visible" -option
		:todo: Allow interactive changing of the window size and navigating over time
		:todo: Qwt seems to allow some kind of incremental rendering for better performance
		"""
		if len(self.x) == 0: return
		
		self.curve.setData(self.x, self.y)
		start = self.x[-1]-self.window_size
		self.setAxisScale(self.xBottom, start, self.x[-1])
		
		first = np.searchsorted(self.x, start)
		visible = self.y[first:]
		self.setAxisScale(self.yLeft, np.min(visible), np.max(visible))

		self.replot()

	


if __name__ == '__main__':
	from trusas0.packing import AsyncIter, ReprUnpack
	import sys
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = QApplication([])
	input = AsyncIter(ReprUnpack(sys.stdin))
	plot = SignalPlot(window_size=30)
	start_x = None
	
	def consume():
		global start_x
		global prev_x
		has_data = False
		for obj in input:
			has_data = True
			if start_x is None:
				start_x = obj['time']

			total_a = np.linalg.norm([obj['xforce'],
				obj['yforce'], obj['zforce']])
			plot.add_datum(obj['time'] - start_x, total_a)

		if has_data:
			plot.refresh()

	update_rate = 100
	timer = QTimer(); timer.timeout.connect(consume)
	timer.start(1/float(update_rate)*1000)

	

	plot.show()
	app.exec_()
