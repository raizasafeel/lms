import { computed, onScopeDispose, watch, type ComputedRef } from 'vue'
import {
	useRoute,
	useRouter,
	type LocationQuery,
	type Router,
} from 'vue-router'
// @ts-expect-error stores/settings is still plain JS, so it has no declarations
import { useSettings } from '@/stores/settings'
import type {
	SettingsRoutableGroup,
	SettingsRoutableItem,
} from '@/types/settingsSchema'
import { queryEqual } from '@/composables/queryEqual'
import { withFormBackground } from '@/composables/useFormRoute'

// The one query key settings owns. The hash belongs to the page underneath
// (course and batch pages keep their tab there), so settings never touches it.
const KEY = 'settings'
const DEFAULT_SLUG = 'general'

/**
 * '?settings=<slug>' or '?settings=<slug>/<record>', or null when closed.
 * The record is a docname, or 'new' for a create form; a docname may hold '/',
 * so the record is everything after the slug.
 */
export const settingsValue = (query: LocationQuery): string | null => {
	if (!(KEY in query)) return null
	const value = query[KEY]
	return (Array.isArray(value) ? value[0] : value) ?? ''
}

const partsOf = (query: LocationQuery) => settingsValue(query)?.split('/') ?? []

const slugOf = (query: LocationQuery) => partsOf(query)[0] ?? ''

const recordOf = (query: LocationQuery) =>
	partsOf(query).slice(1).join('/') || null

const valueFor = (slug?: string | null, record?: string | null) => {
	const base = slug || DEFAULT_SLUG
	return record ? `${base}/${record}` : base
}

// The page's query with the settings key set to `value`, or dropped for null.
const queryWith = (query: LocationQuery, value: string | null) => {
	const { [KEY]: _dropped, ...rest } = query
	return value === null ? rest : { ...rest, [KEY]: value }
}

const isOpenAt = (router: Router) =>
	settingsValue(router.currentRoute.value.query) !== null

// Depth of settings entries we pushed, so close() pops exactly those. replace() merges
// history.state, so a stale depth can ride onto a non-settings entry, trust it only there.
const depthOf = (router: Router) => {
	if (!isOpenAt(router)) return 0
	return Number(
		(router.options.history.state as Record<string, unknown> | null)
			?.settingsDepth ?? 0
	)
}

// Navigate into a settings tab, the one way in, used for both tab clicks and
// openSettings(). Keeps the page's own query and hash, so the page underneath
// stays on the tab, section and filters it was showing.
export function pushSettingsHash(
	router: Router,
	slug?: string | null,
	record?: string | null
) {
	const route = router.currentRoute.value
	const value = valueFor(slug, record)
	if (settingsValue(route.query) === value) return
	// No slug means "just open settings". If already open, pushing would only
	// add an entry rendering the identical panel.
	if (!slug && isOpenAt(router)) return
	// Settings never changes the path under it, so the entry it pushes must keep
	// painting whatever the entry it leaves was painting. Skipping this put a
	// modal behind a modal: settings opened on top of a form route lost the
	// stamp, so the next form route opened from settings recorded the settings
	// entry as its own background, a Dialog, which paints an empty page.
	router.push({
		query: queryWith(route.query, value),
		hash: route.hash,
		state: withFormBackground(router, {
			settingsDepth: depthOf(router) + 1,
		}),
	})
}

