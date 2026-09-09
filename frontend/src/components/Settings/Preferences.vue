<template>
	<SettingsLayout :save-state="saveState">
		<div v-if="settings.doc">
			<div class="text-p-lg-semibold text-ink-gray-8 mb-1">
				{{ __('Preferences') }}
			</div>

			<div class="divide-y divide-outline-elevation-2">
				<div class="flex items-center justify-between gap-4 py-3">
					<div class="flex flex-col">
						<div class="text-p-base-medium text-ink-gray-7">
							{{ __('System Language') }}
						</div>
						<div class="text-p-sm text-ink-gray-5">
							{{ __('The language this site falls back to.') }}
						</div>
					</div>
					<div class="shrink-0">
						<Link
							:key="controlKey.language"
							:model-value="systemLanguage"
							doctype="Language"
							data-test="system-language"
							:readonly="!systemEditable"
							:aria-label="__('System Language')"
							class="w-48"
							@update:model-value="(value) => onSystemSelect('language', value)"
						/>
					</div>
				</div>

				<div class="flex items-center justify-between gap-4 py-3">
					<div class="flex flex-col">
						<div class="text-p-base-medium text-ink-gray-7">
							{{ __('System Timezone') }}
						</div>
						<div class="text-p-sm text-ink-gray-5">
							{{ __('The timezone new batches and courses start from.') }}
						</div>
					</div>
					<div class="shrink-0">
						<Combobox
							:key="controlKey.time_zone"
							:model-value="systemTimezone"
							:options="timezoneOptions"
							data-test="system-timezone"
							:disabled="!systemEditable"
							:aria-label="__('System Timezone')"
							:placeholder="__('Search timezone')"
							class="w-48"
							@update:model-value="
								(value) => onSystemSelect('time_zone', value)
							"
						/>
					</div>
				</div>

				<div class="flex items-center justify-between gap-4 py-3">
					<div class="flex flex-col">
						<div class="text-p-base-medium text-ink-gray-7">
							{{ __('Text Direction') }}
						</div>
						<div class="text-p-sm text-ink-gray-5">
							{{ __('Auto follows the language of the site.') }}
						</div>
					</div>
					<div class="shrink-0">
						<Select
							v-model="textDirection"
							:options="directionOptions"
							data-test="text-direction"
							:aria-label="__('Text Direction')"
							class="w-48"
							@update:model-value="() => docSave.commit('now')"
						/>
					</div>
				</div>
			</div>

			<div class="mt-6">
				<SettingsFields
					:sections="accessSections"
					:data="settings.doc"
					@commit="docSave.commit"
				/>
			</div>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import {
	Combobox,
	Select,
	createDocumentResource,
	createResource,
} from 'frappe-ui'
import { computed, inject, reactive, ref, watch, type Ref } from 'vue'
import Link from '@/components/Controls/Link.vue'
import SettingsFields from '@/components/Layouts/settings/desktop/SettingsFields.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import { useAutosave, type AutosaveStatus } from '@/composables/useAutosave'
import { useSettings } from '@/stores/settings'
import type { User } from '@/types/settings'

interface SystemPreferences {
	language: string
	time_zone: string
	timezones: string[]
}

// The shape this page uses of a frappe-ui document resource. `isDirty` is the
// resource's own doc-vs-originalDoc comparison, and `submit()` resolves with
// the saved document or rejects — it also skips the round trip entirely when
// nothing changed, so calling it on a clean doc is free.
interface SettingsResource {
	doc: Record<string, any>
	isDirty?: boolean
	save: {
		submit: (values?: object, options?: object) => Promise<unknown>
		loading: boolean
	}
}

// `label` and `description` are the sidebar item's, handed down by Settings.vue
// to every panel component. This page draws neither — its two sections head
// themselves — but both stay declared: undeclared props fall through to the
// root element, and `label="General"` on a div is not markup we want.
const props = defineProps<{
	label: string
	description?: string
	data?: SettingsResource
}>()

