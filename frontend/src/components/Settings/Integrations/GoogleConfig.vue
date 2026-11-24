<template>
	<IntegrationConfig
		integration-key="google"
		:is-dirty="isDirty"
		:saving="saving"
		@save="save"
	>
		<FormControl
			type="text"
			:label="__('Client ID')"
			required
			:placeholder="__('Paste your OAuth client ID')"
			:model-value="google.doc?.client_id"
			:error="clientIdError"
			@update:model-value="(value: string) => google.doc && (google.doc.client_id = value)"
		/>
		<Password
			v-model="secretInput"
			:label="__('Client secret')"
			required
			:placeholder="
				hasSavedSecret
					? __('Saved, leave blank to keep it')
					: __('Paste your OAuth client secret')
			"
			:error="clientSecretError"
			:description="
				__(
					'Create an OAuth client in the Google Cloud console, under APIs & Services > Credentials.'
				)
			"
		/>
	</IntegrationConfig>
</template>

<script setup lang="ts">
// `client_secret` loads as Frappe's dummy mask or empty, so the typed secret
// lives outside the document and is written only when something was typed.
import { computed, ref } from 'vue'
import { FormControl, Password, call, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import IntegrationConfig from './IntegrationConfig.vue'
import { loadIntegrationStatus } from './integrations'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import {
	reportSaveFailure,
	useSettingsSource,
} from '@/composables/useSettingsSource'

const DOCTYPE = 'Google Settings'

const google = useSettingsSource({ doctype: DOCTYPE, name: DOCTYPE })
const secretInput = ref('')

const hasSavedSecret = computed(() => Boolean(google.doc?.client_secret))

const clientIdError = computed(() =>
	google.doc?.enable && !String(google.doc?.client_id ?? '').trim()
		? __('Google needs a client ID')
		: ''
)
const clientSecretError = computed(() =>
	google.doc?.enable && !hasSavedSecret.value && !secretInput.value
		? __('Google needs a client secret')
		: ''
)

const isDirty = computed(
	() => Boolean(google.isDirty) || secretInput.value.length > 0
)

useDirtyGuard(
	() => isDirty.value,
	() => {
		secretInput.value = ''
		if (google.isDirty) void google.reload()
	}
)

const saving = ref(false)

// save() and the secret's set_value both write Google Settings; run together
// they race the same `modified` and the second is refused, so they go in turn.
const save = async () => {
	if (saving.value) return
	saving.value = true
	try {
		if (google.isDirty) await google.save()
		if (secretInput.value)
			await call('frappe.client.set_value', {
				doctype: DOCTYPE,
				name: DOCTYPE,
				fieldname: 'client_secret',
				value: secretInput.value,
			})
		secretInput.value = ''
		await google.reload()
		await loadIntegrationStatus()
		toast.success(__('Google settings saved'))
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
	} finally {
		saving.value = false
	}
}
</script>
