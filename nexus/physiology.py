#!/usr/bin/env python2

from trusas0.utils import get_logger
log = get_logger()
from trusas0.packing import default_packer
import pynexus
import argh
import sys
from subprocess import Popen
import os


def record(nexus_address, output):
	dev = pynexus.Nexus(nexus_address)
	for sample in dev:
		output.send(sample)

def main(nexus_address, pin=None):
	if pin:
		# TODO: Check the status
		Popen("echo %s |bt-agent"%(pin,),
			stdout=open(os.devnull), stderr=open(os.devnull),
			shell=True)
	record(nexus_address, default_packer())

if __name__ == '__main__':
        argh.dispatch_command(main)
