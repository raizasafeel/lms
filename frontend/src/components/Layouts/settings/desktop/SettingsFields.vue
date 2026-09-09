<template>
	<div>
		<template v-for="(section, index) in sections" :key="index">
			<div
				v-if="section.label"
				class="text-p-lg-semibold text-ink-gray-8 mb-1"
				:class="{ 'mt-6': index > 0 }"
			>
				{{ __(section.label) }}
			</div>
			<div :class="flush ? '' : 'divide-y divide-outline-elevation-2'">
				<template
					v-for="(field, fieldIndex) in visibleFields(section)"
					:key="fieldIndex"
				>
					<div v-if="field.type == 'upload'" class="py-3">
						<ImageUploadField
							:icon="field.icon || 'lucide-image'"
							:label="__(field.label)"
							:description="uploadDescription(field)"
							:image_url="fileUrl(data[field.name]) || ''"
							:required="field.reqd"
							:is_private="!field.public"
							:disabled="field.disabled"
							@upload="(url) => setValue(field, url)"
							@remove="() => setValue(field, null)"
						/>
					</div>

					<div
						v-else-if="field.type == 'code'"
						class="py-3"
						@input="report(field, 'typing')"
						@focusout="report(field, 'now')"
					>
						<div
							data-testid="code-field-label"
							class="text-p-base-medium text-ink-gray-7 mb-2"
						>
							{{ __(field.label) }}
						</div>
						<CodeEditor
							:type="codeType(field)"
							v-model="data[field.name]"
							:height="codeHeight(field)"
							class="shrink-0"
							:required="field.reqd"
							:readonly="field.disabled"
							:showLineNumbers="true"
							:aria-label="__(field.label)"
						>
						</CodeEditor>
						<div
							v-if="field.description"
							data-testid="code-field-description"
							class="text-p-sm text-ink-gray-5 mt-2"
						>
							{{ __(field.description) }}
						</div>
					</div>

					<div
						v-else-if="field.type == 'textarea'"
						class="py-3"
						@input="report(field, 'typing')"
						@focusout="report(field, 'now')"
					>
						<div class="text-p-base-medium text-ink-gray-7 mb-2">
							{{ __(field.label) }}
						</div>
						<div :style="contentBox(section, field)">
							<FormControl
								type="textarea"
								:rows="field.rows || 3"
								v-model="data[field.name]"
								:disabled="field.disabled"
								:required="field.reqd"
								:aria-label="__(field.label)"
								:placeholder="field.placeholder || __(field.label)"
							/>
						</div>
						<div
							v-if="field.description"
							class="text-p-sm text-ink-gray-5 mt-2"
						>
							{{ __(field.description) }}
						</div>
					</div>

					<div v-else-if="field.type == 'richtext'" class="py-3">
						<div class="text-p-base-medium text-ink-gray-7 mb-2">
							{{ __(field.label) }}
						</div>
						<div :style="contentBox(section, field)">
							<TextEditor
								variant="email"
								:model-value="data[field.name]"
								:editable="!field.disabled"
								:placeholder="field.placeholder || __(field.label)"
								:toolbar-label="__(field.label)"
								min-height="7rem"
								max-height="13rem"
								@change="(value) => onRichText(field, value)"
							/>
						</div>
						<div
							v-if="field.description"
							class="text-p-sm text-ink-gray-5 mt-2"
						>
							{{ __(field.description) }}
						</div>
					</div>

					<div
						v-else-if="field.fullWidth"
						class="py-3"
						@input="onInput(field)"
						@focusout="onSettle(field)"
					>
						<div class="text-p-base-medium text-ink-gray-7 mb-2">
							{{ __(field.label) }}
						</div>
						<FormControl
							:key="field.name"
							v-model="data[field.name]"
							:type="field.type"
							:required="field.reqd"
							:disabled="field.disabled"
							:min="field.min"
							class="w-full"
							:aria-label="__(field.label)"
							:placeholder="field.placeholder || __(field.label)"
						/>
						<div
							v-if="field.description"
							class="text-p-sm text-ink-gray-5 mt-2"
						>
							{{ __(field.description) }}
						</div>
					</div>

					<div v-else class="flex items-center justify-between gap-4 py-3">
						<div class="flex flex-col">
							<div class="text-p-base-medium text-ink-gray-7">
								{{ __(field.label) }}
							</div>
							<div v-if="field.description" class="text-p-sm text-ink-gray-5">
								{{ __(field.description) }}
							</div>
						</div>
						<div class="shrink-0">
							<BooleanSwitch
								v-if="field.type == 'checkbox'"
								size="sm"
								:model-value="data[field.name]"
								:disabled="field.disabled"
								@update:model-value="(value) => onPick(field, value)"
							/>
							<Link
								v-else-if="field.type == 'link'"
								:model-value="displayValue(field)"
								:doctype="linkDoctype(field)"
								:filters="field.filters"
								:required="field.reqd"
								:readonly="field.disabled"
								:onCreate="createHandler(field)"
								:aria-label="__(field.label)"
								class="w-48"
								@update:model-value="(value) => onPick(field, value)"
							/>
							<Select
								v-else-if="field.type == 'select'"
								:model-value="displayValue(field)"
								:options="field.options"
								:disabled="field.disabled"
								:aria-label="__(field.label)"
								class="w-48"
								@update:model-value="(value) => onPick(field, value)"
							/>
							<span
								v-else
								class="contents"
								@input="onInput(field)"
								@focusout="onSettle(field)"
							>
								<FormControl
									:key="field.name"
									v-model="data[field.name]"
									:type="field.type"
									:rows="field.rows"
									:options="field.options"
									:required="field.reqd"
									:disabled="field.disabled"
									:min="field.min"
									class="w-48"
									:aria-label="__(field.label)"
									:placeholder="field.placeholder || __(field.label)"
								/>
							</span>
						</div>
					</div>
				</template>
			</div>
		</template>
	</div>
