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

			<div class="flex items-center justify-between gap-8">
				<div class="flex min-w-0 flex-col">
					<div class="text-p-base-medium text-ink-gray-7">
						{{ __('Use HTML') }}
					</div>
					<div class="text-p-sm text-ink-gray-5">
						{{ __('Write the body as raw HTML instead of formatted text.') }}
					</div>
				</div>
				<BooleanSwitch
					v-model="doc.use_html"
					data-testid="template-use-html"
					size="sm"
					:aria-label="__('Use HTML')"
				/>
			</div>

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
					<RichTextEditor
						v-else
						:content="doc.response"
						:editable="true"
						:fixed-menu="true"
						:placeholder="RICH_PLACEHOLDER"
						:editor-class="RICH_EDITOR_CLASS"
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
import { ErrorMessage, FormControl, LoadingIndicator } from 'frappe-ui'
import { computed, ref, useId } from 'vue'
import { InputLabel } from '@/components/Form/labeling'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import { DOCTYPE } from '@/components/Settings/EmailTemplate/emailTemplates'
import { useSettingsRecord } from '@/composables/useSettingsRecord'
import { runSave, useSaveState } from '@/composables/useSettingsSave'
import { cleanError } from '@/utils'

/**
 * One email template, behind both New and a row.
 *
 * Hand-rolled rather than routed through SettingsFields, after CRM's
 * Settings/Telephony/TwilioSettings.vue: a `space-y-4` body, text fields in a
 * two-column grid, and a rule between sections. New and edit are the same state
 * machine — they only ever differed in which key the name is written to and
 * whether the save is an insert.
 *
 * Handed the open record's name and reporting only that it is finished, the
 * same contract ZoomAccountForm.vue has.
 */
const props = defineProps<{ name?: string | null }>()

const emit = defineEmits<{ back: [] }>()

const contentLabelId = useId()

/**
 * The body slot, as one definite height that both editors fill exactly.
 *
 * A reserved height only the code editor filled is what left a gap under the
 * rich one: `min-height` on the slot plus a `max-h` on the editor inside it
 * capped the content well short of the reservation, and the remainder showed as
 * dead space above the hint. So the slot is a flex column of a fixed height and
 * each control is told to fill it — Ace by being handed this height outright,
 * the rich editor by growing into it — which is also what keeps the hint and
 * everything under it from moving when Use HTML is flipped.
 *
 * The number is the schema renderer's own row arithmetic: 1.5rem a line plus
 * its padding.
 */
const CONTENT_ROWS = 10
const CONTENT_HEIGHT = `calc(${CONTENT_ROWS} * 1.5rem + 1.25rem)`

// `editorClass` lands on EditorContent, the fixed menu's sibling — and Editor
// itself is renderless, so both are children of the slot above and the pair
// lays out as its flex column. A class on the RichTextEditor tag would not do
// this: with the fixed menu on it has two root nodes to fall through to, which
// is none.
const RICH_EDITOR_CLASS =
	'prose-sm min-h-0 max-w-none flex-1 overflow-y-auto rounded-b-md border-x border-b border-outline-elevation-2 bg-surface-gray-2 px-2 py-1'

const RICH_PLACEHOLDER = __(
	'Dear {{ member_name }},\n\nYou have been enrolled in our upcoming batch {{ batch_name }}.\n\nThanks,\nFrappe Learning'
)

const record = computed(() => props.name ?? null)

// Ace hands its value over on blur, not per keystroke, so an edit to the HTML
// body is not in the document yet when the pointer reaches Save — and a Save
// still disabled swallows the click that would have blurred it. This says the
// editor is holding something; the value itself lands on the blur that the now
// enabled button's focus causes, before the click runs.
const codeTouched = ref(false)

// `renameField: 'name'` is the whole rename: a template autonames by Prompt, so
// its name IS its id and a set_value on it is dropped. The composable sends the
// rename_doc first and then settles both copies of the document, which is what
// keeps a name-only edit from reading unsaved for good — getChangedFields()
// strips `name` from the payload, so the rename is the only write there is.
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
 * The name box, over the two keys a template's name is written to.
 *
 * `__newname` before the record exists — Document.set_new_name() reads the id
 * from it, and it is what the old create form sent — and `name` after, where
 * an edit is a rename rather than a field write.
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
		// A draft has no record page to stay on — the record is opened by name,
		// and the name is only settled by the insert. Going back is also what
		// refetches the list, which the list itself does on close.
		after: () => {
			if (wasNew) emit('back')
		},
		failure: (err: any) =>
			cleanError(err?.messages?.[0] || err?.message) ||
			__('Error saving email template'),
	})
}
</script>
