import logging
import json
import time
import inspect
import sys
import os

class RobustJsonEncoder(json.JSONEncoder):
	def default(self, obj):
		try:
			encoded = super(RobustJsonEncoder, self).default(obj)
		except TypeError:
			obj = str(obj)
			encoded = self.encode(obj)

		return encoded

class GmtJsonFormatter(logging.Formatter):
	# Inspired by https://github.com/madzak/python-json-logger/,
	# but reimplemented due to the weird license and some other
	# oddness I didn't understand in the first glance.

	def __init__(self, *args, **kwargs):
		super(GmtJsonFormatter, self).__init__(*args, **kwargs)
		self.converter = time.gmtime

	def format(self, record):
		if record.exc_info:
			record.exc_text = self.formatException(record.exc_info)
		elif record.args:
			record.exc_text = self.formatException(record.exc_info)

		record.asctime = self.formatTime(record, self.datefmt)

		return json.dumps(record.__dict__, cls=RobustJsonEncoder)

	def parse(self, line):
		return json.loads(line)

class DebuggableStreamHandler(logging.StreamHandler):
	def __init__(self, human_formatter=logging.Formatter(), **kwargs):
		super(DebuggableStreamHandler, self).__init__(**kwargs)
		self.human_formatter = human_formatter
		if os.getenv("TRUSAS_SERIALIZED_LOG"):
			self.format = super(DebuggableStreamHandler, self).format
	
	def format(self, record):
		if not self.stream.isatty():
			return super(DebuggableStreamHandler, self).format(record)
		return self.human_formatter.format(record)
			

log_formatter = GmtJsonFormatter()
log_handler = DebuggableStreamHandler()
log_handler.setFormatter(log_formatter)

def configure_logger():
	if log_handler in logging.root.handlers: return
	
	logging.root.addHandler(log_handler)
	logging.root.setLevel(logging.DEBUG)
	# The exception hook works in mysterious ways
	def excepthook(*exc_info):
		log.error("Unhandled %s (this is a bug): %s"%(
			exc_info[0].__name__, str(exc_info[1])),
			 exc_info=exc_info)
	sys.excepthook = excepthook
 
def get_logger(do_configure_logger=True):
	"""
	Get's a logger with a saner name for standalone scripts,
	which get their sys.argv[0] as the name. This is nice if you have
	a log dump from multiple simultaneous processes.

	:param do_configure_logger: If this is True, the root logger is configured
		using log_handler and set time to GMT. Trusas modules
		should keep this default on for interoperability.
	
	>>> orig_name = __name__; __name__ = '__main__'
	>>> get_logger().name == sys.argv[0]
	True
	>>> __name__ = orig_name
	
	Otherwise works as logging.getLogger(__name__)
	
	>>> orig_name = __name__; __name__ = 'some_module'
	>>> get_logger().name
	'some_module'
	>>> __name__ = orig_name
	
	:todo: Maybe digging out the would-be module name would be
		nicer as then the behavior would be consistent regardless
		of how the module is called.

	"""
	if do_configure_logger:
		configure_logger()
	frame = inspect.stack()[1][0]
	name = frame.f_globals["__name__"]
	if name == '__main__':
		name = sys.argv[0]
	return logging.getLogger(name)

log = get_logger() # Eat the own poison

import errno
import select
from StringIO import StringIO
from itertools import chain

def _stringio_getline(s):
	line_delim = '\n' # TODO: There may be a more portable way for this
	for i, buf in enumerate(s.buflist):
		if line_delim in buf:
			break
	else:
		return None

	last, not_ours = s.buflist[i].split(line_delim, 1)
	line = "".join(chain(s.buflist[:i], [last]))
	s.buflist = [not_ours] + s.buflist[i+1:]
	return line
	

