# Not even attempting any autoconfiguration.
# You will most likely have to edit these if you
# want to compile this. Also assumes the needed tools
# are in PATH
ANDROID_JAR=/opt/android-sdk/platforms/android-10/android.jar
GSON_JAR=lib/gson-2.2.2.jar

SENSOR_PORT=27545

#TrusasSensorDump.apk : 
#	aapt package -v -f -m -S res -J src -M AndroidManifest.xml -I /opt/android-sdk/platforms/android-15/android.jar
#	javac -d obj -classpath $(ANDROID_JAR) -sourcepath src src/trusas/*.java
#	dx --dex  --verbose --output=bin/classes.dex obj lib
#	aapt package -v -f -M AndroidManifest.xml -S res -I $(ANDROID_JAR) -F bin/AndroidTest.unsigned.apk bin
#

TrusasSensorDump.apk : TrusasSensorDump-unsigned.apk Insecure.keystore
	jarsigner -keystore Insecure.keystore -storepass dontcare -keypass dontcare -signedjar $@ $< dontcare

TrusasSensorDump-unsigned.apk : bin/classes.dex AndroidManifest.xml
	aapt package -f -M AndroidManifest.xml -I $(ANDROID_JAR) -F $@ bin

bin/classes.dex : build/independent/trusas/TrusasSensorDump.class
	dx --dex --output=$@ build lib

Insecure.keystore : Insecure.keystore
	keytool -genkeypair -storepass dontcare -keypass dontcare -dname "O=dontcare" -keystore Insecure.keystore -alias dontcare -validity 10000

build/independent/trusas/TrusasSensorDump.class : TrusasSensorDump.java
	javac -target 1.6 -d build -cp $(ANDROID_JAR):$(GSON_JAR) $^


.PHONY: install
install : TrusasSensorDump.apk
	adb install -r $^

.PHONY: start
start: install
	adb shell am startservice -a independent.trusas.TrusasSensorDump

.PHONY: test
test : start
	adb forward tcp:$(SENSOR_PORT) tcp:$(SENSOR_PORT)
	sleep 1
	nc localhost $(SENSOR_PORT)


