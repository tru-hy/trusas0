#include "TmsiAmplifier.h"
#include <vector>
#include <iostream>
#include <string>

using std::vector;
using std::string;

int main()
{
	TmsiAmplifier amp("00:A0:96:2F:A8:A6", BLUETOOTH_AMPLIFIER);
	vector<string> enabled_channels;
	for(int i = 0; i < amp.channels_desc.size(); ++i) {
		channel_desc &desc = amp.channels_desc[i];
		enabled_channels.push_back(desc.name);

	}
	amp.set_active_channels(enabled_channels);
	amp.start_sampling();
	vector<float> samples(enabled_channels.size());
	for(;;) {
		amp.fill_samples(samples);
		float* data = &samples.front();
		for(int i = 0; i < enabled_channels.size(); ++i) {
			std::cout << enabled_channels[i] << data[i] << " ";
		}
		std::cout << std::endl;
	}
}
