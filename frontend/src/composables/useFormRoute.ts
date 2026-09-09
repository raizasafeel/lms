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

// Reads the state of the CURRENT history entry through the router rather than
// window.history: createMemoryHistory (used in tests) never touches
// window.history, and vue-router mirrors the web history's state here too.
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
 * Merge the CURRENT entry's background stamp into the state of an entry that is
 * an overlay over the same page — settings, which is addressed by the hash and
 * so never changes the path under it.
 *
 * Without this a settings entry pushed from on top of a form route carries no
 * stamp at all, and two things break at once: App.vue paints the form route (a
 * Dialog, so nothing) behind settings, and the next openFormRoute finds no
 * stamp to carry forward and records the SETTINGS entry — a modal — as its own
 * background. Written unconditionally, null included, for the reason below:
 * createWebHistory's replace() merges, so an omitted key leaks the old value.
 */
export function withFormBackground(
	router: Router,
	state: HistoryState = {}
): HistoryState {
	return { ...state, [FORM_BACKGROUND]: formBackgroundPath(router) }
}

// Normalizes `to` and stamps FORM_ENTRY, preserving whatever state the caller
// already set rather than clobbering it — both openFormRoute (true) and
// saveAndReplace (false) go through this.
//
// FORM_BACKGROUND is always written, null included. createWebHistory's
// replace() MERGES the new state over the entry it replaces, so leaving the key
// out of saveAndReplace's state would let the form's background leak onto the
// destination and paint a stale page under a route that is not a modal at all.
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
	// Carry an existing background forward instead of stacking a second one:
	// opening form B from form A must still show the page A was opened over,
	// not form A itself. `matched` is empty only at START_LOCATION, where there
	// is no page behind us to keep.
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
	// Going through the router rather than window.history keeps it readable
	// under createMemoryHistory, which never touches window.history.
	const openedByUs = historyState(router)[FORM_ENTRY] === true

	// router.back()/replace() are async, and the component stays mounted until
	// the navigation actually flushes — so a second close() call inside that
	// window (double-tapping the mobile back chevron, or two Escape presses:
	// the desktop Dialog's :open="true" is a literal, not the controlled
	// isOpen the real Dialog tracks internally, so it stays visibly open
	// after the first Escape until the route pop renders) would call
	// router.back() again and pop a second entry. Guard with a flag cleared in
	// afterEach — mirrors feat/settings-url-routing's useSettingsHash.ts
	// `dropping`, cleared the same way because afterEach fires on aborted
	// navigations too, so a cancelled pop can't leave `closing` stuck true.
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

	// saveAndReplace does NOT need the same guard. Unlike back(), replace() is
	// idempotent under a repeated identical call — two replaces to the same
	// destination land you there once, not twice as far, so there is no
	// compounding effect to guard against. Its only call site today is a
	// resource's onSuccess (fires once per submit) behind a Save button whose
	// :loading state already disables a second click — there is no
	// back-arrow/Escape-shaped path that can fire it twice the way close() has.
	//
	// Saving navigates onward by REPLACING, so the form entry is consumed and
	// Back reaches the list rather than a stale, empty form.
	const saveAndReplace = (to: RouteLocationRaw): void => {
		router.replace(withFormEntry(to, false))
	}

	return { close, saveAndReplace, openedByUs }
}
