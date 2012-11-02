#!/usr/bin/python2

"""
A simple program to transform some data values in the stream

NOTE: This allows execution of arbitrary python code, so use with care!

:todo: Seems very slow
"""
import argh
from packing import default_packer, default_unpacker
import sys
import logging; log = logging.getLogger(__name__)

def _generate_function(source):
	# There is a "nicer way" for this using types.FunctionType,
	# but that would add about 20 lines with no real benefit
	exec("def func(d, header): "+source)
	return func

@argh.plain_signature
@argh.arg('transformations', type=str, nargs='+')
def main(transformations):
	global d # Not passing d as a parameter 
	funcs = map(_generate_function, transformations)
	
	input = default_unpacker()
	output = default_packer()
	for header, d in input:
		for func in funcs:
			d = func(d, header)
		output.send(d, header=header)
	
if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+sys.argv[1:])
