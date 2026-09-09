<template>
	<SettingsLayout
		:title="title"
		show-back
		:unsaved="isNew ? false : isDirty"
		:save-label="__('Save')"
		:saving="saving"
		:can-save="isDirty"
		save-testid="template-save"
		@back="emit('back')"
		@save="submit"
	>
		<div v-if="doc" data-testid="template-form" class="min-w-0 space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					v-model="templateName"
					data-testid="template-name"
					:label="__('Name')"
					type="text"
					:placeholder="__('Batch Enrollment Confirmation')"
					required
					autocomplete="off"
				/>
				<FormControl
					v-model="doc.subject"
					data-testid="template-subject"
					:label="__('Subject')"
					type="text"
					:placeholder="__('Your enrollment in {{ batch_name }} is confirmed')"
					required
					autocomplete="off"
				/>
			</div>

			<div class="h-px border-t border-outline-elevation-2" />

			<Checkbox
				v-model="useHtml"
				data-testid="template-use-html"
				:label="__('Use HTML')"
				:description="
					__('Write the body as raw HTML instead of formatted text.')
				"
			/>

			<div class="min-w-0 space-y-1.5">
				<InputLabel
					:id="contentLabelId"
					:label="__('Content')"
					:required="true"
				/>
				<div
					data-testid="template-body"
					role="group"
					class="flex min-w-0 flex-col"
					:aria-labelledby="contentLabelId"
					:style="{ height: CONTENT_HEIGHT }"
					@input="codeTouched = true"
				>
					<CodeEditor
						v-if="doc.use_html"
						v-model="doc.response_html"
						type="HTML"
						:height="CONTENT_HEIGHT"
						:autofocus="false"
						:showLineNumbers="true"
					/>
					<TextEditor
						v-else
						variant="email"
						:model-value="doc.response"
						:placeholder="RICH_PLACEHOLDER"
						:height="CONTENT_HEIGHT"
						:toolbar-label="__('Content')"
						@change="setResponse"
					/>
				</div>
				<p class="text-p-sm text-ink-gray-5">
					{{ __('Jinja placeholders are expanded when the mail is sent.') }}
				</p>
			</div>

			<ErrorMessage v-if="error" class="ms-1" :message="error" />
		</div>

		<div v-else-if="loading" class="flex justify-center pt-8">
			<LoadingIndicator class="size-6 text-ink-gray-5" />
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import {
	Checkbox,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
} from 'frappe-ui'
import { computed, ref, useId } from 'vue'
import { InputLabel } from '@/components/Form/labeling'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import TextEditor from '@/components/Controls/TextEditor.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import { DOCTYPE } from '@/components/Settings/EmailTemplate/emailTemplates'
import { useSettingsRecord } from '@/composables/useSettingsRecord'
import { runSave, useSaveState } from '@/composables/useSettingsSave'
import { cleanError } from '@/utils'

/**
 * One email template, behind both New and a row. Hand-rolled after CRM's
 * TwilioSettings.vue: a `space-y-4` body, text fields in a two-column grid, and
 * a rule between sections. New and edit are the same state machine.
 */
const props = defineProps<{ name?: string | null }>()

const emit = defineEmits<{ back: [] }>()

const contentLabelId = useId()

/**
 * The body slot, as one definite height that both editors fill exactly. A
 * reserved height only the code editor filled is what left a gap under the rich
 * one, so the slot is a flex column and each control is told to fill it.
 */

// The number is the schema renderer's own row arithmetic: 1.5rem a line plus
// its padding.
const CONTENT_ROWS = 10
const CONTENT_HEIGHT = `calc(${CONTENT_ROWS} * 1.5rem + 1.25rem)`

const RICH_PLACEHOLDER = __(
	'Dear {{ member_name }},\n\nYou have been enrolled in our upcoming batch {{ batch_name }}.\n\nThanks,\nFrappe Learning'
)

const record = computed(() => props.name ?? null)

// Ace hands its value over on blur, not per keystroke, so an edit to the HTML
// body is not in the document yet when the pointer reaches Save, and a disabled
// Save swallows the click that would have blurred it.
const codeTouched = ref(false)

// `renameField: 'name'` is the whole rename. A template autonames by Prompt, so
// its name is its id and a set_value on it is dropped. The composable sends
// rename_doc first and then settles both copies of the document.
const { source, doc, isNew, isDirty, loading } = useSettingsRecord({
	doctype: DOCTYPE,
	record,
	renameField: 'name',
	dirty: (s) => s.isDirty || codeTouched.value,
})

const title = computed(() =>
	isNew.value ? __('New Email Template') : source.name || __('Email Template')
)

/**
 * The name box, over the two keys a template's name is written to. `__newname`
 * before the record exists, which is where Document.set_new_name() reads the id
 * from, and `name` after, where an edit is a rename rather than a field write.
 */
const templateName = computed<string>({
	get: () => {
		const current = doc.value
		if (!current) return ''
		return String((isNew.value ? current.__newname : current.name) ?? '')
	},
	set: (value) => {
		const current = doc.value
		if (!current) return
		current[isNew.value ? '__newname' : 'name'] = value
	},
})

// frappe-ui's Checkbox writes a boolean and `use_html` is a 0/1 check field.
// The dirty diff and the save payload both compare against the document the
// server sent, so the number is what has to go back into it.
const useHtml = computed<boolean>({
	get: () => Boolean(doc.value?.use_html),
	set: (value) => {
		const current = doc.value
		if (current) current.use_html = value ? 1 : 0
	},
})

// The editor owns its content and reports a new value rather than being written
// to, so the document is written from here.
const setResponse = (value: string) => {
	const current = doc.value
	if (current) current.response = value
}

const state = useSaveState()
const saving = state.saving
const error = state.error

const validate = (): string => {
	const current = doc.value
	if (!current) return ''
	if (!templateName.value.trim()) return __('Name is required')
	if (!current.subject) return __('Subject is required')
	const body = current.use_html ? current.response_html : current.response
	if (!body) return __('Content is required')
	return ''
}

const submit = () => {
	// Read before the write: an inserted draft is still a draft afterwards, so
	// this is the only moment the two states can be told apart.
	const wasNew = isNew.value
	return runSave(state, {
		validate,
		run: async () => {
			await source.save()
			codeTouched.value = false
		},
		success: wasNew
			? __('Email Template created successfully')
			: __('Email Template updated successfully'),
		// A draft has no record page to stay on, because the record is opened by
		// name and the name is only settled by the insert. Going back is also what
		// refetches the list.
		after: () => {
			if (wasNew) emit('back')
		},
		failure: (err: any) =>
			cleanError(err?.messages?.[0] || err?.message) ||
			__('Error saving email template'),
	})
}
</script>
