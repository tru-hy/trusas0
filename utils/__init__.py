"""A random collection of utilities and hacks around Python's annoyances"""
import inspect
import sys
import signal
import atexit
import traceback
import time
import re
import json
from os import path

from logutils import get_logger
log = get_logger()

class register_shutdown:
	"""
	Try to ensure a clean shutdown

	Tries to make sure the shutdown function is called in all
	normal* stoppage situations.
	
	
	If pass_args is TRue, the func gets passed whatever
	was given by eg atexit-callback or signal callback, so
	probably the safest thing is to grab **kwargs
	
	If unless dont_remove is true and func returns a non-true value or raises
	an exception, it is removed from the shutdown registry.
	Without this eg. in signal situation you'd get first called
	because of the signal and if you shut down nicely, called
	again by the exit-handler. Also if the callback misbehaves
	we don't end up in some kind of weird recursion loop.
	So return non-false from the shutdown function if you
	are doing something stupid you shouldn't be doing.

	:note: This will most definitely produce weird results if
		called more than once per process

	* This is in contrast to the Python-developers criteria
	  which was probably conceived in a lottery on lots of
	  crack.

	"""

	def __init__(self, func, pass_args=False):
		self.func = func
		self.pass_args = pass_args
		self.already_called = False
		self.orig_int = signal.signal(signal.SIGINT, self._wrapper)
		self.orig_term = signal.signal(signal.SIGTERM, self._wrapper)
		atexit.register(self._wrapper)
		log.debug("Registering shutdown handler %s"%str(func))


	def clear_handlers(self):
		log.debug("Clearing shudown handler %s"%str(self.func))
		signal.signal(signal.SIGINT, self.orig_int)
		signal.signal(signal.SIGTERM, self.orig_term)
		# Oh god I'm getting tired of these insane design
		# decisions! First no standard way to remove an
		# atexit handler.
		try:
			atexit._exithandlers.remove((self._wrapper, [], {}))
		except ValueError:
			# It seems that the handler is usually magically removed
			# at some point, so no need to worry
			pass
	
	
	def _wrapper(self, *args, **kwargs):
		if self.already_called:
			log.warning(
			"Nothing to worry about, but shutdown handler %s called more than once. "\
			"This shouldn't happen, but it does. Maybe Jami will fix it "\
			"some day."%self.func)
			return
		self.already_called = True
			
		if not self.pass_args:
			args, kwargs = [], {}
		self.clear_handlers()	
		
		self.func(*args, **kwargs)
		
		

def arg_dict(ignore=['self']):
	"""Get dict of current function's arguments
	
	A function to get current function arguments as dict without
	to repeat yourself.
	
	:todo: Return as something orderable
	
	For example
	>>> def func(param1, param2="default"):
	...     locvar="locval"
	...     # A sorthack due to unordenedness of dicts
        ...     return sorted(arg_dict().items())
	>>> func("arg1", "arg2")
	[('param1', 'arg1'), ('param2', 'arg2')]

	By default doesn't return the self-parameter.
	:todo: :warning: This is done via a hack that depends that skips all
		parameters named "self" as I couldn't find a way
		to find out if the caller is a method or not.
	

	>>> class Cls:
	...     def method(self, param1, param2="default"):
	...         return sorted(arg_dict().items())
	...	def unorthodox_method(this):
	...         return arg_dict().keys()
        >>> Cls().method('arg1', 'arg2')
	[('param1', 'arg1'), ('param2', 'arg2')]
        >>> Cls().unorthodox_method()
	['this']
	"""
	
	frame = inspect.stack()[1][0]
	args = inspect.getargvalues(frame)
	argnames = args.args
	
	return dict((arg, args.locals[arg])
		for arg in argnames if arg not in ignore)
	
class ShellError(Exception):
	def __init__(self, command, stdout, stderr, status_code):
		Exception.__init__(self, json.dumps(arg_dict()))

import envoy
def sh(command, success_code=0, **kwargs):
	result = envoy.run(command)
	log.debug(command)
	if success_code is not None and result.status_code != success_code:
		raise ShellError(command=command,
			stdout=result.std_out,
			stderr=result.std_err,
			status_code=result.status_code)
	return result

def relative(rel_path, relative_to=None):
	if relative_to is None:
		relative_to = inspect.stack()[1][1]
	
	directory = path.dirname(relative_to)
	return path.join(directory, rel_path)

class Signal(list):
	def connect(self, handler):
		if handler in self: return
		self.append(handler)

	def disconnect(self, handler):
		try:
			self.remove(handler)
		except ValueError:
			pass
	
	def emit(self, *args, **kwargs):
		for handler in self:
			handler(*args, **kwargs)

	def robust_emit(self, *args, **kwargs):
		for handler in self:
			try:
				handler(*args, **kwargs)
			except:
				traceback.print_exc()

class Hook(list):
	def __init__(self, func):
		self.func = func
		self.before = Signal()
		self.after = Signal()

	def __call__(self, *args, **kwargs):
		self.before.robust_emit(*args, **kwargs)
		retval = self.func(*args, **kwargs)
		self.after.robust_emit(retval, *args, **kwargs)
		return retval

if __name__ == "__main__":
    import doctest
    doctest.testmod()
