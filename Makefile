.PHONY: all
all: android nexus

.PHONY: android
	make -C android/java

.PHONY: nexus
	make -C nexus/pynexus
	
