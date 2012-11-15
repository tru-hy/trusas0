"""
TODO: Add the usual stuff that startup scripts need here so
	they don't have to import stuff from weird places
"""

import utils
import logging
from utils import sh
from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import run_ui

log = utils.get_logger()

def set_default_log():
	"""
	Set the default formatter for the console, the
	JSON version is a bit difficult to read
	Just assume it's the first

	:note: ui.run_ui sets up a separate logger for JSON,
		this should get a lot more opaque once it's refractored
		here.
	"""
	for handler in logging.root.handlers:
		if not isinstance(handler, logging.StreamHandler):
			continue
		handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
		break
set_default_log() # Set a nicer logging output for output scripts; the
		  # JSON is very difficult to work with while developing


