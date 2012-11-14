#!/usr/bin/env python2

import sys
import signal
from gi.repository import Champlain, GtkChamplain, Gtk, GtkClutter, GObject
import argh

@argh.command
def main(init_zoom=17, update_freq=10, window_title=None):
	from trusas0.packing import AsyncIter, ReprUnpack
	
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	GtkClutter.init([])

	window = Gtk.Window()
	if window_title is not None:
		window.set_title(window_title)
	
	window.connect("destroy", Gtk.main_quit)
	
	widget = GtkChamplain.Embed()
	widget.set_size_request(640, 480)
	
	map_view = widget.props.champlain_view
	
		


	markers = Champlain.MarkerLayer()
	map_view.add_layer(markers)
	current_pos = Champlain.Point()
	current_pos.hide()
	markers.add_marker(current_pos)
	
	has_any_locations = False
	
	map_view.set_zoom_level(init_zoom)
	def set_position(lat, lon, has_any_locations=has_any_locations):
		current_pos.show()
		map_view.center_on(lat, lon)
		current_pos.set_location(lat, lon)

	window.add(widget)
	window.show_all()

	input = AsyncIter(ReprUnpack(sys.stdin))
	def consume():
		for header, loc in input:
			set_position(loc['latitude'], loc['longitude'])
	
		return True
		
	GObject.timeout_add(int(1.0/update_freq*1000), consume)

	Gtk.main()

if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+sys.argv[1:])
