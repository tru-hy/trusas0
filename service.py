from subprocess import Popen
import os
from os import path
import sys
import time
import signal
import shlex
import errno
import trusas0.utils
import itertools
log = trusas0.utils.get_logger()

# TODO: Currently allows only one session to run at the same time
#	could be easily fixed by adding some kind of session id to
#	the environment.
# TODO: The whole environment probing thing is a needlessly hacky
#	approach, change to a good-old run-dir with pidfiles.
SERVICE_VAR="TRUSAS_SERVICE"
BASE_DIR_VAR="TRUSAS_DIR"

class ServiceException(Exception): pass
class ServiceNotFound(ServiceException): pass

class Service(object):
	def __init__(self, command_spec, outfile_spec, errfile_spec):
		self.command_spec = command_spec
		self.outfile_spec = outfile_spec
		self.errfile_spec = errfile_spec
		self.extra_env = {}

	def parametrize(self, **kwargs):
		self.command = tuple(part%kwargs
			for part in self.command_spec)
		self.outfile = self.outfile_spec%kwargs
		self.errfile = self.errfile_spec%kwargs

class Command(object):
	def __init__(self, command):
		self.command = command
	
	def __call__(self, **kwargs):
		return self.command%kwargs

class ServiceManager(object):
	# TODO: USE THIS!
	SERVICE_LOCK_FILE='_manager.lock'
	PID_DIR="_pids"

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
		self.session_dir = session_dir
		self.runners = {}
		# TODO: This is maybe not really our job to track

		pid_dir = path.join(session_dir, "_pids")
		try:
			os.mkdir(pid_dir)
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise
			log.warning("Starting with residual pid directory %s"%pid_dir)
		

		self.__initialize_services(pid_dir)
	
		
	def __initialize_services(self, pid_dir):
		for name, service in self.services.iteritems():
			service.parametrize(
				name=name,
				session_dir=self.session_dir)
			self.runners[name] = ServiceRunner(name=name,
					spec=service,
					pid_dir=pid_dir,
					session_dir=self.session_dir)

	def __getitem__(self, name):
		return self.services[name]

	def start(self):
		signal.signal(signal.SIGCHLD, bury_child)
		for name in self.services:
			self.ensure_service(name)
		return self

	def start_service(self, name):
		self.runners[name].start()
	
	def ensure_service(self, name):
		self.runners[name].ensure()

	def is_running(self, name):
		return self.runners[name].is_running()
	
	def dead_services(self):
		return [name for name in self.services
			if not self.is_running(name)]

	def shutdown(self, timeout=10.0, poll_interval=0.1):
		"""
		:todo: Do this asynchronously
		"""
		for name, runner in self.runners.iteritems():
			try:
				runner.stop()
			except OSError, e:
				log.warning(
					"Couldn't tell service %s to stop: %s"%(name, str(e)))
		
		for i in range(int(timeout/poll_interval)):
			for name, runner in self.runners.items():
				if not runner.is_dangling(): continue
				log.info("%s reported dead"%(name))
				runner.clear()
				del self.runners[name]

			if len(self.runners) == 0:
				break
			time.sleep(poll_interval)
		
		log.warning("FIXME!!! Killing leftover 'ghost' services (probably adbd) "\
			"left over due to the stupid environment hacking stuff")
		for name, pid in running_service_pids():
			try:
				os.kill(pid, signal.SIGTERM)
			except OSError, e:
				log.warning(
					"Couldn't kill 'ghost' service %s: %s"%(name, str(e)))

		if len(self.runners) == 0:
			return

		for name, runner in self.runners.iteritems():
			try:
				runner.kill()
			except OSError, e:
				log.warning(
					"Couldn't kill service %s: %s"%(name, str(e)))

		raise ServiceException("Following services had to be forced to shut down: %s"%str(self.runners.keys()))
		

FILE_TEMPLATE="%(session_dir)s/%(name)s"
class ServiceSpec(object):

	def __init__(self):
		self.services = {}

	def add(self, name, command, outfile=None, errfile=None):
		if name in self.services:
			raise ServiceException("Service '%s' already registered."%name)
		if outfile is None:
			outfile = FILE_TEMPLATE + ".data"
		if errfile is None:
			errfile = FILE_TEMPLATE + ".log"
		
		if isinstance(command, basestring):
			command = shlex.split(command)
		
		service = Service(command, outfile, errfile)
		self.services[name] = service

	def __setitem__(self, name, command):
		self.add(name, command)

	def __getitem__(self, name):
		return self.services[name]

	def instance(self, session_dir):
		return ServiceManager(self, session_dir)
		
	
