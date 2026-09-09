import { onScopeDispose } from 'vue'
import {
	useRouter,
	type HistoryState,
	type RouteLocationRaw,
	type Router,
} from 'vue-router'

/**
 * Marker written into history.state when we open a form route ourselves.
 * Its absence means the user arrived by deep link, reload, or a hand-typed URL,
 * so there is no entry of ours to pop.
 */
const FORM_ENTRY = 'lmsFormEntry'

/**
 * The location openFormRoute is leaving. A form route renders a Dialog, and a
 * router.push() unmounts the page it was opened from, so the dialog would float
 * over a blank app. App.vue keeps the stamped location rendered underneath.
 */
const FORM_BACKGROUND = 'lmsFormBackground'

// Reads the state of the current history entry through the router rather than
// window.history. createMemoryHistory never touches window.history, and
// vue-router mirrors the web history's state here too.
const historyState = (router: Router): Record<string, unknown> =>
	(router.options.history.state as Record<string, unknown> | null) ?? {}

/**
 * The fullPath App.vue should render behind the current form route, or null
 * when nothing stamped one (a deep link, a reload, a hand-typed URL).
 */
export function formBackgroundPath(router: Router): string | null {
	const stored = historyState(router)[FORM_BACKGROUND]
	return typeof stored === 'string' && stored ? stored : null
}

/**
 * Merge the current entry's background stamp into the state of an entry that
 * overlays the same page. Without this a settings entry pushed from a form route
 * carries no stamp, and the next openFormRoute records a modal as its background.
 */
export function withFormBackground(
	router: Router,
	state: HistoryState = {}
): HistoryState {
	return { ...state, [FORM_BACKGROUND]: formBackgroundPath(router) }
}

// Normalizes `to` and stamps FORM_ENTRY, preserving whatever state the caller
// already set rather than clobbering it.

// FORM_BACKGROUND is always written, null included. createWebHistory's
// replace() merges over the entry it replaces, so an omitted key would let the
// form's background leak onto a destination that is not a modal at all.
const withFormEntry = (
	to: RouteLocationRaw,
	value: boolean,
	background: string | null = null
): Exclude<RouteLocationRaw, string> & { state: Record<string, unknown> } => {
	const location = typeof to === 'string' ? { path: to } : to
	const priorState =
		'state' in location && location.state
			? (location.state as Record<string, unknown>)
			: {}
	return {
		...location,
		state: {
			...priorState,
			[FORM_ENTRY]: value,
			[FORM_BACKGROUND]: background,
		},
	}
}

export function openFormRoute(
	router: Router,
	to: RouteLocationRaw
): Promise<unknown> {
	const current = router.currentRoute.value
	// Carry an existing background forward instead of stacking a second one, so
	// opening form B from form A still shows the page A was opened over. `matched`
	// is empty only at START_LOCATION.
	const background = current.matched.length
		? formBackgroundPath(router) ?? current.fullPath
		: null
	return router.push(withFormEntry(to, true, background))
}

export function useFormRoute(parent: RouteLocationRaw): {
	close: () => void
	saveAndReplace: (to: RouteLocationRaw) => void
	openedByUs: boolean
} {
	const router = useRouter()
	// Read once, at setup. By close time this is still the same history entry.
	// Going through the router keeps it readable under createMemoryHistory, which
	// never touches window.history.
	const openedByUs = historyState(router)[FORM_ENTRY] === true

	// router.back() is async and the component stays mounted until the navigation
	// flushes, so a second close() inside that window would pop a second entry.
	// The flag is cleared in afterEach, which fires on aborted navigations too.
	let closing = false
	onScopeDispose(
		router.afterEach(() => {
			closing = false
		})
	)

	const close = (): void => {
		if (closing) return
		closing = true
		if (openedByUs) router.back()
		else router.replace(parent)
	}

	// saveAndReplace needs no such guard. replace() is idempotent under a repeated
	// identical call, and its only caller is a resource's onSuccess behind a Save
	// button whose loading state already disables a second click.

	// Saving navigates onward by replacing, so the form entry is consumed and Back
	// reaches the list rather than a stale, empty form.
	const saveAndReplace = (to: RouteLocationRaw): void => {
		router.replace(withFormEntry(to, false))
	}

	return { close, saveAndReplace, openedByUs }
}