</template>
<script setup>
import { FormControl, Select } from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import { watch } from 'vue'
import Link from '@/components/Controls/Link.vue'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import ImageUploadField from '@/components/Controls/ImageUploadField.vue'
import TextEditor from '@/components/Controls/TextEditor.vue'
import { seedCheckboxDefaults } from '@/components/Settings/Mobile/mobileRows'

// The ImageUploadField above binds :is_private="!field.public" inline on
// purpose. Behind a helper the manifest in publicImageUploads.test.ts sees only
// "computed" and stops catching a flip to public.

const props = defineProps({
	sections: {
		type: Array,
		required: true,
	},
	data: {
		type: Object,
		required: true,
	},
	// A settings page is a long list of unrelated settings, and the rule under each
	// row keeps one from reading as part of the next. A record form is one block
	// about one thing, where the same rules only chop it into stripes.
	flush: {
		type: Boolean,
		default: false,
	},
})

// There is no Update button on these panels, so every control says when its
// value is settled. A pick commits 'now'; a text, number or code field commits
// 'typing', which the panel writes only after a rest period.
const emit = defineEmits(['commit'])

// The template branches out switch, Link and select on its own. This is for
// everything the shared FormControl branch covers, where a radio or a date is
// still a pick and a text or number field is not.
const INSTANT_TYPES = [
	'checkbox',
	'radio',
	'select',
	'link',
	'combobox',
	'autocomplete',
	'date',
	'datetime',
	'datetime-local',
	'time',
	'upload',
]

// A field the document has hidden is not rendered, so it is neither written nor
// validated. Only Transactions' coupon block uses this.
const visibleFields = (section) =>
	section.fields.filter((field) => !field.showIf || field.showIf(props.data))

// The schema names a language the way a CodeMirror mode does; CodeEditor names
// it the way Ace does. Neither is derivable from the other, and anything
// unmapped falls back to HTML.
const CODE_TYPES = { htmlmixed: 'HTML', javascript: 'JavaScript', json: 'JSON' }

const codeType = (field) => CODE_TYPES[field.mode] || 'HTML'

// 25px a line, which is what the one pre-existing code field's `rows: 10` was
// drawn at when the height was hardcoded to 250px. Its height must not move
// because a second field finally reads the number.
const codeHeight = (field) => `${(field.rows ?? 10) * 25}px`

const CONTENT_TYPES = ['textarea', 'richtext']

// Whether another content control stands in for this one. Two conditional
// fields in the same section drawn at the same `rows` are the two halves of one
// slot, and the shared number is how the schema says so.
const swapsWithSibling = (section, field) =>
	Boolean(field.showIf) &&
	section.fields.some(
		(other) =>
			other !== field &&
			Boolean(other.showIf) &&
			other.rows === field.rows &&
			CONTENT_TYPES.includes(other.type)
	)

// The height a swap slot is reserved, so nothing below the field moves when the
// toggle is flipped. Only a swap slot gets it: the floor comes out taller than
// the control it holds, which is dead space anywhere else.
const contentBox = (section, field) =>
	field.rows && swapsWithSibling(section, field)
		? { minHeight: `calc(${field.rows} * 1.5rem + 1.25rem)` }
		: undefined

