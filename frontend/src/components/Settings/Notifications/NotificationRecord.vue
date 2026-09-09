<template>
	<SettingsLayout
		:title="title"
		show-back
		:unsaved="isDirty"
		v-model:enabled="enabled"
		:save-label="__('Save')"
		:saving="saving"
		:can-save="isDirty"
		save-testid="notification-save"
		@back="emit('back')"
		@save="submit"
	>
		<div v-if="doc" data-testid="notification-form" class="min-w-0 space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<div class="space-y-3">
					<Select
						v-model="doc.channel"
						data-testid="notification-channel"
						:label="__('Sent via')"
						:options="channelOptions()"
						required
					/>
					<Checkbox
						v-if="doc.channel === 'Email'"
						v-model="sendSystemNotification"
						data-testid="notification-in-app"
						:label="__('Also notify in the app')"
					/>
				</div>
			</div>

			<div class="h-px border-t border-outline-elevation-2" />

			<p
				v-if="!canWriteWording"
				data-testid="wording-locked-notice"
				class="text-p-sm text-ink-gray-5"
			>
				{{
					__(
						'Only a System Manager can edit the Subject and Message — writing a rule’s wording can change what a Jinja template reads on this site.'
					)
				}}
			</p>
			<FormControl
				v-model="doc.subject"
				data-testid="notification-subject"
				:label="__('Subject')"
				type="text"
				:disabled="!canWriteWording"
				required
				autocomplete="off"
			/>

			<div class="min-w-0 space-y-1.5">
				<TextEditor
					data-testid="notification-message"
					variant="email"
					:model-value="doc.message"
					:label="__('Message')"
					:required="true"
					:editable="canWriteWording"
					:placeholder="richPlaceholder()"
					:height="CONTENT_HEIGHT"
					@change="setMessage"
					@input="codeTouched = true"
				/>
				<div class="flex items-start justify-between gap-4">
					<p class="text-p-sm text-ink-gray-5">
						{{ __('Jinja placeholders are expanded when the mail is sent.') }}
					</p>
					<Button
						v-if="canWriteWording"
						size="sm"
						class="shrink-0"
						data-testid="use-template"
						@click="showTemplateDialog = true"
					>
						{{ __('Use a template') }}
					</Button>
				</div>
			</div>
		</div>

		<div v-else-if="loading" class="flex justify-center pt-8">
			<LoadingIndicator class="size-6 text-ink-gray-5" />
		</div>

		<ErrorMessage v-if="error" class="ms-1 mt-4" :message="error" />
	</SettingsLayout>

	<UseTemplateDialog
		v-if="canWriteWording"
		v-model="showTemplateDialog"
		:current-subject="doc?.subject"
		:current-message="doc?.message"
		@apply="applyTemplate"
	/>
</template>

<script setup lang="ts">
import {
	Button,
	Checkbox,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	call,
} from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'
import TextEditor from '@/components/Controls/TextEditor.vue'
import Select from '@/components/Controls/Select.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import UseTemplateDialog from '@/components/Settings/Notifications/UseTemplateDialog.vue'
import {
	METHOD,
	NOTIFICATIONS_DOCTYPE,
	channelOptions,
} from '@/components/Settings/Notifications/notifications'
import { reloadSettingsLists } from '@/composables/useSettingsListResource'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import { runSave, useSaveState } from '@/composables/useSettingsSave'
import { cleanError } from '@/utils'
import type { User } from '@/types/settings'

/**
 * One Notification rule, behind a row on Settings > Notifications.
 *
 * Hand-rolled, after EmailAccountForm.vue: this reads and writes through
 * lms.lms.api.get_notification_rules / set_notification_rule rather than a
 * document resource, because core Notification grants DocPerms to System
 * Manager only and this page is reachable by Moderators too. There is no
 * get-one endpoint, so the record is found in the same search-scoped list the
 * page itself reads — searching by the rule's own name always matches it.
 *
 * Recipients, Condition, Document Type and Send Alert On are deliberately not
 * shown — this page edits wording and channel only, not who a rule
 * addresses or what fires it.
 */

interface NotificationRuleRow {
	name: string
	enabled: number
	channel: string
	send_system_notification: number
	subject: string
	message: string
}

const props = defineProps<{ name?: string | null }>()

const emit = defineEmits<{ back: [] }>()

const CONTENT_ROWS = 10
const CONTENT_HEIGHT = `calc(${CONTENT_ROWS} * 1.5rem + 1.25rem)`

// A function, not a module-scope constant: a plain `const __(...)` freezes the
// string against a runtime locale change, and it is exactly the pattern this
// file's own sibling module (notifications.ts) documents against. `doc.` is
// deliberate too — a rule renders against `doc` (see notifications.py's own
// Jinja placeholders), not a bare `member_name`, so a copy-pasted placeholder
// without it would 500 at send time rather than merely rendering blank.
const richPlaceholder = () =>
	__('Dear {{ doc.member_name }},\n\n…\n\nThanks,\nFrappe Learning')

