assert = require 'assert'
Server = require '../service.coffee'
spec = require './timestamper.coffee'
fs = require 'fs'
rimraf = require 'rimraf'
path = require 'path'
child = require 'child_process'
treeKill = require 'tree-kill'

tmpdir = ->
	beforeEach ->
		@tmpdir = fs.mkdtempSync path.join __dirname, '/tmp/trusastest-'
	afterEach ->
		rimraf.sync @tmpdir

describe 'Startup', ->
	tmpdir()
	it 'starts and stops', ->
		console.log "HERE!"
		server = new Server.SessionServer spec, @tmpdir
		session = await server.createSession 'test', autostart: false
		assert .equal (await session.services['test'].getState()), 'unstarted'
		await session.start()
		assert .equal (await session.services['test'].getState()), 'running'
		pids = for name of spec.services
			await session.service(name).get_pid()
		for pid in pids
			assert.doesNotThrow -> process.kill(pid, 0)
		await session.terminate()
		assert .equal (await session.services['test'].getState()), 'terminated'
		
		for pid in pids
			assert.throws -> process.kill(pid, 0)
		
		await session.terminate()
	
	it 'service survives exit', ->
		sid = 'survivor'
		cp = child.fork require.resolve('./utils/startanddie.coffee'), [@tmpdir, 'survivor'],
			silent: false
		ecode = await( new Promise (a) -> cp.once 'exit', a )
		server = new Server.SessionServer spec, @tmpdir
		session = await server.activeSession()
		assert session
		await session.service('test').wait_for 'running'
		await session.terminate()
	
	it 'service survives tree kill', ->
		sid = 'survivor'
		cp = child.fork require.resolve('./utils/startandlive.coffee'), [@tmpdir, 'survivor'],
			silent: false

		msg = await new Promise (a) -> cp.once "message", a
		assert.equal msg, 'started'
		session = await (new Server.SessionServer spec, @tmpdir).activeSession()
		assert session
		await new Promise (a, r) -> treeKill cp.pid, 'SIGTERM', (err) ->
			if err
				r err
			else
				a()
		
		await new Promise (a) -> setTimeout a, 100
		assert await session.service('test').is_running()
		await session.terminate()
		"""
		session = await server.activeSession()
		assert.equal session.service('test').state, 'unknown'
		await session.start()
		assert.equal session.service('test').state, 'running'
		assert session
		await session.terminate()
		"""
	
