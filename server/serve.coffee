#!/usr/bin/env coffee

yargs = require 'yargs'
axios = require 'axios'
express = require 'express'
lodash = require 'lodash'
#LazyRemote = require 'lazyremote-koa'
L = require 'lazyremote'
child_process = require 'child_process'

Service = require './service.coffee'

util = require 'util'

serve = (opts={}) ->
	app = express()
	app.use express.static 'ui'
	require('express-ws')(app)
	spec = require './testpipe.coffee'
	
	api = ->
		lodash: lodash
		sessions: new Service.SessionServer spec, opts.directory
	
	app.ws '/api/v1', (socket) ->
		L socket, expose: api()
		#zone = Zone.current.fork({})
		#task = zone.run ->
		#	L socket, expose: api()
		#socket.onclose = ->
		#	zone.cancelTask task
		
	app.listen 3000


if module == require.main
	opts = yargs
		.option 'directory', alias: 'd', describe: 'base directory for sessions'
		.demandOption(['directory'])
		.help()
		.argv
	serve opts
