#!/usr/bin/env python2

import time
import sys
from utils import get_logger
import argh
log = get_logger()

try:
	import ujson as json
except ImportError:
	import json

def default_packer(output=sys.stdout):
	"""
	Will allow to change the default easily
	in the future.
	"""
	return JsonPack(output)

def default_unpacker(input=sys.stdin):
	"""
	Will allow to change the default easily
	in the future.
	"""
	return JsonUnpack(input)
	

def wrap_object(obj):
	return ({'ts': time.time()}, obj)


class LinePack(object):
	def __init__(self, output):
		self.output = output
	
	def send(self, obj, header=None):
		if header is None:
			data = wrap_object(obj)
		else:
			data = (header, obj)
		
		self.output.write(self.serialize(data))
		self.output.write("\n")
		self.output.flush()


class LineUnpack(object):
	def __init__(self, input):
		self.input = input
	
	def __iter__(self): return self

	def next(self):
		# :todo: We could use the iterator interface (eg self.input.next())
		# but for some reason python does horrible buffering with this,
		# so it's sadly a lot less general readline for now

		while True:
			data = self.input.readline()
			if data is None or data == '':
				raise StopIteration

			try:
				return self.unserialize(data)
			except:
				log.exception("Unrecognized data.")


class JsonPack(LinePack):
	serialize = staticmethod(json.dumps)

class JsonUnpack(LineUnpack):
	unserialize = staticmethod(json.loads)

class ReprPack(LinePack):
	serialize = staticmethod(repr)

from ast import literal_eval
class ReprUnpack(LineUnpack):
	unserialize = staticmethod(literal_eval)

from Queue import Queue, Empty
from threading import Thread

class AsyncIter(object):
	"""A wrapper to allow async reading from an iterator

	Supports the iterator protocol with a twist. Requested
	iterators return the queue contents until the queue is
	empty, after which it raises StopIteration, as a normal
	iterator.
	>>> # A blocking iterator mock
	>>> from threading import Condition
	>>> lock = Condition(); ign = lock.acquire()
	>>> def blocking_iter():
	...     yield "first"; ign = lock.acquire()
	...	yield "second"; ign = lock.notify(); lock.release()
	>>>	
	>>> async = AsyncIter(blocking_iter())
	>>> list(async)
	['first']

	While the queue remains empty, the AsyncIter will immediately raise
	StopIteration
	>>> list(async)
	[]

	But will return the new values after the queue has values
	>>> # Allow blocking_iter to continue
	>>> ign = lock.wait()
	>>> list(async)
	['second']

	If a new iterator is requested, but the wrappee iterator
	has stopped, an EOF error is rised.
	>>> iter(async)
	Traceback (most recent call last):
	    ...
	EOFError: The producer iterator of AsyncIter has stopped
	"""
	
	def __init__(self, iter, queue=None, thread_gen=Thread):
		self.__iter = iter
		
		if queue is None:
			queue = Queue()
		self.__queue = queue
		
		self.__eof = False

		thread_gen(target=self.__consumer).start()

	def __consumer(self):
		# :todo: Option for asynchronous put?
		for item in self.__iter:
			self.__queue.put(item)
		self.__eof = True

	def __iter__(self):
		if self.__eof and self.__queue.empty():
			raise EOFError("The producer iterator of AsyncIter has stopped")
		return self

	def next(self):
		try:
			return self.__queue.get_nowait()
		except Empty:
			raise StopIteration
			
def convert(unpacker=None, packer=None):
	if unpacker is None:
		unpacker = default_unpacker()
	else:
		unpacker = eval(unpacker)
	
	if packer is None:
		packer = default_packer()
	else:
		packer = eval(packer)
	
	for header, data in unpacker:
		packer.send(data, header=header)
		
if __name__ == '__main__':
	parser = argh.ArghParser()
	parser.add_commands([convert])
	parser.dispatch()
	#import doctest
	#doctest.testmod()
