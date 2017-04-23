path = require 'path'

module.exports =
	label: "Test session"
	services:
		test:
			command: path.join __dirname, '../../timestamper.py'
			label: 'Current time'
	
