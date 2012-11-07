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
from trusas0.utils.logutils import LogWatcher
from trusas0.utils import register_shutdown, Hook, logutils
import logging


class StaticWebPage(QWebPage):
	def __init__(self, controller, template, *args, **kwargs):
		QWebPage.__init__(self, *args, **kwargs)
		self.controller = controller
		
		base_url = path.dirname(template)
		baseUrl = QUrl("file://"+base_url+"/")
		with open(template, 'r') as content_file:
			self.mainFrame().setHtml(content_file.read(),
					baseUrl=baseUrl)
		
	

	def acceptNavigationRequest(self, frame, request, type):
		if type == QWebPage.NavigationTypeOther:
			return True
		
		base_url = self.mainFrame().baseUrl()
		url = request.url()
		
		# For some reason isRelative don't work for file-urls
		if not base_url.isParentOf(url):
			log.error("Page called with unexpected url %s"%url.toString())
			return False
		
		action = str(url.path())[len(base_url.path()):]
		args = {str(k): str(v) for (k, v) in url.queryItems()}
		getattr(self.controller, action)(**args)
		return False

class WebUi(object):
	def __init__(self, base_file):
		self._widget = QWebView()
		page = StaticWebPage(self, base_file)
		self._widget.setPage(page)
		page.loadFinished.connect(self._init)

	def _init(self, *args):
		self._dom = self._widget.page().mainFrame().documentElement()


class SessionUi(WebUi):
	def __init__(self, spec, base_dir, content):
		# OH GOD THE HACKS!
		spec.instance = Hook(spec.instance)
		spec.instance.after.connect(self.__setup_my_logger)
		self._spec = spec
		self._base_dir = base_dir
		self._content = content
		
		self._templatedir = path.join(path.dirname(__file__), 'template')
		template_file = path.join(self._templatedir, "index.html")
		WebUi.__init__(self, template_file)

		self._spec = spec
		self._session_base_dir = base_dir

		self._log_watcher = logutils.LogWatcher()

		self._manager = None
		
		page = self._widget.page()
		embed = WidgetEmbedFactory(self)
		page.setPluginFactory(embed)
		page.settings().setAttribute(QWebSettings.PluginsEnabled, True)

	def __template_data(self, template):
		template = path.join(self._templatedir, template)
		with open(template) as html:
			return html.read()	

	def __template_content(self, element, template):
		element.setInnerXml(self.__template_data(template))

	def __content(self, template):
		self._js("$('#content').addClass('hide')")
		self.__template_content(
			self._dom.findFirst("#extra_content"),
			template)
		self._js("$('#extra_content').removeClass('hide')")
	
	def _init(self, ok):
		WebUi._init(self, ok)
		session_dir = get_running_session()
		if session_dir:
			# On reattach, seek to the last line of the log.
			# TODO: We may miss some notifications that has happened
			#	while the session has been running "blindly",
			#	but I'll live with this for now.
			#	Also this is in a weird place as the startup
			#	architecture is currently a mess.
			self._log_watcher.only_new = True
			self._manager = self._spec.instance(session_dir).start()
			self._start_main_ui()
		else:
			self._startup()
	
	def __setup_my_logger(self, manager, session_dir):
		session_dir = manager.session_dir
		formatter = type(trusas0.utils.logutils.log_formatter)()
		my_path = path.join(session_dir, "_ui.log")
		handler = logging.FileHandler(my_path)
		self._log_watcher.add_path(my_path)
		handler.setFormatter(formatter)
		logging.root.addHandler(handler)
	

	def _startup(self):
		self.__content("start_session.html")

	def _js(self, js):
		return self._widget.page().mainFrame().evaluateJavaScript(js)
	
	def index(self):
		# We don't want to remove the element containing the widgets
		# as this will cause their Qt widgets to be deleted which isn't
		# nice. There's probably a better way for this too. This
		# still nags in the stdout btw.
		self._js("$('#extra_content').addClass('hide')")
		self._js("$('#content').removeClass('hide')")

	def create_session(self, session_id, **kwargs):
		try:
			session_dir = ServiceManager.create_session_dir(
					self._base_dir, session_id)
		except ServiceManager.SessionExists, e:
			self.__nag("error", "Session with ID <strong>%s</strong> already exists! Try another name."%session_id)			
			return

		self._manager = self._spec.instance(session_dir).start()
		self._start_main_ui()


	def _start_main_ui(self):
		self._dom.findFirst("#content").setInnerXml(self._content)
		# TODO: The whole startup is a mess. Maybe session creation
		#	should be in a totally separate class so we wouldn't
		#	have these weird implicit states?
		for name, service in self._manager.services.iteritems():
			self._log_watcher.add_path(service.errfile)
		nag_timer = QTimer()
		nag_timer.timeout.connect(self._do_maintenance)
		nag_timer.start(100)
		self.__nag_timer = nag_timer
		self.index()

	def __javascript(self, code):
		self._widget().page().mainFrame().evaluate_javascript(code)

	def __nag(self, level, content):
		classes = dict(
			info="alert-info",
			warning="",
			error="alert-error",
			critical="alert-error")
		data = self.__template_data('nag.html')
		alert_class = classes.get(level, 'alert-error')
		data = data%{'alert_class': alert_class, 'content': content}
		self._dom.findFirst("#nags").appendInside(data)
	
	def _do_maintenance(self, *args):
		for name in self._manager.newly_dead_services():
			log.critical("Service %s died!"%name)
			data = self.__template_data('dead_service.html')
			data = data%dict(name=name)
			self._dom.findFirst("#dead_services").appendInside(data)

		for logpath, record in self._log_watcher.nonblock_iter():
			try:
				if record['levelno'] < logging.WARNING:
					continue
				self.__nag(level="error", content=record['msg'])
			except:
				log.exception("Error while showing an error message, how embarassing (and potentially recursive).")

	def force_start_service(self, name):
		self._manager.ensure_service(name)

	def confirm_shutdown(self):
		if self._manager is None:
			self._widget.close()
			return

		self.__content("confirm_shutdown.html")

	def do_shutdown(self):
		self.__content("do_shutdown.html")
		if self._manager is None:
			self._widget.close()
			return
		try:
			self._manager.shutdown()
		finally:
			self._widget.close()
					
	def _shutdown(self, **kwargs):
		# My children go with me from this cruel world!
		process_group = os.getpgrp()
		# But I'll go last!
		orig_handler = signal.signal(signal.SIGTERM, lambda *args: None)
		try:
			os.killpg(process_group, signal.SIGTERM)
		finally:
			signal.signal(signal.SIGTERM, orig_handler)
		# :todo: It would be nice to wait for all of them
		#	to really stop so we won't leave orphans,
		#	but let's leave the task for init for now.


