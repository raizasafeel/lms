<template>
	<Dialog
		v-model="show"
		:title="__('Use a template')"
		size="sm"
		:actions="dialogActions"
	>
		<template #default>
			<div v-if="step === 'pick'" class="space-y-4">
				<Link
					v-model="selected"
					data-testid="template-picker"
					:label="__('Email Template')"
					doctype="Email Template"
					:filters="{ include_disabled: 1 }"
					:required="true"
				/>
				<ErrorMessage v-if="error" :message="error" />
			</div>
			<div v-else data-testid="template-confirm" class="space-y-2">
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'This replaces the Subject and Message you have already written. This cannot be undone.'
						)
					}}
				</p>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, ErrorMessage, call } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import Link from '@/components/Controls/Link.vue'
import { cleanError } from '@/utils'

/**
 * Copies an Email Template's Subject and Message onto the notification record
 * behind it, mirroring frappe/email/doctype/notification/notification.js's
 * own `fetch_email_template` (lines 168-200): pick a body from `use_html`
 * with the other column as a fallback, and — the part this exists for — warn
 * before overwriting content the admin already wrote rather than doing it
 * silently.
 *
 * The confirmation is a second step of THIS dialog rather than a nested
 * `createDialog`, one modal at a time, and 'Choose a template' / 'Replace
 * this?' as one small state machine rather than two dialogs stacked on top of
 * each other.
 */

const props = defineProps<{
	currentSubject?: string | null
	currentMessage?: string | null
}>()

const show = defineModel<boolean>({ default: false })

const emit = defineEmits<{
	apply: [payload: { subject: string; message: string }]
}>()

type Step = 'pick' | 'confirm'

const step = ref<Step>('pick')
const selected = ref('')
const error = ref('')
const loading = ref(false)

// Fetched once, on the first press of "Use template" — held here so pressing
// Replace on the confirm step does not fetch the same template a second time.
const pending = ref<{ subject: string; message: string } | null>(null)

watch(show, (open) => {
	if (open) return
	// Cleared on close, not on open: the dialog closes itself the instant a
	// template is applied (see `apply` below), and clearing on open would wipe
	// that same tick's own state before the parent ever reads `pending`.
	step.value = 'pick'
	selected.value = ''
	error.value = ''
	pending.value = null
})

const bodyOf = (template: Record<string, any>): string =>
	template.use_html
		? template.response_html || template.response
		: template.response || template.response_html

const apply = () => {
	if (!pending.value) return
	emit('apply', pending.value)
	show.value = false
}

const fetchAndApply = async () => {
	if (!selected.value) {
		error.value = __('Choose a template first.')
		return
	}
	error.value = ''
	loading.value = true
	try {
		const template = (await call('frappe.client.get', {
			doctype: 'Email Template',
			name: selected.value,
		})) as Record<string, any>
		const body = bodyOf(template)
		if (!body) {
			error.value = __('{0} has no message to copy.').format(selected.value)
			return
		}
		pending.value = { subject: template.subject || '', message: body }
		// authored: the record already carries content this would overwrite —
		// EITHER field, not just the Message. notification.js's own version
		// checks a field against Notification's docfield default per field; this
		// dialog checks both of the two fields it actually overwrites, so an
		// admin who wrote only a Subject (message still blank) is warned too,
		// not just one who wrote a Message.
		const authored =
			Boolean((props.currentSubject || '').trim()) ||
			Boolean((props.currentMessage || '').trim())
		if (authored) step.value = 'confirm'
		else apply()
	} catch (err: any) {
		error.value =
			cleanError(err.messages?.[0] || err) || __('Failed to load the template')
	} finally {
		loading.value = false
	}
}

const keepEditing = () => {
	show.value = false
}

const dialogActions = computed(() =>
	step.value === 'pick'
		? [
				{
					label: __('Use template'),
					variant: 'solid' as const,
					loading: loading.value,
					onClick: fetchAndApply,
				},
		  ]
		: [
				{ label: __('Keep my content'), onClick: keepEditing },
				{
					label: __('Replace'),
					variant: 'solid' as const,
					theme: 'red' as const,
					onClick: apply,
				},
		  ]
)
</script>
