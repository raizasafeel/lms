<template>
	<SettingsLayout
		:title="heading"
		:show-back="showBack"
		:save-state="autosave?.status.value"
		:unsaved="autosave ? undefined : source.isDirty"
		:save-label="autosave ? undefined : __('Save')"
		:saving="saving"
		:can-save="source.isDirty"
		save-testid="settings-fields-save"
		v-model:enabled="enabled"
		@back="emit('back')"
		@save="save"
	>
		<SettingsFields
			v-if="source.doc"
			:sections="sections"
			:data="source.doc"
			@commit="commit"
		/>
	</SettingsLayout>
</template>

<script lang="ts">
import type { FieldMeta, FieldsSection } from '@/types/settingsSchema'

/**
 * Lays the server's `reqd` over each field's static one. Pure, and returns new
 * objects: the schema is a module-level constant shared by every mount, so a
 * runtime flag written into it would leak into the next page.
 */
export function applyFieldMeta(
	sections: FieldsSection[],
	meta: FieldMeta | null
): FieldsSection[] {
	if (!meta) return sections
	return sections.map((section) => ({
		...section,
		fields: section.fields.map((field) => {
			const reqd = meta[field.name]?.reqd
			return reqd === undefined ? field : { ...field, reqd: Boolean(reqd) }
		}),
	}))
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import SettingsFields from '@/components/Layouts/settings/desktop/SettingsFields.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import { useAutosave, type CommitMode } from '@/composables/useAutosave'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import {
	useSettingsSource,
	type SettingsDocumentResource,
} from '@/composables/useSettingsSource'
import type { FieldsPage } from '@/types/settingsSchema'

const props = defineProps<{
	page: FieldsPage
	title?: string
	showBack?: boolean
	/** The record id, for a page whose source takes one from the route. */
	record?: string | null
	/**
	 * A resource the caller already loaded. Settings.vue holds LMS Settings, so a
	 * panel over it is handed the document rather than entering it again.
	 */
	data?: SettingsDocumentResource
}>()

const emit = defineEmits<{ back: []; renamed: [string] }>()

const source = useSettingsSource(props.page.source, {
	record: computed(() => props.record ?? null),
	resource: props.data,
	renameField: props.page.renameField,
})

// A panel whose every section carries a heading needs no title above them,
// because the two sit at the same type token and say the same thing twice. A
// back control is exempt, since there the title is the way out of the page.
const heading = computed(() => {
	if (props.showBack) return props.title
	const sections = props.page.sections
	const headed = sections.length > 0 && sections.every((s) => s.label)
	return headed ? undefined : props.title
})

// frappe-ui's own isDirty and its own save, which skips the round trip when
// there are no changed fields and re-clones originalDoc on success. No toast: a
// failed write leaves the header reading "Not saved", which is quieter.
const autosave =
	props.page.save === 'auto'
		? useAutosave({
				isDirty: () => source.isDirty,
				write: () => source.save(),
		  })
		: null

// Only the manual path registers. Settings.vue mounts every panel at once, and
// an autosave panel is dirty for the whole of each in-flight write, so it would
// prompt on the next tab change over a page that has no Save to offer.
if (!autosave)
	useDirtyGuard(
		() => source.isDirty,
		() => void source.reload()
	)

// SettingsFields reports every settled edit whether or not anyone is listening,
// and a manual page has nothing to do with the report. 'cancel' is not a write
// but the withdrawal of one, disarming a rest period a bounded field armed.
const commit = (mode: CommitMode | 'cancel') =>
	mode === 'cancel' ? autosave?.cancel() : autosave?.commit(mode)

// A rename moves the record out from under the URL, and the panel does not own
// the hash, so it reports the move. Compared against the previous name, because
// a panel opened from a list gets no record prop at all.
watch(
	() => source.name,
	(name, previous) => {
		if (name && previous && name !== previous) emit('renamed', name)
	}
)

const saving = ref(false)

const save = () => {
	saving.value = true
	// Read before the write: a successful insert clears isNew, so asking after
	// it reports every save as an update.
	const created = source.isNew
	source
		.save()
		.then(() =>
			props.page.onSaved?.({
				created,
				name: source.name,
				back: () => emit('back'),
			})
		)
		.catch((error: { messages?: string[]; message?: string }) => {
			toast.error(error?.messages?.[0] || error?.message || __('Save failed'))
			console.error(error)
		})
		.finally(() => (saving.value = false))
}

const meta = ref<FieldMeta | null>(null)

// Fetched once, on mount: `reqd` is a doctype's declaration and does not
// change while the page is open.
onMounted(() => {
	props.page
		.meta?.()
		.then((data) => (meta.value = data))
		.catch((error: unknown) => console.error(error))
})

// `enabledField` hoists one Check out of the body and into the header, beside
// Save. The field is removed from the sections here rather than left out of the
// page's schema, so a page opts in with one key.
const sections = computed(() => {
	const withMeta = applyFieldMeta(props.page.sections, meta.value)
	const hoisted = props.page.enabledField
	if (!hoisted) return withMeta
	return withMeta.map((section) => ({
		...section,
		fields: section.fields.filter((field) => field.name !== hoisted),
	}))
})

// The doctype stores a Check as 0/1 and the header switch speaks booleans.
// Undefined when the page hoists nothing or the document has not landed, which
// is what keeps the switch off every other panel's header.
const enabled = computed<boolean | undefined>({
	get: () => {
		const field = props.page.enabledField
		if (!field || !source.doc) return undefined
		return Boolean(source.doc[field])
	},
	set: (value) => {
		const field = props.page.enabledField
		if (field && source.doc) source.doc[field] = value ? 1 : 0
	},
})
</script>