// `set_notification_rule` requires System Manager for `subject`/`message`
// specifically (see the endpoint's own docstring: a rule's message renders as
// Jinja with an unchecked frappe.db.sql/get_all/get_value in scope, so writing
// it is a read-anything primitive core reserves to System Manager). The same
// injected `$user` resource Preferences.vue and half a dozen forms already
// gate desk-only actions on — not a new mechanism.
const user = inject<User>('$user')
const canWriteWording = computed(() => user?.data?.is_system_manager === true)

const record = computed(() => props.name ?? null)

const doc = ref<NotificationRuleRow | null>(null)
const loaded = ref<NotificationRuleRow | null>(null)
const loading = ref(true)

// Set from the editor's native `input`, which fires on the keystroke itself,
// ahead of the `change` that carries the value onto `doc.message`. Without it a
// Save disabled at the moment of the click swallows that click, and the edit
// that was mid-flight is never sent.
const codeTouched = ref(false)

const showTemplateDialog = ref(false)

const saveState = useSaveState()
const saving = saveState.saving
// Rendered outside the `v-if="doc"` block: a rule that fails to load leaves
// `doc` null and `loading` already false, so an ErrorMessage inside the form
// would mount nowhere and the panel would draw as an empty title bar.
const error = saveState.error

const title = computed(() => doc.value?.name || __('Notification'))

const enabled = computed<boolean | undefined>({
	get: () => (doc.value ? Boolean(doc.value.enabled) : undefined),
	set: (value) => {
		if (doc.value) doc.value.enabled = value ? 1 : 0
	},
})

const sendSystemNotification = computed<boolean>({
	get: () => Boolean(doc.value?.send_system_notification),
	set: (value) => {
		if (doc.value) doc.value.send_system_notification = value ? 1 : 0
	},
})

const fetchRecord = async () => {
	if (!record.value) return
	loading.value = true
	try {
		const rows = (await call(METHOD.list, {
			search: record.value,
		})) as NotificationRuleRow[]
		const found = rows.find((row) => row.name === record.value) ?? null
		doc.value = found ? { ...found } : null
		loaded.value = found ? { ...found } : null
		// A renamed or deleted rule answers with a list that simply has no match.
		// Without this the panel would sit empty and silent.
		if (!found) error.value = __('That notification no longer exists')
	} catch (err: any) {
		error.value = __('Failed to load notification')
		console.error(err)
	} finally {
		loading.value = false
	}
}

onMounted(fetchRecord)

const setMessage = (value: string) => {
	if (doc.value) doc.value.message = value
}

const applyTemplate = ({
	subject,
	message,
}: {
	subject: string
	message: string
}) => {
	if (!doc.value) return
	doc.value.subject = subject
	doc.value.message = message
	codeTouched.value = false
}

const isDirty = computed(() => {
	const current = doc.value
	const original = loaded.value
	if (!current || !original) return false
	return (
		current.enabled !== original.enabled ||
		current.channel !== original.channel ||
		current.send_system_notification !== original.send_system_notification ||
		current.subject !== original.subject ||
		current.message !== original.message ||
		codeTouched.value
	)
})

useDirtyGuard(
	() => isDirty.value,
	// Restore the record the panel loaded with. `loaded` is the server's copy,
	// so this returns the form to exactly what a reopen would fetch.
	() => {
		doc.value = loaded.value ? { ...loaded.value } : null
		codeTouched.value = false
	}
)

/**
 * Only the fields that changed, over the record's name — never the whole
 * document. `set_notification_rule` writes only what it is given, and sending
 * every field regardless of whether it moved would defeat the point of that
 * guarantee from the one caller that could actually rely on it.
 */
const buildPayload = (): Record<string, unknown> | null => {
	const current = doc.value
	const original = loaded.value
	if (!current || !original || !record.value) return null
	const payload: Record<string, unknown> = { name: record.value }
	if (current.enabled !== original.enabled)
		payload.enabled = current.enabled ? 1 : 0
	if (current.channel !== original.channel) payload.channel = current.channel
	if (current.send_system_notification !== original.send_system_notification)
		payload.send_system_notification = current.send_system_notification ? 1 : 0
	if (current.subject !== original.subject) payload.subject = current.subject
	if (current.message !== original.message || codeTouched.value)
		payload.message = current.message
	return payload
}

const validate = (): string => {
	const current = doc.value
	if (!current) return ''
	if (!current.subject?.trim()) return __('Subject is required')
	if (!current.message?.trim()) return __('Message is required')
	return ''
}

const submit = () =>
	runSave(saveState, {
		validate,
		run: async () => {
			const payload = buildPayload()
			if (!payload) return
			const updated = (await call(METHOD.set, payload)) as NotificationRuleRow
			doc.value = { ...updated }
			loaded.value = { ...updated }
			codeTouched.value = false
		},
		success: __('Notification updated successfully'),
		after: () => reloadSettingsLists(NOTIFICATIONS_DOCTYPE),
		failure: (err: any) =>
			cleanError(err?.messages?.[0] || err?.message) ||
			__('Error saving notification'),
	})
</script>
