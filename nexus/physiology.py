#!/usr/bin/env python

from trusas0.packing import ReprPack
import pynexus
import argh
import sys

def record(nexus_address, output):
	dev = pynexus.Nexus(nexus_address)
	for sample in dev:
		output.send(sample)

@argh.command
def main(nexus_address):
	record(nexus_address, ReprPack(sys.stdout))

if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+sys.argv[1:])
