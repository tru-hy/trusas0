libpynexus.so : TmsiAmplifier.cpp nexus/tmsi.c AmplifierDriver.cpp pynexus.cpp
	g++ -shared -g -fPIC -fpermissive -lbluetooth $^ -o $@

test : TmsiAmplifier.cpp nexus/tmsi.c AmplifierDriver.cpp test.cpp
	g++ -g -fpermissive -lbluetooth $^ -o $@
