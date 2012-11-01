import os
from os import path
from trusas0.service import ServiceManager, get_running_session
from PyQt4.Qt import *
from PyQt4.QtGui import *
import signal
import subprocess

class SessionUi(object):
	"""
	:todo: Refactor the generic page-backend-stuff to a separate
		class
	:todo: Figure out how to prevent QWebView not to reload
		the DOM on new url
	"""
	def __init__(self, spec, base_dir):
		self.spec = spec
		self.base_dir = base_dir
		# So annoying that QApplication must be
		# created before any widgets
		self.app = QApplication([])
		self.widget = QWebView()
		self.templatedir = path.join(path.dirname(__file__), 'template')
		self.base_url = path.join(self.templatedir, "index.html")
		self.manager = None
		self.widget.loadFinished.connect(self.dispatch)

	def __content(self, template):
		template = path.join(self.templatedir, template)
		with open(template) as html:
			self.content.setInnerXml(html.read())

	def dispatch(self, success):
		frame = self.widget.page().mainFrame()
		self.dom = frame.documentElement()
		self.content = self.dom.findFirst("#content")

		new_url = self.widget.url()
		args = dict((str(n), str(v)) for (n, v) in new_url.queryItems())
		page = args.pop('p', 'index')
		
		handler = getattr(self, page)
		handler(**args)
	
		
	def __call__(self, page, **kwargs):
		args = kwargs.copy()
		args['p'] = page
		url = QUrl(self.base_url)
		url.setQueryItems(args.items())
		self.widget.load(url)
	
	"""
	def initialize(self, status_ok):
		self.widget.loadFinished.disconnect(self.initialize)
		frame = self.widget.page().mainFrame()
		self.dom = frame.documentElement()
		self.content = self.dom.findFirst("#content")

		self.widget.show()
		self.startup()
	"""

	def startup(self, **kwargs):
		session_dir = get_running_session()
		if session_dir:
			self.manager = ServiceManager(self.spec, session_dir)
			self("index", **kwargs)
			return
		self.__content("start_session.html")

	def start_session(self, session_id, **kwargs):
		try:
			session_dir = ServiceManager.create_session_dir(self.base_dir, session_id)
		except ServiceManager.SessionExists, e:
			# TODO: Show using the html stuff
			QMessageBox(QMessageBox.Critical,
				"Can't create session", str(e)).exec_()
			
			self("startup")
			return

		self.manager = ServiceManager(self.spec, session_dir)
		self("index")
	
	def index(self, **kwargs):
		if not self.manager: return self("startup", **kwargs)
		self.__content("main.html")

	def confirm_shutdown(self, **kwargs):
		self.__content("confirm_shutdown.html")

	def do_shutdown(self, **kwargs):
		self.__content("do_shutdown.html")
		try:
			self.manager.shutdown()
		finally:
			self.app.quit()

	def run(self):
		self.widget.show()
		self("index")
		#self.widget.load(QUrl(self.main_template))
		#self.widget.loadFinished.connect(self.initialize)

		signal.signal(signal.SIGINT, signal.SIG_DFL)
		self.app.exec_()

class DialogCancelled(Exception): pass

def _run_dialog(command):
	"""
	:todo: Not probably the most beautiful approach
	"""
	try:
		output = subprocess.check_output(command, shell=True)
	except subprocess.CalledProcessError, e:
		raise DialogCancelled
	
	return output

def string_dialog(name, title):
	cmd = 'zenity --entry '\
		'--text="%s" --title "%s"'%(name, title)
	output = _run_dialog(cmd)
	
	return output.strip()

def confirm_dialog(question, title):
	_run_dialog('zenity --question --text "%s" --title "%s"'%(question, title))
