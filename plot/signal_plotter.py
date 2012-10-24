#!/usr/bin/env python

# Doing * imports from Qt as they have the Q/Qwt namespace prefix
from PyQt4.Qt import *
from PyQt4.Qwt5 import *
import numpy as np
import time
import sys
import argh


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

class PlotManager(object):
	def __init__(self, base_time=None,
			on_add=lambda name, plot: None):
		if base_time is None:
			base_time = time.time()
		self.base_time = base_time
	
		self.plots = {}
		self.on_add = on_add
		
		
	def add_data(self, header, data):
		ts = header['ts'] - self.base_time
		for col in data:
			if not col in self.plots:
				plot = SignalPlot()
				self.plots[col] = plot
				self.on_add(col, plot)
				
			plot = self.plots[col]
			plot.add_datum(ts, data[col])

	def refresh(self):
		for plot in self.plots.values():
			if plot.isVisible():
				plot.refresh()
		
@argh.plain_signature
@argh.arg('-s', '--show_by_default', type=str, nargs='+')
def main(show_by_default=[]):
	from trusas0.packing import AsyncIter, ReprUnpack

	import sys
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = QApplication([])
	input = AsyncIter(ReprUnpack(sys.stdin))
	#plot = SignalPlot(window_size=30)

	main = QMainWindow()
	def new_plot(name, plot):
		dockwidget = QDockWidget(name, main)
		dockwidget.setWidget(plot)
		if name not in show_by_default:
			dockwidget.setVisible(False)
		
		main.addDockWidget(Qt.LeftDockWidgetArea, dockwidget)
	
	manager = PlotManager(on_add=new_plot)
	
	def consume():
		for header, obj in input:
			manager.add_data(header, obj)
		
		manager.refresh()

	update_rate = 30
	timer = QTimer(); timer.timeout.connect(consume)
	timer.start(1/float(update_rate)*1000)
	
	main.show()
	app.exec_()

if __name__ == '__main__':
	parser = argh.ArghParser()
	
	argv = sys.argv[1:]
	# Hacking to disable the subcommand stuff.
	# See: https://bitbucket.org/neithere/argh/issue/13/
	subparser = parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+argv)

