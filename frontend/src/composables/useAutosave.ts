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
 * How settled a change is when it is committed. `now` is a pick, whole at the
 * first interaction. `typing` is a text, number or code field, written after
 * {@link TYPING_REST} of rest so it is not sent a character at a time.
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
	 * Report that a control's value has settled. A `now` commit is written once the
	 * current tick's watchers have run, because the resource decides whether it is
	 * dirty in a watcher of its own.
	 */
	commit: (mode?: CommitMode) => void
	/** Send a waiting edit now, on teardown or when leaving the route. */
	flush: () => void
	/** Drop a waiting edit without sending it. */
	cancel: () => void
	reset: () => void
}

export interface AutosaveOptions {
	/**
	 * Is there anything to write? For a document this is frappe-ui's own `isDirty`,
	 * a value comparison against the `originalDoc` it cloned on load, so a field
	 * changed and changed back is clean and never reaches the server.
	 */
	isDirty: () => boolean
	/**
	 * Performs one write. Resolve on success, reject to surface an error, which is
	 * what a frappe-ui resource's `submit()` already does.
	 */
	write: () => Promise<unknown>
}

/**
 * Autosave, as a state machine over a resource's dirty flag. A commit arriving
 * mid-write is held and replayed after, never issued alongside, and a clean
 * resource is never written. Shaped after TanStack's mutations.
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

	// Neither frappe-ui's debounce nor vueuse's useDebounceFn can be cancelled, so
	// the rest period is a plain timer this owns. The immediate path has no timer,
	// so taking its flag back down is what cancels it.
	const disarm = () => {
		clearTimeout(restTimer)
		restTimer = undefined
		tickPending = false
		// A write queued behind one already in flight is a waiting edit too. The
		// in-flight write's `.finally` re-fires `send()` off this flag, so leaving it
		// set writes the very value the cancel exists to withhold.
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

	// A pick commits from the same handler that wrote the value, and the resource
	// is not dirty yet, because frappe-ui maintains isDirty from a deep watcher
	// Vue runs at the end of the tick.
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
	// closing the dialog inside the rest period disposes this scope while an edit
	// is waiting, and removing a focused input fires no focusout to rescue it.
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
