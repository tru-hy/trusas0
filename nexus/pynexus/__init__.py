import ctypes
from os import path

_lib = ctypes.CDLL(path.join(path.dirname(__file__), "libpynexus.so"))

class NexusException(Exception): pass

class Nexus(object):
	
	def __init__(self, btaddr):
		self.__nexus = _lib.start(btaddr)
		error = ctypes.c_char_p(_lib.get_error(self.__nexus)).value
		if error:
			raise NexusException(error)

		self.n_chans = _lib.number_of_channels(self.__nexus)
		names = ctypes.c_char_p(_lib.channel_names(self.__nexus)).value
		self.chan_names = names.split(",")[:-1]

	def __iter__(self): return self
	
	def next(self):
		data = _lib.fetch_data(self.__nexus)
		data = ctypes.cast(data, ctypes.POINTER(ctypes.c_float))[:self.n_chans]
		return dict((self.chan_names[i], data[i]) for i in range(self.n_chans))

if __name__ == '__main__':
	dev = Nexus("00:A0:96:2F:A8:A6")
	for sample in dev:
		print sample
