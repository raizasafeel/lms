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
				@toggle="(value) => toggleIntegration(card.integration.key, value)"
				@install="installApp(card.install?.url ?? '', openSettings)"
				@configure="emit('update:record', card.integration.key)"
				@open-records="openSettings(card.integration.records?.slug ?? '')"
				@action="(action) => runAction(card.integration, action)"
			/>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, type Component } from 'vue'
import { LoadingIndicator } from 'frappe-ui'
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
	isSwitchOn,
	loadIntegrationStatus,
	missingApp,
	statusLine,
	switchLockedReason,
	toggleIntegration,
	type CardAction,
	type Integration,
	type IntegrationKey,
} from './integrations'
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

const runAction = (integration: Integration, action: CardAction) => {
	if (action.opens === 'configure') emit('update:record', integration.key)
	else openSettings(integration.records?.slug ?? '', null, null, action.record)
}

const cardFor = (integration: Integration) => {
	const current = status.value!
	const key = integration.key
	const enabled = isSwitchOn(key)
	return {
		integration,
		enabled,
		status: statusLine(key, current, enabled),
		lockedReason: switchLockedReason(key, current),
		install: missingApp(key, current),
		canConfigure: isConfigurable(integration, current),
		canOpenRecords: hasRecordsAvailable(integration, current),
	}
}

const cards = computed(() => integrations.map(cardFor))

onMounted(loadIntegrationStatus)
</script>