// Keeps the settings dialog in sync with the `settings` query key. The URL is the
// source of truth; the store (isSettingsOpen, activeTab) is only a read-only mirror.
export function useSettingsHash(tabs: ComputedRef<SettingsRoutableGroup[]>) {
	const route = useRoute()
	const router = useRouter()
	const settingsStore = useSettings()

	// Set while a close unwinds our entries; carries the page query we closed
	// with, since the entry popped back to predates any filter changed while open.
	let closing: { query: LocationQuery } | null = null

	// go() is async; clear on afterEach (fires on aborts too) so an aborted pop
	// can't leave it stuck.
	let dropping = false
	// Same for close()'s own pop. `closing` can't serve as this flag: it is
	// nulled by the URL watcher, and a refused navigation never changes the
	// URL, so a refused dismiss would leave close() dead for the session.
	let popping = false
	onScopeDispose(
		router.afterEach((_to, _from, failure) => {
			dropping = false
			popping = false
			// Only on a refusal. A completed pop still needs `closing` for the URL
			// watcher below; a refused one never reaches it, and leaving it set
			// force-closes the dialog on the next settings change.
			if (failure) closing = null
		})
	)

	const items = computed(() => tabs.value.flatMap((tab) => tab.items))
	const defaultItem = computed<SettingsRoutableItem | null>(
		() => items.value[0] ?? null
	)

	const value = computed(() => settingsValue(route.query))
	const isOpen = computed(() => value.value !== null)

	const itemForSlug = (slug: string) =>
		items.value.find((item) => item.slug === slug) ?? null

	const activeTab = computed<SettingsRoutableItem | null>(() => {
		if (!isOpen.value) return null
		return itemForSlug(slugOf(route.query)) ?? defaultItem.value
	})

	// Swaps the settings value of the current entry, leaving the page's keys and hash.
	const replaceValue = (next: string | null, state = {}) =>
		router.replace({
			query: queryWith(route.query, next),
			hash: route.hash,
			state: withFormBackground(router, state),
		})

	const selectTab = (item: SettingsRoutableItem | null) => {
		if (!item || item === activeTab.value) return
		pushSettingsHash(router, item.slug)
	}

	// A record only exists on a tab that takes records; elsewhere the second
	// segment is nonsense and the normalisation watcher strips it.
	const activeRecord = computed<string | null>(() => {
		if (!isOpen.value || !activeTab.value?.records) return null
		return recordOf(route.query)
	})

	// Open a record in the active tab, or return to its list with null (replace = bad-id
	// fallback). INVARIANT: go(-1) assumes a record sits on its tab's list: list→record only.
	const selectRecord = (
		record: string | null,
		options: { replace?: boolean } = {}
	) => {
		const slug = activeTab.value?.slug
		if (!slug || !activeTab.value?.records) return
		const next = valueFor(slug, record)
		if (value.value === next) return
		if (!options.replace) return pushSettingsHash(router, slug, record)
		// Pop reuses the list entry directly behind this one; depthOf() === 0
		// means we deep-linked in, so fall back to replace instead (same as close()).
		if (depthOf(router) === 0) return replaceValue(next)
		if (dropping) return
		dropping = true
		router.go(-1)
	}

	// Renames the CURRENT record entry to a new docname (a rename keeps the
	// record open but changes its name), via replace() so history depth is
	// unchanged and Back still lands on the list. A real browser's replace()
	// merges history.state on its own; memory history drops it, so the current
	// depth is passed explicitly to keep both behaving the same.
	const replaceRecord = (record: string) => {
		const slug = activeTab.value?.slug
		if (!slug || !activeTab.value?.records) return
		const next = valueFor(slug, record)
		if (value.value === next) return
		replaceValue(next, { settingsDepth: depthOf(router) })
	}

	// router.go() is async, so the dialog is still visibly open when a second
	// dismiss arrives (Escape twice, or a backdrop click right after) while
	// depthOf() reads the same value. Popping again would overshoot by a page.
	const close = () => {
		if (!isOpen.value || popping) return
		const ours = depthOf(router)
		if (ours === 0) return replaceValue(null)
		popping = true
		closing = { query: queryWith(route.query, null) }
		router.go(-ours)
	}

	watch(value, (current) => {
		if (!closing) return
		const { query } = closing
		closing = null
		// Back on the page; the entry popped to may predate a filter changed while
		// settings was open, restore it. Or our entries are gone but settings is
		// still open (a deep link then a tab switch): drop it rather than reopen.
		if (current !== null || !queryEqual(query, route.query)) {
			router.replace({
				query,
				hash: route.hash,
				state: withFormBackground(router),
			})
		}
	})

	// An unknown or permission-hidden slug lands on the default tab (no dead entry).
	// Watches `items` too: tabs load async, so a deep link's slug can't be judged yet.
	watch(
		[value, items],
		() => {
			if (!isOpen.value || closing || !defaultItem.value) return
			// An empty slug ('?settings=') is normalised too, or the URL would
			// disagree with the default-tab view and nothing else would repair it.
			const item = itemForSlug(slugOf(route.query))
			if (!item) return replaceValue(valueFor(defaultItem.value.slug))
			// Tab is real but takes no records, drop the phantom id rather than
			// render the list with it still in the URL.
			if (!item.records && recordOf(route.query)) {
				replaceValue(valueFor(item.slug))
			}
		},
		{ immediate: true }
	)

	watch(
		[isOpen, activeTab],
		([open, tab]) => {
			settingsStore.isSettingsOpen = open
			settingsStore.activeTab = tab?.label ?? null
		},
		{ immediate: true }
	)

	return {
		items,
		isOpen,
		activeTab,
		activeRecord,
		selectTab,
		selectRecord,
		replaceRecord,
		close,
	}
}
