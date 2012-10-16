"""A random collection of utilities and hacks around Python's annoyances"""
import logging; log = logging.getLogger(__name__)
import json

import inspect
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

if __name__ == "__main__":
    import doctest
    doctest.testmod()