const settingsStore = useSettings()
const user = inject<User>('$user')

// Settings.vue hands the LMS Settings resource down as `data`. Reaching for
// the document here when it does not is not a second copy:
// createDocumentResource returns the instance already cached under this
// doctype + name.
function cachedSettings(): SettingsResource {
	return createDocumentResource({
		doctype: 'LMS Settings',
		name: 'LMS Settings',
		fields: ['*'],
		cache: 'LMS Settings',
		auto: true,
	}) as unknown as SettingsResource
}

const settings = props.data ?? cachedSettings()

const canEditSystem = computed<boolean>(
	() => user?.data?.is_system_manager === true
)

// An LMS Settings doc saved before text_direction existed comes back with the
// field null, and a Select bound to null renders an empty "Select option".
//
// Resolve it for display only. Writing Auto onto the doc would be a change
// against originalDoc, so documentResource would report the panel dirty the
// instant it opened and the header would read "Not saved" before the user had
// touched anything. Nothing is lost by not persisting it: resolve_text_direction
// singles out only 'Left to Right' and 'Right to Left', so a null field and an
// explicit Auto already mean the same thing to the server.
const TEXT_DIRECTION_DEFAULT = 'Auto'

const textDirection = computed<string>({
	get: () => settings.doc?.text_direction || TEXT_DIRECTION_DEFAULT,
	set: (value) => {
		if (settings.doc) settings.doc.text_direction = value
	},
})

type SystemField = 'language' | 'time_zone'

const systemLanguage = ref<string>('')
const systemTimezone = ref<string>('')

const systemValues: Record<SystemField, Ref<string>> = {
	language: systemLanguage,
	time_zone: systemTimezone,
}

// Bumped to remount the control whose clear was refused. Both controls draw a
// frappe-ui Combobox, which keeps the text it displays in an internal `query`
// ref and re-derives it from the value only once the popover closes — so
// restoring a value the prop already held would leave the box looking empty
// until then. Remounting re-derives it now.
const controlKey = reactive<Record<SystemField, number>>({
	language: 0,
	time_zone: 0,
})

const preferences = createResource({
	url: 'lms.lms.api.get_system_preferences',
	auto: true,
})

const savePreferences = createResource({
	url: 'lms.lms.api.set_system_preferences',
})
// The permission AND the answer. `get_system_preferences` only starts fetching
// when this panel mounts, while the panel itself renders as soon as the
// app-start LMS Settings resource has a doc -- so both controls were live for a
// window in which `systemDirty` reads false (no server value to compare
// against) and the arrival watcher then overwrites whatever was picked. The
// choice vanished with no write, no error and no "Not saved" marker.
const systemEditable = computed<boolean>(
	() => canEditSystem.value && Boolean(preferences.data)
)

watch(
	() => preferences.data as SystemPreferences | undefined,
	(data) => {
		if (!data) return
		systemLanguage.value = data.language
		systemTimezone.value = data.time_zone
	},
	{ immediate: true }
)

const timezoneOptions = computed(() => {
	const data = preferences.data as SystemPreferences | undefined
	return (data?.timezones || []).map((zone) => ({
		label: zone,
		value: zone,
	}))
})

const directionOptions = computed(() => [
	{ label: __('Auto'), value: 'Auto' },
	{ label: __('Left to Right'), value: 'Left to Right' },
	{ label: __('Right to Left'), value: 'Right to Left' },
])