// A `disabled` field is shown and never written. Every write and every report
// goes through these two, so the flag is enforced once here rather than on each
// of the eight controls.
const setValue = (field, value) => {
	if (field.disabled) return
	props.data[field.name] = value
	emit('commit', 'now')
}

const report = (field, mode) => {
	if (!field.disabled) emit('commit', mode)
}

// The editor owns its own content, so it reports a new value rather than being
// written to. It commits 'typing' because it fires on every keystroke.
const onRichText = (field, value) => {
	if (field.disabled) return
	props.data[field.name] = value
	emit('commit', 'typing')
}

// LMS Payment points a Link at whatever doctype a sibling field names, so the
// target can be a function of the document rather than a constant.
const linkDoctype = (field) =>
	typeof field.doctype === 'function'
		? field.doctype(props.data)
		: field.doctype

const commitMode = (field) =>
	INSTANT_TYPES.includes(field.type) ? 'now' : 'typing'

// The floor the schema declared for a number field, or null where it declared
// none. Only a stated bound is enforced.
const minOf = (field) =>
	field.type === 'number' && typeof field.min === 'number' ? field.min : null

const isBlank = (value) =>
	value === null || value === undefined || String(value).trim() === ''

// What a picker shows while the document has nothing. Display only: writing it
// onto the document would make the panel read dirty the instant it opened. The
// checkbox `default` is seeded instead, because a null checkbox saves nothing.
const displayValue = (field) =>
	isBlank(props.data[field.name]) && field.displayFallback !== undefined
		? field.displayFallback
		: props.data[field.name]

// The user picked it, so it is written like any other value, including when
// what they picked is the fallback they were already being shown.
const onPick = (field, value) => setValue(field, value)

// Link renders its "Create New" footer on the presence of this handler, so a
// field that declares none must be given none. The value Link passes is the
// name typed into the inline create box, so it is written back like any pick.
const createHandler = (field) =>
	field.onCreate
		? (value, close) => {
				field.onCreate(value, close)
				if (value) setValue(field, value)
		  }
		: undefined

// Cleared, non-numeric, or under the floor. The doctype's validate() rejects
// all three the same way, so this does too.
const isOutOfBounds = (field, value) => {
	const min = minOf(field)
	if (min === null) return false
	if (isBlank(value)) return true
	const number = Number(value)
	return Number.isNaN(number) || number < min
}

// The last in-bounds value each bounded field held, which is where an
// out-of-bounds one is put back to. The last valid value, not the one held at
// focus: a valid edit during the same visit may already have been written.
const lastGood = {}

const rememberBounded = (data) => {
	for (const section of props.sections)
		for (const field of section.fields)
			if (minOf(field) !== null) lastGood[field.name] = data[field.name]
}

const onInput = (field) => {
	if (field.disabled) return
	// Mid-type the field is on its way somewhere, so an out-of-bounds value is
	// left as typed and never written. A rest period armed by an earlier valid
	// keystroke would fire against it, so disarm that too.
	if (isOutOfBounds(field, props.data[field.name])) {
		emit('commit', 'cancel')
		return
	}
	lastGood[field.name] = props.data[field.name]
	emit('commit', commitMode(field))
}

// Leaving the field is the first moment the value is final, so this is the only
// place a bound is enforced. A settled field is reported even when it rolled
// back, because a cancelled write leaves the document ahead of the server.
const onSettle = (field) => {
	if (field.disabled) return
	if (isOutOfBounds(field, props.data[field.name])) {
		props.data[field.name] = lastGood[field.name]
	}
	emit('commit', 'now')
}

// Attach fields arrive from the backend as a {file_name, file_url} object, but
// become a plain file_url string after a fresh upload. Handle both shapes.
const fileUrl = (value) =>
	value && typeof value === 'object' ? value.file_url : value

// The row has one description slot. A field that explains itself uses it; one
// that does not falls back to naming the attached file, which is what the
// hand-written upload block this replaced always showed.
const uploadDescription = (field) =>
	field.description
		? __(field.description)
		: fileName(props.data[field.name]) || ''

const fileName = (value) => {
	const url = fileUrl(value)
	return value && typeof value === 'object' && value.file_name
		? value.file_name
		: (url || '').split('/').pop()
}

watch(
	() => props.data,
	(data) => {
		if (!data) return
		seedCheckboxDefaults(props.sections, data)
		// Re-seeded per document, so the first out-of-bounds edit after a load
		// has the loaded value to go back to rather than an undefined.
		rememberBounded(data)
	},
	{ immediate: true }
)
</script>
