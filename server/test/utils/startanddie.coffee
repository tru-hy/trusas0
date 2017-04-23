server = require '../../service.coffee'
spec = require '../timestamper.coffee'

do ->
	dir = process.argv[2]
	sid = process.argv[3]
	server = new server.SessionServer spec, dir
	await server.createSession sid
	process.exit()
