import logging
import json
import time
import inspect
import sys

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
			print record.exc_info
			record.exc_text = self.formatException(record.exc_info)
			print record.exc_text
		elif record.args:
			record.exc_text = self.formatException(record.exc_info)

		record.asctime = self.formatTime(record, self.datefmt)

		return json.dumps(record.__dict__, cls=RobustJsonEncoder)

	def parse(self, line):
		return json.loads(line)


log_formatter = GmtJsonFormatter()
log_handler = logging.StreamHandler()
log_handler.setFormatter(log_formatter)

def configure_logger():
	if log_handler in logging.root.handlers: return
	logging.root.handlers.append(log_handler)
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

