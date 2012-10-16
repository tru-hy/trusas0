class ReprPack(object):
	def __init__(self, output):
		self.output = output
	
	def send(self, obj):
		self.output.write(repr(obj))
		self.output.write("\n")
		self.output.flush()

from ast import literal_eval
class ReprUnpack(object):
	def __init__(self, input):
		self.input = input
	
	def __iter__(self): return self

	def next(self):
		data = self.input.readline()
		return literal_eval(data)

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
			
		
		
if __name__ == '__main__':
	import doctest
	doctest.testmod()
