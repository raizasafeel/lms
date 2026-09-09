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
							:label="__(field.label)"
							:description="uploadDescription(field)"
							:image_url="fileUrl(data[field.name]) || ''"
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
							<RichTextEditor
								:content="data[field.name]"
								:editable="!field.disabled"
								:fixed-menu="true"
								:placeholder="field.placeholder || __(field.label)"
								editor-class="prose-sm max-w-none border-b border-x border-outline-elevation-2 bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem] max-h-[13rem] overflow-y-auto"
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
import RichTextEditor from '@/components/RichTextEditor.vue'
import { seedCheckboxDefaults } from '@/components/Settings/Mobile/mobileRows'

// The ImageUploadField above binds :is_private="!field.public", and it is
// written inline deliberately. Privacy is the FIELD's decision, never this
// component's: the backend maps every Attach / Attach Image field of a
// third-party <Gateway> Settings doctype to type 'Upload' (api.py
// get_transformed_fields), and those reach here via the payment gateway form —
// merchant QR codes and KYC documents among them. Only a field that opts in with
// `public: true` may be world-readable; everything else keeps frappe's private
// default. Behind a helper the privacy ratchet in publicImageUploads.test.ts can
// only see "computed" and would stop catching a flip to public — which is why
// the negation stays here and is not folded into the shared row.

const props = defineProps({
	sections: {
		type: Array,
		required: true,
	},
	data: {
		type: Object,
		required: true,
	},
	// A settings page is a long list of unrelated settings, and the rule under
	// each row is what keeps one from reading as part of the next. A record form
	// is one block of fields about one thing, where the same rules only chop it
	// into stripes — so a form asks for them off.
	flush: {
		type: Boolean,
		default: false,
	},
})

// There is no Update button on these panels, so every control has to say when
// its value is settled and the panel above decides what to do about it.
//
// A checkbox, radio, dropdown, switch or Link commits 'now' — a pick is whole
// at the first interaction. A text, number or code field commits 'typing',
// which the panel writes only after a rest period, so a half-typed value is
// not sent a character at a time into a doctype that validates on save
// (contact_us_email, contact_us_url and lesson_dwell_time each throw from
// validate()).
//
// Leaving the field ends the typing, so focusout commits 'now' too. That is
// not a second write: dirtiness is a comparison, so it writes if the value
// changed and does nothing if it did not. focusout and not blur, because blur
// does not bubble past the input.
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
// it the way Ace does. One is not derivable from the other, so the mapping is
// written out — and anything unmapped falls back to HTML, which is what every
// code field rendered as before any of them was asked.
const CODE_TYPES = { htmlmixed: 'HTML', javascript: 'JavaScript', json: 'JSON' }

const codeType = (field) => CODE_TYPES[field.mode] || 'HTML'

// 25px a line, which is what the one pre-existing code field's `rows: 10` was
// already being drawn at back when the height was hardcoded to 250px. Its
// height must not move because a second field finally reads the number.
const codeHeight = (field) => `${(field.rows ?? 10) * 25}px`

const CONTENT_TYPES = ['textarea', 'richtext']

// Whether another content control stands in for this one. Two conditional
// fields in the same section drawn at the same `rows` are the two halves of a
// single slot — Email Template's HTML body and its rich one, swapped by Use
// HTML — and the shared number is how the schema says so.
const swapsWithSibling = (section, field) =>
	Boolean(field.showIf) &&
	section.fields.some(
		(other) =>
			other !== field &&
			Boolean(other.showIf) &&
			other.rows === field.rows &&
			CONTENT_TYPES.includes(other.type)
	)

// The height a swap slot is reserved, so the box keeps it whichever control is
// inside and nothing below the field moves when the toggle is flipped.
//
// Only a swap slot gets it. The floor is computed at 1.5rem a line and a
// textarea is drawn at frappe-ui's `text-base`, whose line box is 16.1px, so
// the floor always comes out taller than the control it holds — 116px against
// 78px at SEO's `rows: 4`. Where two controls swap that surplus is the price of
// the slot not moving; where one control stands alone it was pure dead space
// between the textarea and its description, which is what put a gap under the
// two meta fields and nowhere else.
const contentBox = (section, field) =>
	field.rows && swapsWithSibling(section, field)
		? { minHeight: `calc(${field.rows} * 1.5rem + 1.25rem)` }
		: undefined

