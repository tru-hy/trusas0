#!/usr/bin/python2

"""
A simple program to transform some data values in the stream

NOTE: This allows execution of arbitrary python code, so use with care!

:todo: Seems very slow
"""
import argh
from packing import ReprPack, ReprUnpack
import sys
import logging; log = logging.getLogger(__name__)

def transformer(input, output, transforms):
	for header, data in input:
		for key, func in transforms.iteritems():
			if key not in data: continue
			try:
				data[key] = func(data[key])
			except Exception, e:
				log.error("Transformation exception: %s"%e)
		output.send(data, header=header)

@argh.plain_signature
@argh.arg('transformations', type=str, nargs='+')
def main(transformations):
	transfs = {}
	for trans_spec in transformations:
		name, func = trans_spec.split("=", 1)
		func = eval(func)
		transfs[name] = func
	
	input = ReprUnpack(sys.stdin)
	output = ReprPack(sys.stdout)
	transformer(input, output, transfs)

if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([argh.alias('')(main)])
	parser.dispatch(argv=['']+sys.argv[1:])
