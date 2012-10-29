#include "TmsiAmplifier.h"
#include <iostream>

extern "C" {

typedef struct nexus_struct {
	TmsiAmplifier *amp;
	vector<float> *buffer;
} nexus_struct;

nexus_struct *start(const char *btaddr) {
	TmsiAmplifier *amp = new TmsiAmplifier(btaddr, BLUETOOTH_AMPLIFIER);
	nexus_struct *nexus = new nexus_struct;
	nexus->amp = amp;
	vector<string> enabled_channels;
	for(int i = 0; i < amp->channels_desc.size(); ++i) {
		channel_desc &desc = amp->channels_desc[i];
		enabled_channels.push_back(desc.name);
	}
	amp->set_active_channels(enabled_channels);
	nexus->buffer = new vector<float>(enabled_channels.size());
	amp->start_sampling();
	return nexus;
}

int number_of_channels(nexus_struct *nexus) {
	return int(nexus->buffer->size());
}

const char *channel_names(nexus_struct *nexus) {
	string names;
	for(int i = 0; i < nexus->amp->channels_desc.size(); ++i) {
		channel_desc &desc = nexus->amp->channels_desc[i];
		names += desc.name + ",";
	}

	return names.c_str();

}

float *fetch_data(nexus_struct *nexus) {
	nexus->amp->fill_samples(*(nexus->buffer));
	float* data = &(nexus->buffer->front());
	return data;
}

void close(nexus_struct *nexus) {
	delete nexus->amp;
	delete nexus->buffer;
	delete nexus;
}

}
