path = require 'path'

module.exports =
	entry: './ui/ui.coffee'
	output:
		path: path.resolve('./ui/')
		filename: 'ui.mangled.js'
	module:
		rules: [
			(test: /\.css$/, loader: 'style-loader!css-loader'),
			(test: /\.coffee$/, loader: 'babel-loader!coffee-loader'),
			(test: /\.vue$/, loader: "vue-loader", options:
				loaders:
					coffee: 'babel-loader!coffee-loader'),
		]
	resolve:
		alias:
			vue: 'vue/dist/vue.js'

