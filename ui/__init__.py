import os
from os import path
import trusas0
from trusas0.service import ServiceManager, get_running_session
from PyQt4.Qt import *
from PyQt4.QtGui import *
import signal
import subprocess
import re
import trusas0.utils; log = trusas0.utils.get_logger()

class SessionUi(object):
	"""
	:todo: Refactor the generic page-backend-stuff to a separate
		class
	:todo: Figure out how to prevent QWebView not to reload
		the DOM on new url
	"""
	def __init__(self, spec, base_dir, content):
		self.spec = spec
		self.base_dir = base_dir
		# So annoying that QApplication must be
		# created before any widgets
		self.app = QApplication([])
		self.widget = QWebView()
		self.widget.page().settings().setAttribute(
			QWebSettings.PluginsEnabled, True)
		
		self.main_content = content

		self.embed = WidgetEmbedFactory(self, parent=self.widget)
		self.widget.page().setPluginFactory(self.embed)
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

	def startup(self, **kwargs):
		session_dir = get_running_session()
		if session_dir:
			self.manager = self.spec.instance(session_dir).start()
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

		self.manager = self.spec.instance(session_dir).start()
		self("index")
	
	def index(self, **kwargs):
		if not self.manager: return self("startup", **kwargs)
		self.content.setInnerXml(self.main_content)
		container = self.dom.findFirst("#embedded-widgets")

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
			
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		self.app.exec_()

class WidgetEmbedFactory(QWebPluginFactory):
	# TODO: Refactor this 2:20AM-code
	def __init__(self, ui, parent=None, poll_interval=1.0,):
		QWebPluginFactory.__init__(self, parent)
		self.poll_interval = poll_interval
		self.ui = ui
		
		self.widgets = {}

		# There's probably a way to get notified
		# by X when a new window opens, but this
		# must suffice for now
		self.swallow_timer = QTimer()
		self.swallow_timer.timeout.connect(self._swallow_windows)
	
	def create(self, mimeType, url, names, values):
		if mimeType != "x-trusas/widget":
			return None
		
		self.swallow_timer.start(int(self.poll_interval*1000))
		param = dict((str(n), str(v)) for (n, v) in zip(names, values))
		
		window = param["window"]
		if window not in self.widgets.iteritems():
			self.widgets[window] = QX11EmbedContainer(self.parent())

		widget = self.widgets[window]

		if "command" not in param:
			return widget
		
		args = dict(ROOT=trusas0.ROOT)
			
		if "service" in param:
			service = self.ui.manager.services[param["service"]]
			args['service_out'] = service.outfile
		
		command = param["command"]%args

		subprocess.Popen(command, shell=True)
		return widget
		
	
	def plugins(self):
		plugin = QWebPluginFactory.Plugin()
		plugin.name = "Trusas embedder"
		plugin.description = "Embed anything"	
		mimeType = QWebPluginFactory.MimeType()
		mimeType.name = "x-trusas/widget"
		mimeType.description = "Trusas widget"
		mimeType.fileExtensions = []
		plugin.mimeTypes = [mimeType]
		return [plugin]

	def _swallow_windows(self):
		for name, widget in self.widgets.iteritems():
			if widget.clientWinId() > 0:
				continue
			wid = find_x_window_id(name)
			if not wid: continue
			widget.embedClient(wid)
			


def find_x_window_id(name):
	# Most likely not the most efficient nor nice way to do this
	try:
		output = subprocess.check_output(('xwininfo -name %s'%name).split())
	except Exception, e:
		log.debug("xwininfo failed: %s"%(str(e)))
		return None

	matches = re.search('^xwininfo: Window id: 0x([0-9A-Fa-f]+)', output, re.MULTILINE)
	if not matches: return None
	return int(matches.groups()[0], base=16)
	

