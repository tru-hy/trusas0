from trusas0 import ROOT
from trusas0.service import ServiceSpec
from trusas0.ui import SessionUi

s = ServiceSpec()
s['dummy'] = ROOT+'/dummy_service.py'

SessionUi(s, '/tmp/sessions').run()
