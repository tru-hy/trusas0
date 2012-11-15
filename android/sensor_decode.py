#!/usr/bin/env python2

from trusas0.packing import default_unpacker, default_packer
from trusas0.utils import get_logger
log = get_logger()

# See http://developer.android.com/reference/android/hardware/Sensor.html
# and hope Google keeps ABI compatibility in this.
SENSOR_TYPES = {
	1:	'accelerometer',
	13:	'ambient_temperature',
	9:	'gravity',
	4:	'gyroscope',
	5:	'light',
	10:	'linear_acceleration',
	2:	'magnetic_field',
	3:	'orientation',
	6:	'pressure',
	8:	'proximity',
	12:	'relative_humidity',
	11:	'rotation_vector',
	7:	'temperature'
	}

SENSOR_MAPPINGS = dict(
	linear_acceleration=lambda v: {
			'accel_x': v[0],
			'accel_y': v[1],
			'accel_z': v[2]
			},
	
	gyroscope=lambda v: {
			'rot_rate_x': v[0],
			'rot_rate_y': v[1],
			'rot_rate_z': v[2]
			}
	)

def map_from_android(event):
	# TODO: Due to hackery in sensors.py
	#sensor_type = SENSOR_TYPES[event['sensor']['mType']]
	sensor_type = SENSOR_TYPES[event['sensor_type']]

	if sensor_type not in SENSOR_MAPPINGS:
		return None
	
	return SENSOR_MAPPINGS[sensor_type](event['values'])

def main():
	unpacker = default_unpacker()
	packer = default_packer()

	for header, event in unpacker:
		mapped = map_from_android(event)
		if mapped is None: continue
		packer.send(mapped, header=header)

if __name__ == '__main__':
	main()
