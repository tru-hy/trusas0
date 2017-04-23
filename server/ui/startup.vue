<script lang="coffee">
Promise = require 'bluebird'
axios = require 'axios'
R = require 'lazyremote'
module.exports =
	created: ->
		@remote = @trusas()
		console.log @remote
		activeSession = await R.resolve(@remote.sessions.activeSession())
		console.log activeSession
		if activeSession
			@$router.replace "/session/"

	data: ->
		sessionId: ""

	computed:
		inputErrors: ->
			errors = []
			invalid = new Set @sessionId.match /[^\w-:.]/g
			if invalid.size
				invalid = [invalid...].map((c) -> "'#{c}'").join(', ')
				errors.push "No weird characters like #{invalid}"
			return errors
		isValid: ->
			@sessionId and not @inputErrors

	methods:
		useCurrentTimestamp: ->
			@sessionId = await R.resolve @remote.sessions.date()
		
		start: ->
			await R.resolve @remote.sessions.createSession @sessionId
			@$router.replace "/session/"

</script>


<template lang="pug">
v-app
	v-content
		v-container(fluid)
			v-row
				v-col(xs6,offset-xs3)
					v-card.startSession.elevation-1
						v-card-row.success
							v-card-title.white--text Start a new session
						v-card-text
							v-row
								v-text-field(
									name="sessionId",label="Session id",
									v-model="sessionId",required,
									prependIcon="label",
									hint="Enter an identifier for the session.",
									v-bind:rules="inputErrors"
									)
								v-btn.black--text(icon,
										v-tooltip:top="{html: 'Use current timestamp'}",
										@click.native="useCurrentTimestamp()"
										)
									v-icon access_time
								
						v-card-row(actions)
							v-btn(large,primary,:disabled="isValid",@click.native="start()") Start
				
</template>
