import Vue from 'vue'

import Vuetify from 'vuetify'
require 'vuetify/dist/vuetify.min.css'
Vue.use Vuetify

import VueRouter from 'vue-router'
Vue.use(VueRouter)

R = require 'lazyremote'

TrusasRemote = (url='/') ->
	remote = (await R '/api/v1/').root
	methods:
		trusas: -> remote

router = new VueRouter
	routes: [
		(path: '/', component: require './startup.vue'),
		(path: '/session/', component: require './session.vue')
	]

do ->
	remote = await TrusasRemote '/api/v1/'
	console.log remote
	Vue.mixin remote
	app = new Vue
		router: router
	app.$mount("#container")
