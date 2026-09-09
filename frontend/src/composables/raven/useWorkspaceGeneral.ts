// The workspace General form as a value, so the page header can own Save while
// the tab owns the fields, both reading off one source the way CRM's
// SettingsPage does.
import { createResource, toast } from 'frappe-ui'
import { computed, reactive, watch, type ComputedRef } from 'vue'
import type { WorkspaceDetail, WorkspaceVisibility } from '@/types'

export interface WorkspaceGeneralForm {
	draft: { label: string; type: WorkspaceVisibility }
	/** The page stands for a workspace that does not exist yet, so Save creates it. */
	isNew: ComputedRef<boolean>
	/** Differs from what is stored, so there is something for Save to send. */
	dirty: ComputedRef<boolean>
	/** Enough is filled in for Save to commit, which is what disables the button. */
	canSubmit: ComputedRef<boolean>
	saving: ComputedRef<boolean>
	/** Nothing here is editable while the Raven workspace is gone. */
	locked: ComputedRef<boolean>
	save: () => Promise<void>
	reset: () => void
}

interface WorkspaceGeneralOptions {
	/** The mapping autonames from its label, so a saved rename moves the docname
	 *  and the owner has to adopt the new one. */
	onRenamed?: (newName: string) => void
	/** True while the page has no record behind it. New is a page, not a write:
	 *  it used to POST create_workspace before anything had been filled in. */
	isNew?: () => boolean
	/** The docname create_workspace answered with, for the owner to adopt. */
	onCreated?: (newName: string) => void
}

export function useWorkspaceGeneral(
	detail: ComputedRef<WorkspaceDetail | null>,
	onChanged: () => void,
	options: WorkspaceGeneralOptions = {}
): WorkspaceGeneralForm {
	const isNew = computed<boolean>(() => !!options.isNew?.())

	const draft = reactive<{ label: string; type: WorkspaceVisibility }>({
		label: '',
		type: 'Private',
	})

	/** Which record the draft currently holds. Null until the first load lands. */
	let draftFor: string | null = null

	/** What the draft was last seeded with, so an edit can be told from a record
	 *  that moved underneath one. `dirty` reads the record as it stands now, so
	 *  once a reload has landed an untouched draft measures as changed. */
	const seeded = reactive<{ label: string; type: WorkspaceVisibility }>({
		label: '',
		type: 'Private',
	})

	function reset(): void {
		if (!detail.value) return
		draft.label = detail.value.workspace_label
		draft.type = detail.value.workspace_type
		seeded.label = draft.label
		seeded.type = draft.type
		draftFor = detail.value.name
	}

	const edited = computed<boolean>(
		() => draft.label !== seeded.label || draft.type !== seeded.type
	)

	const trimmedLabel = computed<string>(() => draft.label.trim())

	const dirty = computed<boolean>(() => {
		// Nothing is stored yet, so anything filled in is unsaved work, which is
		// what the leave guard asks about.
		if (isNew.value) return !!trimmedLabel.value || draft.type !== 'Private'
		if (!detail.value) return false
		return (
			(!!trimmedLabel.value &&
				trimmedLabel.value !== detail.value.workspace_label) ||
			draft.type !== detail.value.workspace_type
		)
	})

	// A new workspace needs a name and nothing else; a stored one also needs
	// something to send, so an empty name never commits.
	const canSubmit = computed<boolean>(() =>
		isNew.value ? !!trimmedLabel.value : dirty.value
	)

	// A reload can come from something that is not a save, so a record already on
	// screen keeps its unsaved draft. Keyed on the docname, because a load for a
	// different record is a navigation and always wins.
	watch(
		detail,
		(current) => {
			if (current && draftFor === current.name && edited.value && dirty.value)
				return
			reset()
		},
		{ immediate: true, deep: true }
	)

	const locked = computed<boolean>(() => !!detail.value?.stale)

	function onError(fallback: string) {
		return (err: { messages?: string[] }): void => {
			toast.error(err?.messages?.[0] ?? fallback)
			onChanged()
		}
	}

	const setLabel = createResource({
		url: 'raven_integration.api.set_workspace_label',
		onError: onError(__('Could not rename the workspace')),
	})

	const setWorkspaceType = createResource({
		url: 'raven_integration.api.set_workspace_type',
		onError: onError(__('Could not change the visibility')),
	})

	// Its own error handler rather than the shared one, because there is no record
	// to reload when the create is the thing that failed.
	const createWorkspace = createResource({
		url: 'raven_integration.api.create_workspace',
		onError(err: { messages?: string[] }) {
			toast.error(err?.messages?.[0] ?? __('Could not create the workspace'))
		},
	})

	const saving = computed<boolean>(
		() =>
			setLabel.loading || setWorkspaceType.loading || createWorkspace.loading
	)

	// One call, because there is no record yet for the two field endpoints to
	// address. The owner then adopts the docname and this becomes the ordinary
	// detail page for what was just created.
	async function create(): Promise<void> {
		if (!trimmedLabel.value) return
		const created = (await createWorkspace.submit({
			label: trimmedLabel.value,
			type: draft.type,
		})) as string | null | undefined
		if (!created) return
		toast.success(__('Workspace created'))
		options.onCreated?.(created)
	}

	/** False when the caller must stop, because submit() does not reject and the
	 *  rename would otherwise run against a visibility write that failed. */
	async function writeVisibility(current: WorkspaceDetail): Promise<boolean> {
		if (draft.type === current.workspace_type) return true
		await setWorkspaceType.submit({ name: current.name, type: draft.type })
		return !setWorkspaceType.error
	}

	/** False when the caller must stop: the write failed, or the rename was handed
	 *  up and adopting the new docname reloads the page by itself. */
	async function writeLabel(current: WorkspaceDetail): Promise<boolean> {
		if (!trimmedLabel.value || trimmedLabel.value === current.workspace_label)
			return true
		const renamed = (await setLabel.submit({
			name: current.name,
			label: trimmedLabel.value,
		})) as { name?: string } | undefined
		if (setLabel.error) return false
		if (renamed?.name && renamed.name !== current.name && options.onRenamed) {
			options.onRenamed(renamed.name)
			return false
		}
		return true
	}

	// Two endpoints, one button, so only the changed fields are sent. Rename last:
	// the mapping autonames from its label, so a rename moves the docname and a
	// visibility write landing after it would address a doc that is gone.
	async function save(): Promise<void> {
		if (isNew.value) return create()
		const current = detail.value
		if (!current || !dirty.value) return
		if (!(await writeVisibility(current))) return
		if (!(await writeLabel(current))) return
		onChanged()
	}

	return { draft, isNew, dirty, canSubmit, saving, locked, save, reset }
}