class PollingFileWatcher(object):
	"""
	There's a python module for inotify which would be definitely
	nicer. 
	"""
	def __init__(self, poll_interval=0.1, only_new=False):
		self._paths = []
		self._files = []
		self._buffers = {}
		self.poll_interval = poll_interval
		self.only_new = only_new

	def add_path(self, path):
		if os.path.isdir(path):
			raise TypeError("Can't watch directory path %s"%str(path))
		
		self._paths.append(path)
		self.__open_file(path)
		
	def on_exception(self, path, exc_info):
		"""
		Handler for exceptions as we don't want to raise
		from the next-method. Overwrite/hook on this for
		custom handling
		"""
		log.exception("Watching file %s failed."%path)

	def __seek_to_last_line(self, f):
		f.seek(0, 2)
		if f.tell() == 0:
			return # An empty file
		# Using lowlevel IO to make sure we play with single bytes
		fd = f.fileno()
		
		#
		os.lseek(fd, -1, 2) # Go to the last byte
		char = None
		# Here goes the delimiter portability, well, most stuff
		# won't work on non-unix (or even non-Linux), so doing
		# this the right way doesn't really pay off.
		while f.tell() > 0:
			char = os.read(fd, 1)
			if char == '\n':
				return # We found our place
			os.seek(-2, 1) # Seek to one before
		 

	def __open_file(self, path):
		try:
			fobj = open(path, 'r')
			if self.only_new:
				self.__seek_to_last_line(fobj)
			self._files.append(fobj)
			self._buffers[path] = StringIO()
		except IOError, e:
			pass
			# TODO: Something fishy was going on, lets just trust..
			#if e.errno != errno.ENOENT:
			#	raise
			# We'll watch if this gets created

			

	def __iter__(self): return self

	def __probe_created_files(self):
		existing = [f.name for f in self._files]
		missing = (p for p in self._paths if p not in existing)
		for path in missing:
			try:
				self.__open_file(path)
			except:
				self.on_exception(self, path, sys.exc_info())

	def __read_to_buf(self, f):
		try:
			data = f.read()
			# Here's the fun part. Select considers
			# EOF'd files to be 'ready for reading',
			# so the select is in most cases useless
			# for us.
			if not data:
				# Don't clutter the buffer with empty strings
				return
			path = f.name
			self._buffers[path].write(data)
		except:
			self.on_exception(path, sys.exc_info())

	def _fill_buffers(self, poll_interval):
		# Check if there are files to be watched
		self.__probe_created_files()
		ready, ign, ign = select.select(
				self._files, [], [],
				poll_interval)
		
		for f in ready:
			self.__read_to_buf(f)

	def nonblock_iter(self):
		self._fill_buffers(poll_interval=0.0)
		for path, buf in self._buffers.iteritems():
			line = _stringio_getline(buf)
			if line is not None:
				yield path, line
				
	def next(self):
		while True:
			# First return any data we may have in the
			# buffers
			for path, buf in self._buffers.iteritems():
				line =  _stringio_getline(buf)
				if line is not None:
					return path, line
			
			# The sleep is due to not-so-suiteble for us
			# behavior of select, see __read_to_buf.
			time.sleep(self.poll_interval)
			self._fill_buffers(self.poll_interval) 

				

# TODO: This may be replaced by a nicer inotify-implementation
#	later
FileWatcher = PollingFileWatcher
			
class LogWatcher(FileWatcher):
	"""
	Iterates over given log files

	>>> from threading import Thread
	>>> from tempfile import mkdtemp
	>>> from os import path
	>>> tmpdir = mkdtemp(prefix="logutils_test")
	>>> log1 = logging.Logger("foo")
	>>> log1.addHandler(logging.FileHandler(path.join(tmpdir, "log1.log")))
	>>> log1.handlers[-1].setFormatter(log_formatter)
	>>> log1.error("message1")
	>>>
	>>> watcher = LogWatcher()
	>>> watcher.add_path(log1.handlers[-1].baseFilename)
	>>> logpath, record = watcher.next()
	>>> str(path.basename(logpath))
	'log1.log'
	>>> str(record['msg'])
	'message1'
	>>>
	>>> watcher.add_path(path.join(tmpdir, "log2.log"))
	>>> log2 = logging.Logger("bar")
	>>> log2.addHandler(logging.FileHandler(path.join(tmpdir, "log2.log")))
	>>> log2.handlers[-1].setFormatter(log_formatter)
	>>> log2.error("message2")
	>>> logpath, record = watcher.next()
	>>> str(path.basename(logpath))
	'log2.log'
	>>> str(record['msg']) 
	'message2'
	
	"""
	def __init__(self, formatter=log_formatter, **kwargs):
		super(LogWatcher, self).__init__(**kwargs)
		self.formatter = formatter

	def nonblock_iter(self):
		for path, line in FileWatcher.nonblock_iter(self):
			try:
				record = self.formatter.parse(line)
			except:
				log.info("Unknown log format: %s"%line)
				continue
			yield path, record

	def next(self):
		path, line = FileWatcher.next(self)
		while True:
			try:
				return (path, self.formatter.parse(line))
			except:
				self.on_exception(path, sys.exc_info())


if __name__ == '__main__':
	import doctest
	doctest.testmod()
