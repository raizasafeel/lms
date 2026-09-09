import {
	computed,
	nextTick,
	onScopeDispose,
	ref,
	type ComputedRef,
	type Ref,
} from 'vue'

/** How long a typing field rests before its edit is written. */
export const TYPING_REST = 2000
/** How long "Saved" holds before the marker goes quiet. */
export const SAVED_FOR = 2000

export type AutosaveStatus =
	| 'idle'
	| 'dirty'
	| 'pending'
	| 'saving'
	| 'saved'
	| 'error'

/**
 * How settled a change is when it is committed.
 *
 * `now` — a checkbox, radio, dropdown, switch, Link or file: a pick is whole
 * at the first interaction and there is nothing to wait for.
 *
 * `typing` — a text, number or code field: written after {@link TYPING_REST}
 * of rest, so a half-typed value is not sent a character at a time.
 */
export type CommitMode = 'now' | 'typing'

export interface Autosave {
	status: ComputedRef<AutosaveStatus>
	isDirty: ComputedRef<boolean>
	/** An edit is waiting out its rest period; nothing has been sent yet. */
	isPending: ComputedRef<boolean>
	isSaving: ComputedRef<boolean>
	isError: ComputedRef<boolean>
	/** Whatever the last failed write threw. Cleared by the next success. */
	error: Ref<unknown>
	lastSavedAt: Ref<Date | null>
	/**
	 * Report that a control's value has settled. A `now` commit is written once
	 * the current tick's watchers have run rather than from inside the handler,
	 * because the resource decides whether it is dirty in a watcher of its own.
	 */
	commit: (mode?: CommitMode) => void
	/** Send a waiting edit now — on teardown, or leaving the route. */
	flush: () => void
	/** Drop a waiting edit without sending it. */
	cancel: () => void
	reset: () => void
}

export interface AutosaveOptions {
	/**
	 * Is there anything to write?
	 *
	 * For a document this is frappe-ui's own `isDirty`, which compares the doc
	 * against the `originalDoc` it cloned on load — a value comparison, so a
	 * field changed and changed back is clean and never reaches the server.
	 * The resource maintains it: a successful save re-clones, and a reload
	 * replaces both sides at once.
	 */
	isDirty: () => boolean
	/**
	 * Performs one write. Resolve on success, reject to surface an error —
	 * which is what a frappe-ui resource's `submit()` already does.
	 */
	write: () => Promise<unknown>
}

/**
 * Autosave, as a state machine over a resource's dirty flag.
 *
 * Shaped after TanStack's mutations — `status` plus the booleans derived from
 * it — so a page renders whatever it wants from the same source rather than
 * being handed a string to display.
 *
 * Two guarantees:
 *
 * A commit arriving mid-write is held and replayed after, never issued
 * alongside. `save.submit()` sends the changed fields as they are at call
 * time, so two in flight at once race to write the same row.
 *
 * A clean resource is never written. Because dirtiness is a comparison and
 * not a touched flag, typing a character and deleting it again queues nothing
 * — which is what keeps a rest-period autosave from writing a value the user
 * has already taken back, and from tripping a doctype that validates on save.
 */
export function useAutosave(options: AutosaveOptions): Autosave {
	const error = ref<unknown>(null)
	const lastSavedAt = ref<Date | null>(null)

	const saving = ref(false)
	const pending = ref(false)
	const justSaved = ref(false)
	const isDirty = computed(() => Boolean(options.isDirty()))
	let queued = false
	let restTimer: ReturnType<typeof setTimeout> | undefined
	let savedTimer: ReturnType<typeof setTimeout> | undefined
	let tickPending = false

	// Neither frappe-ui's debounce nor vueuse's useDebounceFn can be cancelled,
	// so the rest period is a plain timer this owns and can disarm. The
	// immediate path has no timer to clear, so taking its flag back down is
	// what cancels it.
	const disarm = () => {
		clearTimeout(restTimer)
		restTimer = undefined
		tickPending = false
		// A write queued behind one already in flight is a waiting edit too: the
		// in-flight write's `.finally` re-fires `send()` off this flag, so leaving
		// it set writes the very value the cancel exists to withhold.
		queued = false
		pending.value = false
	}

	const send = () => {
		if (saving.value) {
			queued = true
			return
		}
		if (!isDirty.value) return

		saving.value = true
		justSaved.value = false

		options
			.write()
			.then(() => {
				error.value = null
				lastSavedAt.value = new Date()
				justSaved.value = true
				clearTimeout(savedTimer)
				savedTimer = setTimeout(() => (justSaved.value = false), SAVED_FOR)
			})
			.catch((reason: unknown) => {
				// The resource stays dirty, so the marker keeps reading "Not saved"
				// and the edit is still there to retry. Nothing is rolled back here.
				error.value = reason ?? new Error('Autosave failed')
			})
			.finally(() => {
				saving.value = false
				if (queued) {
					queued = false
					send()
				}
			})
	}

	// A pick commits from the same handler that wrote the value, and the
	// resource is not dirty yet at that moment: frappe-ui maintains its own
	// isDirty from a deep watcher on the document (documentResource.js), and
	// Vue runs that watcher at the end of the tick. Sending straight from the
	// handler therefore compares a document against a snapshot it has not
	// re-read, finds it clean, and writes nothing — leaving the marker on
	// "Not saved" with no write ever issued and nothing to clear it.
	//
	// Waiting out the tick is also what coalesces the pair of handlers a
	// control fires on one interaction into a single write.
	const sendAfterTick = () => {
		if (tickPending) return
		tickPending = true
		void nextTick().then(() => {
			if (!tickPending) return
			tickPending = false
			send()
		})
	}

	const commit = (mode: CommitMode = 'now') => {
		if (mode === 'now') {
			disarm()
			sendAfterTick()
			return
		}
		clearTimeout(restTimer)
		pending.value = true
		restTimer = setTimeout(() => {
			pending.value = false
			restTimer = undefined
			send()
		}, TYPING_REST)
	}

	const flush = () => {
		if (!restTimer) return
		disarm()
		send()
	}

	const reset = () => {
		disarm()
		clearTimeout(savedTimer)
		queued = false
		justSaved.value = false
		error.value = null
	}

	const status = computed<AutosaveStatus>(() => {
		if (saving.value) return 'saving'
		if (error.value) return 'error'
		if (pending.value) return 'pending'
		if (isDirty.value) return 'dirty'
		if (justSaved.value) return 'saved'
		return 'idle'
	})

	// Send, don't drop. frappe-ui's SettingsDialog defaults to unmountOnHide, so
	// closing the dialog or switching tabs inside the rest period disposes this
	// scope while an edit is still waiting — and removing the focused input from
	// the DOM fires no focusout, so no `now` commit rescues it either.
	onScopeDispose(() => {
		flush()
		clearTimeout(restTimer)
		clearTimeout(savedTimer)
	})

	return {
		status,
		isDirty,
		isPending: computed(() => pending.value),
		isSaving: computed(() => saving.value),
		isError: computed(() => Boolean(error.value)),
		error,
		lastSavedAt,
		commit,
		flush,
		cancel: disarm,
		reset,
	}
}
