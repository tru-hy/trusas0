#!/usr/bin/env python2
"""
A stupid service that just repeteadly sends the current time.
Mostly useful for testing or showing the current time in an
overkill (albeit more elegant ;) way.
"""
import time, sys, argh
from packing import default_packer

@argh.command
def main(interval=0.1):
	output = default_packer()
	while True:
		output.send({'time': time.time()})
		time.sleep(interval)

if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+sys.argv[1:])
	
