import path from 'node:path'
import { fileURLToPath } from 'node:url'
import frappeUIPreset from 'frappe-ui/tailwind'
import { safeAreaPlugin } from './tailwind/safeArea.js'
import { resolveFrameworkUi } from './resolveFrameworkUi.js'

// Where the linked `@framework/ui` package's source sits. App code imports it by
// name, through the package's `exports`; tailwind cannot, because `content` takes
// globs over files rather than module specifiers. Tailwind generates
// only the classes it finds in `content`, so without this every class used *only*
// inside a `@framework/ui` component is missing from this app's CSS. It fails
// invisibly and selectively: the classes that app code also uses somewhere are
// generated anyway, so what goes missing is whatever is unique to the library
// `lucide-group` and `lucide-ungroup` in ConditionBuilder's row menu were rendering
// as empty spans, being the only two icons nothing in LMS uses elsewhere.
// `fileURLToPath(import.meta.url)` rather than `import.meta.dirname`: tailwind
// loads this config through jiti, which shims `import.meta.url` but not the
// newer `dirname`, and an undefined base would resolve the glob off the cwd.
const frameworkUi = resolveFrameworkUi(
	path.dirname(fileURLToPath(import.meta.url))
)

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		`${frameworkUi}/**/*.{vue,js,ts,jsx,tsx}`,
		'./node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		extend: {
			strokeWidth: {
				1.5: '1.5',
			},
			screens: {
				'2xl': '1600px',
				'3xl': '1920px',
			},
		},
	},
	plugins: [safeAreaPlugin],
}
