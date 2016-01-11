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
import itertools


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

	def _init(self, ok):
		page = self._widget.page()
		frame = page.mainFrame()
		document = frame.documentElement()
		self._dom = document
		
	def _js(self, js, ignore_return=True):
		if ignore_return:
			# Serializing the return value is a VERY (about 1GB memory)
			# expensive operation if it returns something from the DOM.
			# If a return value is needed, be sure to cast it so that
			# it doesn't refer to the DOM.
			js = js + ";null;"
		return self._widget.page().mainFrame().evaluateJavaScript(js)



class SessionUi(WebUi):
	def __init__(self, manager, was_running, content):
		self._manager = manager
		self._known_corpses = []
		
		self._log_watcher = logutils.LogWatcher()
		# On reattach, seek to the last line of the log.
		# TODO: We may miss some notifications that has happened
		#	while the session has been running "blindly",
		#	but I'll live with this for now.
		if was_running:
			self._log_watcher.only_new = True
		self.__setup_my_logger()

		self._content = content
		
		self.__nag_timer = QTimer()
		self.__nag_timer.timeout.connect(self._do_maintenance)
		
		self._templatedir = path.join(path.dirname(__file__), 'template')
		template_file = path.join(self._templatedir, "index.html")
		WebUi.__init__(self, template_file)

		page = self._widget.page()
		embed = WidgetEmbedFactory(self)
		page.setPluginFactory(embed)
		page.settings().setAttribute(QWebSettings.PluginsEnabled, True)
	
	def _reborn(self, name):
		try:
			self._known_corpses.remove(name)
		except ValueError:
			pass

	def __template_data(self, template):
		template = path.join(self._templatedir, template)
		with open(template) as html:
			return html.read()	

	def __template_content(self, element, template):
		element.setInnerXml(self.__template_data(template))

	def __content(self, template):
		# TODO: An unsuccesfull hack to try to keep the
		# 	QX11Embed widgets alive. Remove.
		self._js("$('#content').addClass('hide')")
		self.__template_content(
			self._dom.findFirst("#extra_content"),
			template)
		self._js("$('#extra_content').removeClass('hide')")
	
	def _init(self, ok):
		WebUi._init(self, ok)
		self._dom.findFirst("#content").setInnerXml(self._content)
		for name, service in self._manager.services.iteritems():
			self._log_watcher.add_path(service.errfile)

		# Start the manager before the nag_timer
		# starts to look for the pids
		self._manager.start()

		self.__nag_timer.start(100)
		self.index()
	
	def __setup_my_logger(self):
		session_dir = self._manager.session_dir
		formatter = type(trusas0.utils.logutils.log_formatter)()
		my_path = path.join(session_dir, "_ui.log")
		handler = logging.FileHandler(my_path)
		self._log_watcher.add_path(my_path)
		handler.setFormatter(formatter)
		logging.root.addHandler(handler)
	

	def index(self):
		# We don't want to remove the element containing the widgets
		# as this will cause their Qt widgets to be deleted which isn't
		# nice. There's probably a better way for this too. This
		# still nags in the stdout btw.
		self._js("$('#extra_content').addClass('hide')")
		self._js("$('#content').removeClass('hide')")

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
		for name in self._manager.dead_services():
			if name in self._known_corpses: continue
			log.critical("Service %s died!"%name)
			data = self.__template_data('dead_service.html')
			data = data%dict(name=name)
			self._dom.findFirst("#dead_services").appendInside(data)
			self._known_corpses.append(name)

		for logpath, record in self._log_watcher.nonblock_iter():
			try:
				if record['levelno'] < logging.WARNING:
					continue
				self.__nag(level="error", content=record['msg'])
			except:
				log.exception("Error while showing an error message, how embarassing (and potentially recursive).")

	def force_start_service(self, name):
		self._reborn(name)
		self._manager.ensure_service(name)

	def confirm_shutdown(self):
		self.__content("confirm_shutdown.html")

	def do_shutdown(self):
		self.__content("do_shutdown.html")
		# TODO: Errors (including and perhaps especially non-clean shutdowns)
		#	should be acknowledged before the UI closes
		self.__nag_timer.stop()
		if self._manager is None:
			self._widget.close()
			return
		try:
			self._manager.shutdown()
		finally:
			self._widget.close()
					
	def _shutdown(self, **kwargs):
		# TODO: The architecture really doesn't separate
		#	the real "business" logic from the UI,
		#	so stuff ends up in weird places like this,
		#	but we (or the embed thingie) started them,
		#	so let's clean up also.

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

