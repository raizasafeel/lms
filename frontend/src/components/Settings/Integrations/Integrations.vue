<template>
	<component
		:is="pages[openKey]"
		v-if="openKey && pages[openKey]"
		@back="emit('update:record', null)"
	/>
	<SettingsLayout v-else :title="__('Integrations')">
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
				@configure="emit('update:record', card.integration.key)"
				@open-records="openSettings(card.integration.records?.slug ?? '')"
			/>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, reactive, type Component } from 'vue'
import { LoadingIndicator, toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import IntegrationCard from './IntegrationCard.vue'
import GoogleConfig from './GoogleConfig.vue'
import CodeRunnerConfig from './CodeRunnerConfig.vue'
import UnsplashConfig from './UnsplashConfig.vue'
import FlowConfig from './FlowConfig.vue'
import ZoomConfig from './ZoomConfig.vue'
import {
	installApp,
	integrations,
	hasRecordsAvailable,
	integrationStatus as status,
	isConfigurable,
	isIntegrationEnabled,
	loadIntegrationStatus,
	lockedReason,
	missingApp,
	saveIntegrations,
	statusLine,
	type Integration,
	type IntegrationKey,
} from './integrations'
import { reportSaveFailure } from '@/composables/useSettingsSource'
import { openSettings } from '@/utils'

/** The integration whose page is open in place of the grid, kept in the URL. */
const props = defineProps<{ record?: string | null }>()
const emit = defineEmits<{ 'update:record': [record: string | null] }>()

const pages: Partial<Record<IntegrationKey, Component>> = {
	google: markRaw(GoogleConfig),
	code_runner: markRaw(CodeRunnerConfig),
	unsplash: markRaw(UnsplashConfig),
	flow: markRaw(FlowConfig),
	zoom: markRaw(ZoomConfig),
}

const openKey = computed(() => props.record as IntegrationKey | null)

/** Flipped and being written; shown at once and dropped when the write settles. */
const pending = reactive<Partial<Record<IntegrationKey, boolean>>>({})

const isEnabled = (key: IntegrationKey): boolean =>
	pending[key] ?? isIntegrationEnabled(key)

// Each switch saves the moment it flips; a refusal puts it back.
const toggle = async (key: IntegrationKey, value: boolean) => {
	if (key in pending) return
	pending[key] = value
	try {
		await saveIntegrations({ [key]: value })
		toast.success(value ? __('Turned on') : __('Turned off'))
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
		await loadIntegrationStatus()
	} finally {
		delete pending[key]
	}
}

const cardFor = (integration: Integration) => {
	const current = status.value!
	const key = integration.key
	const enabled = isEnabled(key)
	return {
		integration,
		enabled,
		status: statusLine(key, current, enabled),
		lockedReason:
			key in pending
				? __('Saving…')
				: lockedReason(key, current, { enabled: isEnabled }),
		installUrl: missingApp(key, current)?.url ?? null,
		canConfigure: isConfigurable(integration, current),
		canOpenRecords: hasRecordsAvailable(integration, current),
	}
}

const cards = computed(() => integrations.map(cardFor))

onMounted(loadIntegrationStatus)
</script>
