Promise = require 'bluebird'
Process = require 'process'
Path = require 'path'
child_process = require 'child_process'
EventEmitter = require 'events'
Tail = require('tail-stream')
Readline = require 'readline'
ShellQuote = require 'shell-quote'
disown = require './utils/disown.coffee'
Lockfile = Promise.promisifyAll require 'lockfile'
_ = require 'lodash'

Most = require 'most'
Most.hold = require('@most/hold').hold
Most.create = require('@most/create').create
fs = Promise.promisifyAll require 'fs'

class ServiceError extends Error
class SessionError extends Error

Sleep = (duration) -> new Promise (a) -> setTimeout a, duration

pid_is_running = (pid) ->
	try
		process.kill(pid, 0)
		return true
	catch
		return false

OUT_TEMPLATE="$(directory)"

class Runner extends EventEmitter
	constructor: (@name, @service, @directory) ->
		super()
		@pidfile = Path.join @directory, '_pids', @name + '.pid'
		@pidlock = Path.join @directory, '_pids', @name + '.pidlock'
		@outfile = (Path.join @directory, @name + ".jsons")
		@errfile = (Path.join @directory, @name + ".err")
		
		
		s = Tail.createReadStream @outfile,
			beginAt: 'end'
			waitForCreate: true
		Readline.createInterface input: s, terminal: false
		.on "line", (line) =>
			obj = JSON.parse line
			@emit "sample", obj
		
		@state = Most.hold Most.skipRepeats Most.create (add, end, error) =>
			state = undefined
			until state == 'terminated'
				state = await @getState()
				add state
				await Sleep 100
			end()

	wait_for: (target) ->
		await @state.filter((s) -> s == target).take(1).drain()

	get_pid: ->
		parseInt await fs.readFileAsync @pidfile
	
	has_pid: ->
		@get_pid()
		.then -> true
		.catch -> false
	
	is_running: ->
		try
			pid = await @get_pid()
		catch error
			if error.code == 'ENOENT'
				return false
			else
				throw error
		return pid_is_running pid

	_withPidlock: (f) ->
		try
			await Lockfile.lockAsync @pidlock, wait: 10000
			return f()
		finally
			await Lockfile.unlockAsync @pidlock



	start: -> @_withPidlock =>
		state = await @_checkState()
		if state != 'unstarted' and state != 'dead'
			throw new SessionError "The service #{@name} is already in state #{state}!"
		out = await fs.openAsync @outfile, 'a'
		err = await fs.openAsync @errfile, 'a'
		if Array.isArray @service.command
			command = @service.command
		else
			command = ShellQuote.parse @service.command
		#process = child_process.spawn command[0],
		pid = await disown command,
			stdout: @outfile
			stderr: @errfile
			detached: true
		await fs.writeFileAsync @pidfile, String(pid)
	
	_checkState: ->
		try
			pid = await @get_pid()
		catch error
			if error.code == 'ENOENT'
				return "unstarted"
			else
				throw error
		if pid == 0
			return "terminated"

		if pid_is_running pid
			return "running"
		else
			return "dead"


	getState: -> @_withPidlock =>
		@_checkState()
			
	terminate: -> @_withPidlock =>
		state = await @_checkState()
		
		return if state == 'terminated'

		if state in ['dead', 'unstarted']
			await fs.writeFile @pidfile, "0"
			return
		
		pid = await @get_pid()
		if pid == 0
			console.warn "Somebody cleared the pidfile #{@pidfile} without a lock!"
			return
		while true
			try
				process.kill pid, 'SIGTERM'
			catch error
				if error.code == 'ESRCH'
					await fs.writeFileAsync @pidfile, "0"
					break
				else
					throw error
			await Sleep 100

class @SessionServer
	constructor: (@spec, @base_directory) ->
		@lockfile = Path.join @base_directory, '_session.lock'
		@__session_cache = {}
	
	date: -> (new Date()).toISOString()
	
	activeSessionId: ->
		try
			session_id = String await fs.readFileAsync @lockfile
		catch error
			if error.code == 'ENOENT'
				return null
			else
				throw error
		
		return session_id

		@__active_session = new Session @spec, @base_directory, session_id
	
	getSession: (session_id) ->
		return new Session @spec, @base_directory, session_id

	createSession: (session_id, opts={}) ->
		if fs.existsSync @lockfile
			throw new SessionError("Session already running!")
		directory = Path.join @base_directory, session_id
		if fs.existsSync directory
			throw new SessionError("Session with id #{session_id} already exists!")
		fs.mkdirSync directory
		await fs.writeFileAsync @lockfile, session_id
		session = @getSession session_id
		if opts.autostart ? true
			await session.start()
		return session_id

class Session
	constructor: (@spec, @base_directory, @session_id) ->
		@directory = Path.join @base_directory, @session_id
		try
			fs.mkdirSync Path.join @directory, '_pids'
		catch e
			if e.code != 'EEXIST'
				throw e
		@services = {}
		for name, service of @spec.services
			@services[name] = new Runner name, service, @directory
		@lockfile = Path.join @base_directory, '_session.lock'
		
	start: ->
		for name of @spec.services
			await @service(name).start()
	
	terminate: ->
		for name of @spec.services
			await @service(name).terminate()
		try
			await fs.unlinkAsync @lockfile
		catch

	
	service: (name) ->
		return @services[name]
	
