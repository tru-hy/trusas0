gst-launch -v -m uvch264_src auto-start=true initial-bitrate=5000000 name=src \
	mpegtsmux m2ts-mode=true name=mux ! queue ! filesink location=$1 \
	src.vidsrc ! video/x-h264,width=1920,height=1080,framerate=30/1 ! queue ! h264parse ! mux. \
	src.vfsrc ! video/x-raw-yuv, width=640, height=360, framerate=30/1 ! queue ! autovideosink \
	\
	alsasrc device="hw:1,0" ! queue ! voaacenc !  mux.
