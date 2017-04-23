<template lang="pug">
div
	router-view
	v-modal(v-if="socketStatus == 0",persistent,v-bind:value="true")
		v-card
			v-card-row
				v-card-title
					div(style="text-align: center; width: 100%;")
						div Connecting
						v-progress-circular(indeterminate)
	v-modal(v-if="socketStatus > 1",persistent,v-bind:value="true")
		v-card
			v-card-row
				v-card-title Connection dropped!
			v-card-text Lost connection to Trusas. Reloading the page may help.
			v-card-row(actions)
				v-btn(flat,primary,onclick="location.reload();") Reload
</template>
