#!/usr/bin/env python2

from trusas0.packing import default_unpacker, default_packer
from trusas0.utils import get_logger
log = get_logger()

def map_from_android(event):
	d = {}
	d['provider'] = event['mProvider']
	d['latitude'] = event['mLatitude']
	d['longitude'] = event['mLongitude']
	if event['mHasAltitude']:
		d['altitude'] = event['mAltitude']
	if event['mHasBearing']:
		d['bearing'] = event['mBearing']
	if event['mHasSpeed']:
		d['speed'] = event['mSpeed']
	if event['mHasAccuracy']:
		d['accuracy'] = event['mAccuracy']

	return d

def main():
	unpacker = default_unpacker()
	packer = default_packer()

	for header, event in unpacker:
		mapped = map_from_android(event)
		if mapped is None: continue
		packer.send(mapped, header=header)

if __name__ == '__main__':
	main()
