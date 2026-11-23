<template>
	<div v-if="doc" class="mx-auto w-full max-w-3xl space-y-10 px-5 py-8">
		<SettingsGroup
			:title="__('Enrollment')"
			:description="__('How people join this batch.')"
		>
			<SettingRow
				:label="__('Self enrollment')"
				:summary="
					doc.allow_self_enrollment
						? __(
								'Learners enroll themselves, and pay first if the batch is paid.'
						  )
						: __('Learners are asked to contact you, and you enroll them.')
				"
			>
				<template #control>
					<Switch
						v-model="doc.allow_self_enrollment"
						:aria-label="__('Self enrollment')"
					/>
				</template>
			</SettingRow>
			<SettingRow
				:label="__('Confirmation email')"
				:summary="__('Sent to each learner when they are enrolled.')"
			>
				<template #control>
					<Link
						variant="outline"
						ref="emailTemplateLink"
						v-model="doc.confirmation_email_template"
						doctype="Email Template"
						:placeholder="__('Default email')"
						:aria-label="__('Confirmation email template')"
						:onCreate="openEmailTemplateForm"
						align="end"
						class="w-56"
					/>
				</template>
			</SettingRow>
		</SettingsGroup>

		<SettingsGroup
			:title="__('Live classes')"
			:description="
				__('Each class gets a join link from the video call account set here.')
			"
		>
			<SettingRow :label="__('Video calls')" :summary="conferencingSummary">
				<template #control>
					<Select
						variant="outline"
						v-model="doc.conferencing_provider"
						:options="conferencingOptions"
						:aria-label="__('Conferencing provider')"
						class="w-40"
					/>
				</template>
				<Link
					variant="outline"
					v-if="doc.conferencing_provider === 'Zoom'"
					v-model="doc.zoom_account"
					doctype="LMS Zoom Settings"
					:label="__('Zoom account')"
					:onCreate="
						(_value: string, close: () => void) => openSettings('zoom', close)
					"
				/>
				<Link
					variant="outline"
					v-else-if="doc.conferencing_provider === 'Google Meet'"
					v-model="doc.google_meet_account"
					doctype="LMS Google Meet Settings"
					:label="__('Google Meet account')"
					:onCreate="
						(_value: string, close: () => void) =>
							openSettings('google-meet', close)
					"
				/>
			</SettingRow>
		</SettingsGroup>

		<SettingsGroup
			:title="__('Search and sharing')"
			:description="
				__('How the batch shows up in search results and shared links.')
			"
		>
			<SettingRow
				:label="__('Description')"
				:summary="__('Leave empty to use the short description.')"
			>
				<FormControl
					variant="outline"
					v-model="form!.meta.description"
					type="textarea"
					:placeholder="doc.description"
					:aria-label="__('Meta description')"
				/>
			</SettingRow>
			<SettingRow :label="__('Keywords')">
				<FormControl
					variant="outline"
					v-model="form!.meta.keywords"
					:placeholder="__('Comma separated keywords')"
					:aria-label="__('Meta keywords')"
				/>
			</SettingRow>
		</SettingsGroup>

		<BatchManageGroup :batch="batch" />
	</div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FormControl, Switch } from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import Select from '@/components/Controls/Select.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import BatchManageGroup from '@/pages/Batches/components/BatchManageGroup.vue'
import { openBatchForm } from '@/composables/useBatchForms'
import { injectBatchForm } from '@/pages/Batches/composables/useBatchForm'
import { openSettings } from '@/utils'
import type { BatchDetails, Resource } from '@/types'

/** Batch settings: what is not edited in place on the overview. */
const props = defineProps<{ batch: Resource<BatchDetails | null> }>()

const router = useRouter()
const route = useRoute()
const form = injectBatchForm()
const doc = computed(() => form?.doc.value ?? null)
const emailTemplateLink = useTemplateRef<{ reload: () => void }>(
	'emailTemplateLink'
)

const conferencingOptions = [
	{ label: __('None'), value: '' },
	{ label: __('Zoom'), value: 'Zoom' },
	{ label: __('Google Meet'), value: 'Google Meet' },
]

const conferencingSummary = computed(() => {
	const account = doc.value?.zoom_account || doc.value?.google_meet_account
	if (!doc.value?.conferencing_provider) {
		return __('No account connected, so classes have no join links.')
	}
	return account
		? `${doc.value.conferencing_provider} · ${account}`
		: __('Pick the account classes are created from.')
})

const openEmailTemplateForm = (): void => {
	openBatchForm(
		router,
		'NewBatchEmailTemplate',
		props.batch.data?.name ?? '',
		route.hash
	)
}

// EmailTemplateForm is a route, so it hands the new name back in the URL.
// The param is stripped once adopted, or a reload would re-apply it.
watch(
	[() => route.query.emailTemplate, doc],
	([created]) => {
		if (typeof created !== 'string' || !created || !doc.value) return
		doc.value.confirmation_email_template = created
		emailTemplateLink.value?.reload()
		const query = { ...route.query }
		delete query.emailTemplate
		router.replace({ ...route, query })
	},
	{ immediate: true, flush: 'post' }
)
</script>
