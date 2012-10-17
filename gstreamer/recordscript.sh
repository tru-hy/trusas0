VIDEO_DEVICE="/dev/video0"
AUDIO_DEVICE="hw:1,0"

v4l2-ctl -d /dev/video0 -c focus_auto=0,focus_absolute=0

gst-launch-0.10 uvch264_src device="$VIDEO_DEVICE" auto-start=true fixed-framerate=true initial-bitrate=5000000 name=src \
	mpegtsmux m2ts-mode=true name=mux ! queue ! filesink location=$1 \
	src.vidsrc ! video/x-h264,width=1920,height=1080,framerate=30/1 ! queue ! h264parse ! mux. \
	src.vfsrc ! video/x-raw-yuv,framerate=30/1 ! queue ! xvimagesink \
	\
	alsasrc device="$AUDIO_DEVICE" ! queue ! voaacenc !  mux.
