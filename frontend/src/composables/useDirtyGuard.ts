import { onScopeDispose, ref } from 'vue'
import type { Router } from 'vue-router'

// Confirm before a navigation discards an unsaved settings form.
// A set, not one slot: Settings.vue renders every panel in a `v-for`, so
// several are registered at once, and one slot would leave earlier panels unguarded.
type DirtyCheck = () => boolean

interface DirtyEntry {
	isDirty: DirtyCheck
	discard?: () => void
}

const registered = new Set<DirtyEntry>()

// Suppressed for the rest of the navigation the user answered, so a redirect
// chained off it does not ask a second time for one decision. Cleared by the
// router's afterEach, which fires once the whole chain settles.
const suppressed = new Set<DirtyEntry>()

// Register a form from its setup; it deregisters itself when that component
// goes away. `discard` is what the form does on Discard: without it the
// guard only stops asking, and the next Save writes the edits anyway.
export function useDirtyGuard(isDirty: DirtyCheck, discard?: () => void) {
	const entry: DirtyEntry = { isDirty, discard }
	registered.add(entry)
	onScopeDispose(() => {
		registered.delete(entry)
		suppressed.delete(entry)
	})
}

// Install the guard on the router (Settings.vue does this once). Must abort
// (return false), never navigate: navigating from a guard cancels the pop, and vue-router won't restore the URL.
export function installDirtyGuard(
	router: Router,
	confirm: () => Promise<boolean>
) {
	// A stub router in a test may not have afterEach; the suppression below is
	// then simply never released, which is the old drop-the-checker behaviour.
	const stopAfter = router.afterEach?.(() => suppressed.clear()) ?? (() => {})
	const stopBefore = router.beforeEach(async (to, from) => {
		const dirty = [...registered].filter(
			(entry) => !suppressed.has(entry) && entry.isDirty()
		)
		if (!dirty.length) return true
		// Same view: a query change (the page's filters) is not leaving the form.
		// Another path under the same hash is a different page, so it still asks.
		if (to.path === from.path && to.hash === from.hash) return true

		if (!(await confirm())) return false

		// Throw the edits away, then stop asking for the rest of this navigation.
		// Suppressed rather than deleted, so a form still mounted is guarded
		// again the next time it goes dirty.
		for (const entry of dirty) {
			entry.discard?.()
			suppressed.add(entry)
		}
		return true
	})
	return () => {
		stopBefore()
		stopAfter()
	}
}

// The confirm dialog's state, kept here (not a component) so the guard can
// await an answer from inside a navigation. Alias `show` in <script setup>,
// since Vue only unwraps top-level refs.
export const discardPrompt = { show: ref(false) }

let resolver: ((ok: boolean) => void) | null = null

export function confirmDiscard(): Promise<boolean> {
	// A second prompt can open mid-flight (browser-Back twice); settle the
	// one being superseded as FALSE rather than leak its promise.
	answerDiscard(false)
	discardPrompt.show.value = true
	return new Promise<boolean>((resolve) => {
		resolver = resolve
	})
}

// Safe against watch(show)'s dismissal-as-cancel: nulls `resolver` synchronously,
// so its re-entrant call finds nothing to resolve.
export function answerDiscard(ok: boolean) {
	discardPrompt.show.value = false
	const resolve = resolver
	resolver = null
	resolve?.(ok)
}
