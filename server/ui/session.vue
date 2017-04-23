<style scoped>
.logo {
	text-align: center;
	padding: 10px;
	padding-top: 30px;
	color: white;
}
.viz-grid {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
}
</style>

<template lang="pug">
v-app(left-fixed-sidebar)
	main
		v-sidebar(v-model="sidebar",fixed)
			.logo
				img(src="logo.svg")
				.title trusas
			v-list(dense,v-if="session.services")
				v-divider(light)
				v-subheader Services
				v-list-item(v-for="(info, name) of session.services")
					v-list-tile(:title="info.state")
						v-list-tile-content
							v-list-tile-title {{info.service.label || name}}
							
						v-list-tile-action
							v-icon(v-if="info.state == 'running'",success,title='Running').success--text lens
							v-icon(v-else-if="info.state == 'terminated'",success,title='Finished').primary--text check_box
							v-icon(v-else-if="info.state == 'dead'",error,title='Dead').error--text error
							v-progress-circular(v-else,indeterminate,title='Unknown').primary--text
				v-divider(light)
				v-btn(large,warning,block,raised,@click.native="confirmTerminate = true") Terminate

		v-content
			v-alert(v-bind:value="isTerminated",info,icon="check_box")
				div This session is finished. You can look around, but nothing intresting's gonna happen.
					v-btn(primary,@click.native="$router.replace('/')") Start a new one
			v-container(fluid)
				.viz-grid
					v-card
							trusas-timeseries(v-if="getRemote()",:service="getRemote().services.test",:api="getApi()")
					v-card
							v-card-text STUFF
					v-card
							v-card-text STUFF
					v-card
							v-card-text STUFF
		
		v-modal(persistent,v-model="confirmTerminate")
			v-card
					v-card-row
						v-card-title Terminate Current Session?
					v-card-text Terminate the session only after the experiment is over.
					v-card-row(actions)
						v-btn(flat,@click.native="confirmTerminate = false") Cancel
						v-btn(flat,warning,@click.native="terminate(); confirmTerminate = false") Terminate
			

</template>

<script lang="coffee">
R = require('lazyremote')
Vue = require 'vue'
Vue.component 'trusas-timeseries', require './timeseries.vue'
module.exports =
	created: ->
		@api = @$router.trusas
		@remote = @api.sessions.getSession @$route.params.id
		@session = await R.resolve @remote
		for name of @session.services then do (name) =>
			s = @remote.services[name]
			@states[name] = 'unknown'
			await R.resolve s.state.forEach (state) =>
				@session.services[name].state = state
				@states[name] = state
	
	data: ->
		session: {}
		confirmTerminate: false
		sidebar: true
		states: {}
	
	computed:
		isTerminated: ->
			for name, service of @session.services
				if service.state != 'terminated'
					return false
			return true

	methods:
		getRemote: -> @remote
		getApi: -> @api
		terminate: ->
			await R.resolve @remote.terminate()
</script>
