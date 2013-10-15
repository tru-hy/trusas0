from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import run_ui

s = ServiceSpec()
s['dummy'] = ROOT+'/dummy_service.py'

content = """<h3>Just a dummy session</h3>
	<p>Nothing to see here.</p>"""
run_ui(spec=s, base_dir='/tmp/sessions', content=content)