class SessionStarterUi(WebUi):
	def __init__(self, spec, base_dir, content,
			startup_template=None, main_ui_cls=SessionUi):
		self._spec = spec
		self._base_dir = base_dir
		self._content = content
		self._main_ui_cls = main_ui_cls
		self._ui = None

		if startup_template is None:
			startup_template=trusas0.utils.relative(
				path.join("template", "start_session.html"))
		self._startup_template = startup_template
				
		

	def get_session_ui(self):
		session_dir = get_running_session()
		if session_dir:
			self._start_session(session_dir, True)
			return self._ui
		
		# TODO: WOW! This is quite horribly wrong! But for some reason
		# if we create the widgets now, but never show them,
		# the main UI will freeze at getting the DOM (weird, yes),
		# so defer until here.
		# TODO, FIXME: STOP DOING STUPID THINGS IN THE CONSTRUCTORS
		#		SO THESE ARE NEEDED!!
		#		- Butbutbut, I like the pseudo-RAII-thingie and
		#		  single-step initialization
		#		- FU! WE WRAPPERS DON'T CARE ABOUT YOUR WANTS
		#		  AND CRAZY REFTRACKING SCHEMES!
		#		  WRITE C++ AND SUFFER THE HELL IF YOU WANT
		#		  RAII YOU LAZY BUM!
		WebUi.__init__(self, self._startup_template)
		self._dialog = QDialog()
		# Why is there no dummy layout?
		self._dialog.setLayout(QStackedLayout())
		self._dialog.layout().addWidget(self._widget)
		#self._dialog.showFullScreen()
		self._dialog.show()
		self._dialog.exec_()
		return self._ui

	def cancel(self):
		self._dialog.reject()

	def create_session(self, session_id, **kwargs):
		try:
			session_dir = ServiceManager.create_session_dir(
					self._base_dir, session_id)
		except ServiceManager.SessionExists, e:
			if session_id == '':
				self._js("bootbox.alert('I really need that ID, so empty one isn\\'t an option!')")
				return
			self._js("bootbox.alert('Session with ID <strong>%s</strong> already exists! Try another ID.')"%session_id)			
			return

		self._start_session(session_dir, False)
		self._dialog.accept()
	
	def _start_session(self, session_dir, already_running):
		manager = self._spec.instance(session_dir)
		self._ui = self._main_ui_cls(manager=manager,
			content=self._content,
			was_running=already_running,
			)

def _qt_scope_hack(app):
	"""
	If QApplication gets out of scope before the
	program ends, it tends to segfault. This of course kills
	our otherwise nice shutdown handlers, so let's put it to
	the global scope as a workaroundhack. Other hack that works
	is to return the app from the function and make sure the
	caller makes a ref on it, but I'll rather contain the
	hackery here.
	"""
	hackname = "_qapp_hack"
	for retry in itertools.count(0):
		if hackname + str(retry) not in globals():
			break

	globals()[hackname] = app


def run_ui(spec, base_dir, content):

	# TODO: QApplication or something in Qt seems to
	# crash when we return from here. Investigate and hack around.
		
	app = QApplication([])
	_qt_scope_hack(app)
		
	start_ui = SessionStarterUi(spec, base_dir, content)
	
	ui = start_ui.get_session_ui()
	if ui is None: return
	
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
		# by X when a new window opens or better yet
		# make the clients to take a window id, but this
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
		#	tend to "flicker" with small intervals. Investigate
		#	and fix.

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
	

