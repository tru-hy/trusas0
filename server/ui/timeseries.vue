
<script lang="coffee">
require './bokeh-0.12.0.js'
require './bokeh-0.12.0.css'
plt = Bokeh.Plotting

R = require 'lazyremote'
module.exports =
	name: "trusas-timeseries"
	props:
		service: required: true
		api: required: true
		span: type: Number, default: 30
		maxSamples: type: Number, default: 10000
		bufferDuration: type: Number, default: 0.1
	
	mounted: ->
		#plot = plt.figure
		#	tools: false
		#	x_axis_type: 'datetime'
		xrng = new Bokeh.Range1d()
		yrng = new Bokeh.DataRange1d()
		console.log xrng
		#plot = new Bokeh.Plot
		#	x_range: xrng
		#	y_range: yrng
		plot = plt.figure
			x_range: xrng
			y_range: yrng
			tools: []
		plot.toolbar.logo = null
		plot.toolbar_location = null
		
		# EVERY FUCKING TIME!!
		#resize = =>
		#	#console.log @$el.clientWidth
		#	#plot.setv
		#	#	plot_width: @$el.clientWidth
		#	#	plot_height: @$el.clientHeight
		#window.addEventListener 'resize', resize
		#resize()

		source = new Bokeh.ColumnDataSource
			data:
				x: []
				y: []
		line = new Bokeh.Line
			x: field: 'x'
			y: field: 'y'
		plot.add_glyph line, source
		plt.show plot, @$el
		console.log "Got service", await R.resolve @service.name
		update = (d) =>
			[hdr, d] = d
			#s = (new Date()).getTime()/1000
			s = hdr.ts
			xrng.start = s - @span
			xrng.end = s
			source.stream
				x: [hdr.ts]
				y: [Math.sin d.time]
			return
		update = @api.lodash.throttle update, @bufferDuration*1000
		await R.resolve @service.on "sample", update
	data: -> {}
</script>

<style scoped>
.trusas-plot {
	width: 100%;
	height: 100%;
	position: relative;
	z-index: 0;
}
</style>

<template lang="pug">
<div class="trusas-plot"></div>
</template>
