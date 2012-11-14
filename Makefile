.PHONY: all
all: android nexus

.PHONY: android
android:
	make -C android/java

.PHONY: nexus
nexus:
	make -C nexus/pynexus
	
