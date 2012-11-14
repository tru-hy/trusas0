# Not even attempting any autoconfiguration.
# You will most likely have to edit these if you
# want to compile this. Also assumes the needed tools
# are in PATH
ANDROID_JAR=/opt/android-sdk/platforms/android-10/android.jar
GSON_JAR=lib/gson-2.2.2.jar

SENSOR_PORT=27545
LOCATION_PORT=27546

BUILD_DIR=build
PACKAGE_PATH=independent/trusas
JFLAGS =  -target 1.6 -d $(BUILD_DIR) -cp $(ANDROID_JAR):$(GSON_JAR)
JC = javac

TrusasSensorDump.apk : TrusasSensorDump-unsigned.apk Insecure.keystore
	jarsigner -keystore Insecure.keystore -storepass dontcare -keypass dontcare -signedjar $@ $< dontcare

TrusasSensorDump-unsigned.apk : bin/classes.dex AndroidManifest.xml
	aapt package -f -M AndroidManifest.xml -S res -I $(ANDROID_JAR) -F $@ bin

bin/classes.dex : $(BUILD_DIR)/$(PACKAGE_PATH)/DataDump.class
	mkdir -p bin
	dx --dex --output=$@ $(BUILD_DIR) lib

sources=$(wildcard *.java) 
$(BUILD_DIR)/$(PACKAGE_PATH)/DataDump.class : $(sources) $(BUILD_DIR)/$(PACKAGE_PATH)/R.java | $(GSON_JAR)
	$(JC) $(JFLAGS) $^

$(BUILD_DIR)/$(PACKAGE_PATH)/R.java : AndroidManifest.xml res/drawable/status_icon.png
	mkdir -p $(BUILD_DIR)
	aapt package -f -m -S res -J build -M AndroidManifest.xml -I $(ANDROID_JAR)

res/drawable/status_icon.png : ../../res/logo.svg
	mkdir -p res/drawable
	convert -background transparent -antialias -interpolate nearest $^ \
		-resize 25x25 -negate -antialias -interpolate nearest \
		-background transparent -gravity center \
		-extent 25x25 PNG32:$@

$(GSON_JAR): $(GSON_JAR) | lib
	wget http://google-gson.googlecode.com/files/google-gson-2.2.2-release.zip -O /tmp/gson.zip
	unzip -o /tmp/gson.zip google-gson-2.2.2/gson-2.2.2.jar
	mv google-gson-2.2.2/gson-2.2.2.jar lib
	rmdir google-gson-2.2.2
	
lib:
	mkdir -p lib
	

Insecure.keystore : Insecure.keystore
	keytool -genkeypair -storepass dontcare -keypass dontcare -dname "O=dontcare" -keystore Insecure.keystore -alias dontcare -validity 10000

#build/independent/trusas/TrusasSensorDump.class : TrusasSensorDump.java
#	javac -target 1.6 -d build -cp $(ANDROID_JAR):$(GSON_JAR) $^


.PHONY: install
install : TrusasSensorDump.apk
	adb install -r $^

.PHONY: start_sensors
start_sensors: install
	adb shell am startservice -a independent.trusas.SensorDumpManager

.PHONY: test_sensors
test_sensors : start_sensors
	adb forward tcp:$(SENSOR_PORT) tcp:$(SENSOR_PORT)
	sleep 1
	nc localhost $(SENSOR_PORT)

.PHONY: test_location
test_location : install
	adb forward tcp:$(LOCATION_PORT) tcp:$(LOCATION_PORT)
	adb shell am startservice -a independent.trusas.LocationDumpManager
	sleep 1
	nc localhost $(LOCATION_PORT)

