<template>
	<SettingsLayout
		:title="__('Integrations')"
		:unsaved="isDirty"
		:save-label="__('Save')"
		:can-save="isDirty"
		:saving="saving"
		save-testid="integrations-save"
		@save="save"
	>
		<div v-if="!status" class="flex flex-1 items-center justify-center py-20">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
		<div v-else class="grid grid-cols-2 gap-4">
			<IntegrationCard
				v-for="card in cards"
				:key="card.integration.key"
				v-bind="card"
				@toggle="(value) => toggle(card.integration.key, value)"
				@install="installApp(card.installUrl ?? '', openSettings)"
				@configure="openSettings(card.integration.slug)"
			/>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { LoadingIndicator, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import IntegrationCard from './IntegrationCard.vue'
import {
	installApp,
	integrations,
	integrationStatus as status,
	isIntegrationEnabled,
	loadIntegrationStatus,
	lockedReason,
	missingApp,
	needsGoogleRole,
	saveIntegrations,
	statusLine,
	type Integration,
	type IntegrationChanges,
	type IntegrationKey,
	type ToggleKey,
} from './integrations'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import { reportSaveFailure } from '@/composables/useSettingsSource'
import { openSettings } from '@/utils'

/** Toggled but not yet saved; Save writes these and clears them. */
const pending = reactive<IntegrationChanges>({})

const isEnabled = (key: ToggleKey): boolean =>
	pending[key] ?? isIntegrationEnabled(key)

const toggle = (key: IntegrationKey, value: boolean) => {
	if (key === 'frappe_meet') return
	if (value === isIntegrationEnabled(key)) delete pending[key]
	else pending[key] = value
}

const isDirty = computed(() => Object.keys(pending).length > 0)

const cardFor = (integration: Integration) => {
	const current = status.value!
	const key = integration.key
	const missing = missingApp(key, current)
	const toggleKey = key === 'frappe_meet' ? null : key
	const enabled = toggleKey ? isEnabled(toggleKey) : false
	return {
		integration,
		enabled,
		status: statusLine(key, current, enabled),
		toggleable: Boolean(toggleKey),
		lockedReason: toggleKey
			? lockedReason(toggleKey, current, { enabled: isEnabled })
			: '',
		installUrl: missing?.url ?? null,
		canConfigure:
			Boolean(integration.slug) &&
			!missing &&
			!needsGoogleRole(key, current) &&
			isIntegrationEnabled(key),
	}
}

const cards = computed(() => integrations.map(cardFor))

const discard = () => {
	for (const key of Object.keys(pending)) delete pending[key as ToggleKey]
}

useDirtyGuard(() => isDirty.value, discard)

onMounted(loadIntegrationStatus)

const saving = ref(false)

const save = async () => {
	if (saving.value) return
	saving.value = true
	try {
		await saveIntegrations({ ...pending })
		discard()
		toast.success(__('Integrations saved'))
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
		await loadIntegrationStatus()
	} finally {
		saving.value = false
	}
}
</script>
