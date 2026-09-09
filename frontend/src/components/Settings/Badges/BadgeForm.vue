<template>
	<SettingsLayout
		:title="formTitle"
		show-back
		:unsaved="isDirty"
		v-model:enabled="enabled"
		:save-label="__('Save')"
		:saving="saving"
		:can-save="isDirty"
		save-testid="badge-save"
		@back="emit('back')"
		@save="save"
	>
		<div v-if="!badge" class="flex flex-1 items-center justify-center py-20">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>

		<div v-else data-testid="badge-fields" class="space-y-4">
			<ImageUploadField
				testid="badge-image"
				icon="lucide-award"
				:label="__('Badge Image')"
				:description="__('Shown wherever this badge is awarded.')"
				:required="true"
				:image_url="badge.image || ''"
				:is_private="false"
				@upload="setImage"
				@remove="setImage('')"
			/>

			<div class="h-px border-t border-outline-elevation-2" />

			<div class="grid grid-cols-2 gap-4">
				<FormControl
					data-testid="badge-title"
					v-model="badge.title"
					:label="__('Title')"
					type="text"
					:placeholder="__('e.g. Course Champion')"
					required
					autocomplete="off"
				/>
				<FormControl
					data-testid="badge-description"
					v-model="badge.description"
					:label="__('Description')"
					type="textarea"
					:rows="3"
					:placeholder="__('What is this badge awarded for?')"
					required
					class="col-span-2"
				/>
			</div>

			<div class="h-px border-t border-outline-elevation-2" />

			<div class="text-p-lg-semibold text-ink-gray-8">
				{{ __('Assignment rules') }}
			</div>

			<BooleanSwitch
				size="sm"
				v-model="badge.grant_only_once"
				:label="__('Grant Only Once')"
				:description="__('Each user can only receive this badge one time.')"
			/>

			<div class="grid grid-cols-2 gap-4">
				<Select
					v-model="badge.reference_doctype"
					:label="__('Assign For')"
					:options="referenceDoctypeOptions()"
					:required="true"
					class="w-full"
				/>
				<Select
					v-model="badge.user_field"
					:label="__('Assign To')"
					:options="userFieldOptions()"
					:required="true"
					class="w-full"
				/>
				<Select
					v-model="badge.event"
					:label="__('Event')"
					:options="eventOptions()"
					:required="true"
					class="w-full"
				/>
			</div>

			<CodeEditor
				v-model="badge.condition"
				:label="__('Condition')"
				:description="conditionHint()"
				type="JavaScript"
				:required="true"
				:showBorder="true"
				height="250px"
			/>

			<ErrorMessage v-if="error" class="ms-1" :message="error" />
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import {
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	call,
	toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import ImageUploadField from '@/components/Controls/ImageUploadField.vue'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import Select from '@/components/Controls/Select.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import {
	BADGE_DOCTYPE,
	BADGE_RENAME_FIELD,
	conditionHint,
	eventOptions,
	newBadge,
	referenceDoctypeOptions,
	userFieldOptions,
} from '@/components/Settings/Badges/badges'
import { useSettingsRecord } from '@/composables/useSettingsRecord'
import { runSave, useSaveState } from '@/composables/useSettingsSave'
import { cleanError } from '@/utils'
import type { SettingsListRow } from '@/types'

/**
 * One badge, behind both New and a row. Hand-rolled rather than routed through
 * SettingsFields, after CRM's TwilioSettings.vue: a `space-y-4` body, text
 * fields in a two-column grid, and a rule between sections.
 */

const props = defineProps<{
	name?: string | null
	row?: SettingsListRow | null
}>()

const emit = defineEmits<{ back: [] }>()

const state = useSaveState()
const saving = state.saving
const error = state.error

const record = computed(() => props.name ?? null)

// A draft is dirty against the defaults it opened on, not against emptiness.
// The source's own answer for a new record is "holds anything at all", and a
// badge opens holding an event and a user field already.
const pristine = ref('')

const snapshot = (doc: SettingsListRow | null) => JSON.stringify(doc ?? null)

// LMS Badge autonames from its title, so the source renames the record when the
// title field changes rather than trying to write a name that is derived.
const {
	source,
	doc: badge,
	isNew,
	isDirty,
	enabled,
} = useSettingsRecord({
	doctype: BADGE_DOCTYPE,
	record,
	renameField: BADGE_RENAME_FIELD,
	dirty: (s) => (s.isNew ? snapshot(s.doc) !== pristine.value : s.isDirty),
})

const formTitle = computed(() => {
	if (isNew.value) return __('New Badge')
	return badge.value?.title || props.row?.title || __('Badge')
})

watch(
	() => source.doc,
	(doc) => {
		if (!source.isNew || !doc || Object.keys(doc).length) return
		Object.assign(doc, newBadge())
		pristine.value = snapshot(doc)
	},
	{ immediate: true }
)

const setImage = (url: string) => {
	if (badge.value) badge.value.image = url
}

// LMS Badge marks seven fields reqd, so the server would answer one gap per
// round trip. Naming the first here is additive: everything past it still has
// to survive the server saying no.
const validate = (): string => {
	const doc = badge.value
	if (!doc) return __('This badge has not loaded yet')
	if (!doc.title) return __('Title is required')
	if (!doc.reference_doctype) return __('Assign For is required')
	if (!doc.description) return __('Description is required')
	if (!doc.image) return __('Badge Image is required')
	if (!doc.event) return __('Event is required')
	if (!doc.user_field) return __('Assign To is required')
	if (!doc.condition) return __('Condition is required')
	return ''
}

// cleanError() calls String.replace on what it is handed, so an error carrying
// only `message`, such as a network failure, throws inside the handler unless
// the lookup settles on a string first.
const failureMessage = (err: any, fallback: string): string => {
	const message = err?.messages?.[0] || err?.message
	return message ? cleanError(message) : fallback
}

// Only the success path leaves. A rejection keeps the form, the draft and the
// server's message, and re-arms Save.
const save = () => {
	if (!isDirty.value) return
	const creating = isNew.value
	return runSave(state, {
		validate,
		toastInvalid: true,
		run: () => source.save(),
		success: creating
			? __('Badge created successfully')
			: __('Badge updated successfully'),
		after: () => emit('back'),
		failure: (err) =>
			failureMessage(
				err,
				creating ? __('Error creating badge') : __('Error updating badge')
			),
	})
}
</script>