const accessSections = [
	{
		label: 'Access & Availability',
		fields: [
			{
				label: 'Allow Guest Access',
				name: 'allow_guest_access',
				description:
					'If enabled, users can access the course and batch lists without logging in.',
				type: 'checkbox',
			},
			{
				label: 'Disable PWA',
				name: 'disable_pwa',
				description:
					'If checked, users will not be able to install the application as a Progressive Web App.',
				type: 'checkbox',
			},
			{
				label: 'Allow Job Posting',
				name: 'allow_job_posting',
				description:
					'If enabled, users can post job openings on the job board. Else only admins can post jobs.',
				type: 'checkbox',
			},
		],
	},
	// Communication's own General page was dissolved into this one, so these
	// two sections arrive whole rather than being redistributed. They write
	// LMS Settings, which is the doc this page already autosaves, so they need
	// no writer of their own.
	{
		label: 'Contact Information',
		fields: [
			{
				label: 'Email',
				name: 'contact_us_email',
				type: 'text',
				description:
					'Users can reach out to this email for support or inquiries.',
			},
			{
				label: 'URL',
				name: 'contact_us_url',
				type: 'text',
				description:
					'Users can reach out to this URL for support or inquiries.',
			},
		],
	},
	// Not a notification gate: it decides whether a booking carries a calendar
	// invite, not whether the evaluation mail is sent, which is why it sits here
	// with the rest of the site's contact settings.
	{
		label: 'Evaluations',
		fields: [
			{
				label: 'Send calendar invite for evaluations',
				name: 'send_calendar_invite_for_evaluations',
				type: 'checkbox',
				description:
					'If enabled, it sends google calendar invite to the student for evaluations.',
			},
		],
	},
]

// Two writers, because the values on this page live in two places: the three
// access toggles and the text direction are LMS Settings fields, while the
// language and the timezone are System Settings and only reach the server
// through a System Manager-gated endpoint. Committing one must not write the
// other — a moderator changing a toggle has no business issuing a privileged
// call, and a language change should not push an unrelated doc.
const docSave = useAutosave({
	isDirty: () => Boolean(settings.isDirty),
	write: () =>
		settings.save.submit().then(() => settingsStore.loadSidebarSettings(true)),
})

// The system pair has no document behind it, so its clean value is what the
// endpoint last returned. Reloading that resource after a write is what takes
// the pair out of "Not saved" — the same shape as originalDoc, one level up.
const systemDirty = computed<boolean>(() => {
	const data = preferences.data as SystemPreferences | undefined
	if (!data) return false
	return (
		systemLanguage.value !== data.language ||
		systemTimezone.value !== data.time_zone
	)
})

const systemSave = useAutosave({
	isDirty: () => canEditSystem.value && systemDirty.value,
	write: () =>
		savePreferences
			.submit({
				language: systemLanguage.value,
				time_zone: systemTimezone.value,
			})
			.then(() => preferences.reload()),
})

// A control the user cannot edit cannot have changed, and an unchanged value
// is not dirty, so a commit here writes only when there is something to write.
const commitSystem = () => systemSave.commit('now')

// Emptying either control is not one of the choices this pair offers. Link
// clears to '' and Combobox to null, and the endpoint guards each field with
// `if value:` — so a cleared value is dropped without an error: the server
// keeps what it had, the reload hands that back, and the local ref stays
// empty. systemDirty would then read true with nothing left to write and the
// header would sit on "Not saved" for good. Put the last value the endpoint
// returned back instead, and send nothing.
//
// Nothing needs cancelling on the way out. cancel() disarms the rest timer,
// which only a 'typing' commit arms, and this pair always commits 'now'. A
// write already in flight is not ours to take back either — it carries a value
// the user did pick, and its reload refreshes both refs when it lands.
const onSystemSelect = (field: SystemField, value: string | null) => {
	const current = systemValues[field]
	if (value) {
		current.value = value
		commitSystem()
		return
	}
	const data = preferences.data as SystemPreferences | undefined
	current.value = data?.[field] ?? ''
	controlKey[field] += 1
}

// One marker for both writers: whichever is busy speaks, and the quieter
// states only surface once nothing is in flight.
const saveState = computed<AutosaveStatus>(() => {
	const states = [docSave.status.value, systemSave.status.value]
	for (const state of ['saving', 'error', 'pending', 'dirty', 'saved'] as const)
		if (states.includes(state)) return state
	return 'idle'
})
</script>