// A `disabled` field is shown and never written: a consent flag and a
// redemption count are records of what happened, not settings. Every write and
// every report goes through these two, so the flag is enforced once here rather
// than on each of the eight controls — a control that reports a change anyway
// (a rich text editor still fires `change` while uneditable) would have the
// panel save a value nobody chose.
const setValue = (field, value) => {
	if (field.disabled) return
	props.data[field.name] = value
	emit('commit', 'now')
}

const report = (field, mode) => {
	if (!field.disabled) emit('commit', mode)
}

// The editor owns its own content, so it reports a new value rather than being
// written to. 'typing' and not 'now': it fires on every keystroke, and a body
// of prose sent a character at a time is what the rest period exists to stop.
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
// none. Only a stated bound is enforced, so a number field without a `min` goes
// through untouched.
const minOf = (field) =>
	field.type === 'number' && typeof field.min === 'number' ? field.min : null

const isBlank = (value) =>
	value === null || value === undefined || String(value).trim() === ''

// What a picker SHOWS while the document has nothing: the schema's
// `displayFallback`. Display only, and that is the whole point — writing it
// onto the document would make it differ from originalDoc, so the panel would
// report dirty the instant it opened and, because status reports dirty ahead of
// saved, the header would read "Not saved" untouched and never reach "Saved".
// The blank stays blank until the user picks something.
//
// The checkbox `default` is the other thing entirely and still IS seeded, by
// seedCheckboxDefaults: a null checkbox renders off but saves nothing, so a
// declared `1` would flip off behind the user's back. A picker has no such trap.
const displayValue = (field) =>
	isBlank(props.data[field.name]) && field.displayFallback !== undefined
		? field.displayFallback
		: props.data[field.name]

// The user picked it, so it is written like any other value — including when
// what they picked is the fallback they were already being shown.
const onPick = (field, value) => setValue(field, value)

// Link renders its "Create New" footer on the presence of this handler, so a
// field that declares none must be given none — otherwise every link field
// grows a button that does nothing.
//
// The value Link passes is the name the user typed into the inline create box,
// which IS the record being created, so it is written back like any other pick.
// Without that the user creates the record and the field they created it from
// is still empty. A handler that only opens a dialog is called with null and
// writes nothing.
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

// The last in-bounds value each bounded field held — where an out-of-bounds one
// is put back to. The last VALID value and not the value the field held at
// focus: a valid edit taken during the same visit may already have been written
// by the rest period, and rewinding past it would leave the panel dirty with a
// value nobody typed and no way to clear the marker.
const lastGood = {}

const rememberBounded = (data) => {
	for (const section of props.sections)
		for (const field of section.fields)
			if (minOf(field) !== null) lastGood[field.name] = data[field.name]
}

const onInput = (field) => {
	if (field.disabled) return
	// Mid-type the field is on its way somewhere — an empty box between 3 and 15
	// is not a mistake — so an out-of-bounds value is left exactly as typed and
	// never written. But a rest period armed by an earlier, valid keystroke is
	// still ticking, and it would fire against the invalid value the field now
	// holds. Disarm it. Cancelling the whole page's pending write is right, not
	// merely expedient: the document carries a value validate() rejects, so
	// there is nothing that could be saved from it until this field settles.
	if (isOutOfBounds(field, props.data[field.name])) {
		emit('commit', 'cancel')
		return
	}
	lastGood[field.name] = props.data[field.name]
	emit('commit', commitMode(field))
}

// Leaving the field is the first moment the value is final, so this is the only
// place a bound is enforced. An out-of-bounds value goes back to the last good
// one -- and is still reported, because the rolled-back value only matches the
// server's if the write carrying it actually fired. Type 15, clear the box
// (which cancels that pending write), then tab away, and the document is left
// holding 15 against a server holding 30: dirty, with no timer armed, so the
// marker reads "Not saved" for good and the dispose-time flush finds nothing to
// send. Reporting a settled field costs nothing when it is already clean --
// useAutosave's send() returns on `!isDirty`.
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
// hand-written upload block this replaced always showed. Payment Gateways does
// the same, for the same reason — its gateway fields carry no description.
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
