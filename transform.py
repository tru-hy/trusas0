#!/usr/bin/python2

"""
A simple program to do transformations for the data stream

NOTE: This allows execution of arbitrary python code, so use with care!
"""

from __future__ import division
import argh
from packing import default_packer, default_unpacker
import sys
from trusas0.utils import get_logger; log = get_logger()
import traceback
import signal
import itertools

def _generate_function(source):
	# There is a "nicer way" for this using types.FunctionType,
	# but that would add about 20 lines with no real benefit
	return eval("lambda d, header: "+source)

def _call_funcs(funcs, d, header):
	for func in funcs:
		try:
			d = func(d, header)
		except:
			traceback.print_exc()
	return d

def apply(d, **kwargs):
	for key, func in kwargs.iteritems():
		d[key] = func(d[key])
	return d

def fields(d, *fields, **rename):
	new_d = {k: d[k] for k in fields if k in d}

	new_d.update({new: d[old]
		for (new, old) in rename.iteritems() if old in d})
	return new_d

#@argh.plain_signature
@argh.arg('transformation', type=str, nargs='+')
# TODO: Handle these when needed
#@argh.arg('-n', '--nonlambda', type=str, nargs='+')
def main(transformation):
	funcs = list(map(_generate_function, transformation))
	
	input = default_unpacker()
	output = default_packer()
	for header, d in input:
		d = _call_funcs(funcs, d, header)
		output.send(d, header=header)
	
if __name__ == '__main__':
        argh.dispatch_command(main)