def pid_is_running(pid):
	try:
		os.kill(pid, 0)
	except OSError:
		# :todo: The OSError may be in theory for other reasons
		#	than ESRCH
		return False

	return True

class ServiceRunner(object):
	def __init__(self, name, spec, pid_dir, session_dir):
		self.name = name
		# This doesn't really belong here anymore after we get
		# rid of the ENV hacking
		self.session_dir = session_dir 
		self.pidfile = path.join(pid_dir, name + ".pid")
		self.spec = spec
	
	def pid(self):
		try:
			with open(self.pidfile, 'r') as f:
				pidstr = f.read().strip()
				return int(pidstr)
		except ValueError:
			log.critical("Invalid pid '%s' found in pidfile %s"%(pidstr, self.pidfile))
			raise

		return int(open(self.pidfile))

	def _set_pid(self, pid):
		with open(self.pidfile, 'w') as f:
			f.write(str(int(pid)))
	
	def start(self):
		service = self.spec
		name = self.name
		log.info("Starting service %s with command '%s'"%(
			name, " ".join(service.command)))
		
		
		# Move old files out of the way. Shouldn't cause too much
		# problems, as the "stream clients" should follow path and
		# nobody else should be writing or trying to create the file,
		# so we don't even try to be atomic here. Even the file existing
		# is a corner case itself.
		if path.exists(service.outfile) and path.getsize(service.outfile) > 0:
			prevpath = service.outfile
			for retry in itertools.count(1):
				if not path.exists(prevpath):
					os.rename(service.outfile, prevpath)
					break
			
				prevpath = service.outfile + ".%i"%retry
			
			log.warning("Output file for this service already exists, "\
				"moving the old file to '%s' instead."%prevpath)
		
		stdout = open(service.outfile, 'w')
		stderr = open(service.errfile, 'a')

		pid = start_service(name, service.command,
			stdout.fileno(), stderr.fileno(), self.session_dir,
			extra_env=service.extra_env)
		self._set_pid(pid)
		log.info("Started service %s with pid %i"%(name, pid))

		stdout.close()
		stderr.close()

	def ensure(self):
		if not self.is_running():
			self.start()
	
	def stop(self):
		os.kill(self.pid(), signal.SIGTERM)
	
	def kill(self):
		os.kill(self.pid(), signal.SIGKILL)

	def clear(self):
		os.remove(self.pidfile)

	def has_pidfile(self):
		try:
			self.pid()
		except ValueError:
			return False
		except IOError:
			return False

		return True

	def is_dangling(self):
		return self.has_pidfile() and not pid_is_running(self.pid())

	def is_running(self):
		try:
			pid = self.pid()
		except ValueError:
			return False
		except IOError:
			return False

		return pid_is_running(pid)


def bury_child(*args):
	"""
	Attempt not to create zombies
	
	Just ignores the process' return value so that it can
	be removed from the process table. This way the pid-polling i
	same regardless of whether the process is our child or not. And
	anyway the services detach from our parenthood.

	:note: The SIGCHLD seems to get sent sometimes with os.wait blocking.
		This is probably because the kernel gets confused on who's
		who's child on the detach. That's why we use os.WNOHANG-flag.
	:todo: This seems to quite often return (0, 0) even on valid deaths
	"""
	
	child = os.waitpid(-1, os.WNOHANG)

def get_process_environment(pid, proc_dir):
	env_path = path.join(proc_dir, str(pid), 'environ')
	with open(env_path, 'r') as env_file:
		return env_file.read().split('\0')

def _process_envs(proc_dir='/proc'):
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


import pty
def start_service(name, command, stdout_fd, stderr_fd, session_dir, extra_env={}):
	# TODO! CRITICAL! It seems that sometimes the services die with the parent!
	# (may be only the gstreamer thingie that gets an error from xvimagesink, but investigate)
	# Probably best fix would be to use some readily debugged daemonizing library
	pid = os.fork()
	if pid != 0:
		return pid
	
	# Seems that some insane libraries seem to need
	# a terminal, so let's give them one
	# TODO: No idea if this even worsens the daemon-dying
	#	problem
	master, slave = pty.openpty()
	os.dup2(slave, 0)
	os.dup2(stdout_fd, 1)
	os.dup2(stderr_fd, 2)
	os.putenv(SERVICE_VAR, name)
	os.putenv(BASE_DIR_VAR, session_dir)
	for var, val in extra_env.iteritems():
		os.putenv(var, val)
	
	os.setsid()
	os.execvp(command[0], command)

def running_service_pids():
	for pid, env in _process_envs():
		name = _get_env_var(SERVICE_VAR, env)
		if not name: continue
		yield name, pid


if __name__ == '__main__':
	for name, pid in running_service_pids():
		print name, pid
