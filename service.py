from subprocess import Popen
import os
from os import path
import sys
import time
import signal
import shlex
import errno

SERVICE_VAR="TRUSAS_SERVICE"
BASE_DIR_VAR="TRUSAS_DIR"

class ServiceException(Exception): pass
class ServiceNotFound(ServiceException): pass

class Service(object):
	def __init__(self, command_spec, outfile_spec, errfile_spec):
		self.command_spec = command_spec
		self.outfile_spec = outfile_spec
		self.errfile_spec = errfile_spec

	def parametrize(self, **kwargs):
		self.command = tuple(part%kwargs
			for part in self.command_spec)
		self.outfile = self.outfile_spec%kwargs
		self.errfile = self.errfile_spec%kwargs

class ServiceManager(object):
	class SessionExists(Exception): pass
	
	@classmethod
	def create_session_dir(cls, base_dir, session_id):
		session_dir = path.join(base_dir, session_id)
		try:
			os.mkdir(session_dir)
		except OSError, e:
			if e.errno != errno.EEXIST: raise
			raise cls.SessionExists(
				"Session with id '%s' already "\
				"exists in directory '%s'."%(
					session_id, session_dir)
				)
			
		return session_dir
	
	def __init__(self, spec, session_dir):
		self.spec = spec
		self.services = spec.services
		self.pids = {}
		self.session_dir = session_dir
		self.__initialize_services()
		self.start()

	def __initialize_services(self):
		for name, service in self.services.iteritems():
			service.parametrize(
				name=name,
				session_dir=self.session_dir)

	def __getitem__(self, name):
		return self.services[name]

	def start(self):
		signal.signal(signal.SIGCHLD, bury_child)
		for name in self.services:
			self.start_service(name)

	def start_service(self, name):
		service = self.services[name]
		pid = ensure_service(name, service.command,
			service.outfile, service.errfile, self.session_dir)
		self.pids[name] = pid


	def is_running(self, name):
		try:
			pid = self.pids[name]
		except KeyError:
			raise ServiceException("Service '%s' not registered."%name)

		return pid_is_running(pid)

	def dead_services(self):
		return [name for name in self.services
			if not self.is_running(name)]
	
	def shutdown(self, timeout=10.0, poll_interval=0.1):
		"""
		:todo: Do this asynchronously
		"""
		for pid in self.pids.values():
			os.kill(pid, signal.SIGTERM)
		
		for i in range(int(timeout/poll_interval)):
			for dead in self.dead_services():
				print "DEAD", dead
				del self.pids[dead]
			if len(self.pids) == 0:
				return
			time.sleep(poll_interval)
		
		for pid in self.pids.values():
			os.kill(pid, signal.SIGTERM)

		raise ServiceException("Following services had to be forced to shut down: %s"%str(self.pids))
		
			

FILE_TEMPLATE="%(session_dir)s/%(name)s"
class ServiceSpec(object):

	def __init__(self):
		self.services = {}

	def add(self, name, command, outfile=None, errfile=None):
		if name in self.services:
			raise ServiceException("Service '%s' already registered."%name)
		
		
		if outfile is None:
			outfile = FILE_TEMPLATE + ".out"
		if errfile is None:
			errfile = FILE_TEMPLATE + ".err"
		
		if isinstance(command, basestring):
			command = shlex.split(command)
		
		service = Service(command, outfile, errfile)
		self.services[name] = service

	def __setitem__(self, name, command):
		self.add(name, command)

	def __getitem__(self, name):
		return self.services[name]
		
	
def pid_is_running(pid):
	try:
		os.kill(pid, 0)
	except OSError:
		# :todo: The OSError may be in theory for other reasons
		#	than ESRCH
		return False

	return True


def ensure_service(name, command, stdout_file, stderr_file, session_dir):
	try:
		pid = find_service(name)
	except ServiceNotFound:
		pass
	else:
		return pid

	# TODO: Don't overwrite!?
	stdout = open(stdout_file, 'w')
	stderr = open(stderr_file, 'w')
	pid = start_service(name, command,
		stdout.fileno(), stderr.fileno(), session_dir)
	stdout.close()
	stderr.close()
	return pid


def bury_child(*args):
	# Just ignore the return value so that
	# it can be removed from the process table.
	# This way the pid-polling is same regardless of
	# whether the process is our child or not
	os.wait()

def get_process_environment(pid, proc_dir):
	env_path = path.join(proc_dir, str(pid), 'environ')
	with open(env_path, 'r') as env_file:
		return env_file.read().split('\0')

def _process_envs(proc_dir):
	for pid in os.listdir(proc_dir):
		try:
			pid = int(pid)
		except ValueError:
			continue
		
		try:
			env = get_process_environment(pid, proc_dir)
		except IOError:
			continue
		
		yield pid, env

def find_service(name, proc_dir='/proc'):
	service_name = "%s=%s"%(SERVICE_VAR, name)
	
	for pid, env in _process_envs(proc_dir):
		if service_name in env:
			return pid
	
	raise ServiceNotFound

def _get_env_var(name, env):
	for var in env:
		if not var.startswith("%s="%name): continue
		value = var.split("=", 1)[1]
		return value
	return None

def get_running_session(proc_dir='/proc'):
	for pid, env in _process_envs(proc_dir):
		if _get_env_var(SERVICE_VAR, env): break
	else:
		return None

	return _get_env_var(BASE_DIR_VAR, env)



def start_service(name, command, stdout_fd, stderr_fd, session_dir):
	pid = os.fork()
	if pid != 0:
		return pid
	
	os.close(0)
	os.dup2(stdout_fd, 1)
	os.dup2(stderr_fd, 2)
	os.putenv(SERVICE_VAR, name)
	os.putenv(BASE_DIR_VAR, session_dir)
	os.setsid()
	os.execvp(command[0], command)