def run_ui(spec, base_dir, content):
	app = QApplication([])
		
	ui = SessionUi(spec, base_dir, content)


	# Apparently QApplication hates to be out-scoped (leading
	# to a segfault), so let's keep it here.
	# :todo: Doesn't fix it
	ui._apphack = app

	def ui_shutdown(**kwargs):
		ui._shutdown()
		app.exit()
	register_shutdown(ui_shutdown)
	#ui._widget.showFullScreen()
	ui._widget.show()
	app.exec_()
	

class WidgetEmbedFactory(QWebPluginFactory):
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
			try:
				service = self.ui._manager.services[param["service"]]
			except KeyError:
				log.error("The interface thinks there should be a service '%s', but there's not. This is an configuration error."%param["service"])
				return None
			args['service_out'] = service.outfile
		
		command = param["command"]%args
		
		if find_x_window_id(window):
			log.info("Using an existing process for command %s"%command)
			return widget
		
		log.info("Launching widget command: %s"%command)
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
		# TODO: The poll interval has to be (too) large now
		#	because apparently this will get called multiple
		#	times in parallel(?) if the swallow is too slow. Or
		#	something else weird is happening, has the windows
		#	tend to "flicker" with small intervals

		for name, widget in self.widgets.iteritems():
			try:
				winid = widget.clientWinId()
			except RuntimeError:
				# If we hide the element that contains
				# the widget, Qt deletes the underlying
				# widget.
				# :todo: Fix this perhaps using iframes
				#	which would maybe also allow
				#	proper z-indexing for the embedded
				#	widgets
				winid = 0
				widgets = QX11EmbedContainer(self.parent())
				self.widgets[name] = widget
			
			if winid > 0:
				continue
			wid = find_x_window_id(name)
			if not wid: continue
			try:
				widget.embedClient(wid)
			except RuntimeError:
				# See above
				pass
			


def find_x_window_id(name):
	# Most likely not the most efficient nor nice way to do this
	try:
		output = subprocess.check_output(('xwininfo -name %s'%name).split(),
			stderr=open(os.devnull,"w"))
	except Exception, e:
		# Too much spam for even debug log
		#log.debug("xwininfo failed: %s"%(str(e)))
		return None

	matches = re.search('^xwininfo: Window id: 0x([0-9A-Fa-f]+)', output, re.MULTILINE)
	if not matches: return None
	return int(matches.groups()[0], base=16)
	

