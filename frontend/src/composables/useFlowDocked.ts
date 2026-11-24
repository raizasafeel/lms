import { readonly, ref } from 'vue'
import type { Ref } from 'vue'

const docked = ref<boolean>(false)
let watching = false

/** Flow docks its panel by giving <html> a right margin; the window keeps its width. */
function readDocked(): void {
	const margin = parseFloat(
		getComputedStyle(document.documentElement).marginRight
	)
	docked.value = margin > 0
}

function startWatching(): void {
	if (watching) return
	watching = true
	readDocked()
	new MutationObserver(readDocked).observe(document.documentElement, {
		attributes: true,
		attributeFilter: ['style', 'class'],
	})
	window.addEventListener('resize', readDocked)
}

/** Whether Flow's panel is docked beside the app, shared by every caller. */
export function useFlowDocked(): Readonly<Ref<boolean>> {
	startWatching()
	return readonly(docked)
}
