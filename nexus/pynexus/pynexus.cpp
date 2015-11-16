/* A really ugly C-shim to be used with ctypes */

#include "TmsiAmplifier.h"
#include <iostream>

extern "C" {

struct nexus_struct {
	TmsiAmplifier *amp = NULL;
	vector<float> buffer;
	string error = "";
	// Hacky buffer used to pass channel
	// names to numpy.
	string _channelNames;
};

nexus_struct *start(const char *btaddr) {
	nexus_struct *nexus = new nexus_struct;
	try {
		nexus->amp = new TmsiAmplifier(btaddr, BLUETOOTH_AMPLIFIER);
	} catch (exception& e) {
		nexus->error = e.what();
		return nexus;
	}
	vector<string> enabled_channels;
	for(int i = 0; i < nexus->amp->channels_desc.size(); ++i) {
		channel_desc &desc = nexus->amp->channels_desc[i];
		enabled_channels.push_back(desc.name);
	}
	nexus->amp->set_active_channels(enabled_channels);
	nexus->buffer.resize(enabled_channels.size());
	nexus->amp->start_sampling();
	return nexus;
}

const char *get_error(nexus_struct *nexus) {
	return nexus->error.c_str();
}

int number_of_channels(nexus_struct *nexus) {
	return int(nexus->buffer.size());
}

const char *channel_names(nexus_struct *nexus) {
	string& names = nexus->_channelNames;
	names.clear();
	for(int i = 0; i < nexus->amp->channels_desc.size(); ++i) {
		channel_desc &desc = nexus->amp->channels_desc[i];
		names += desc.name + ",";
	}

	return names.c_str();

}

float *fetch_data(nexus_struct *nexus) {
	nexus->amp->fill_samples(nexus->buffer);
	float* data = &(nexus->buffer.front());
	return data;
}

void close(nexus_struct *nexus) {
	delete nexus->amp;
	delete nexus;
}

}
