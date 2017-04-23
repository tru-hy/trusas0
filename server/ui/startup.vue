<script lang="coffee">
Promise = require 'bluebird'
axios = require 'axios'
R = require 'lazyremote'
module.exports =
	data: ->
		sessionId: ""
		YESSHOWITDAMN: true
	
	mounted: ->
		@$el.querySelector("#session_id input").focus()
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
			@sessionId = await R.resolve @$router.trusas.sessions.date()
		
		start: ->
			s = await R.resolve @$router.trusas.sessions.createSession @sessionId
			@$router.replace "/session/#{s}"

</script>


<template lang="pug">
v-app
	v-modal(persistent,v-bind:value="true")
					v-card.startSession
						v-card-row.success
							v-card-title.white--text Start a new session
						v-card-text
							v-row
								v-text-field(
									persistent-hint,
									id="session_id",
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
