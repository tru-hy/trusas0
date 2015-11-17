libpynexus.so : TmsiAmplifier.cpp nexus/tmsi.c AmplifierDriver.cpp pynexus.cpp
	g++ -shared -g -fPIC -Wl,--no-as-needed -fpermissive -lbluetooth $^ -o $@

test : TmsiAmplifier.cpp nexus/tmsi.c AmplifierDriver.cpp test.cpp
	g++ -g -Wl,--no-as-needed -fpermissive -lbluetooth $^ -o $@
