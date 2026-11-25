<template>
	<div
		class="flex flex-col gap-2"
		:data-testid="`google-service-${service.key}`"
		:data-enabled="enabled ? 'true' : 'false'"
	>
		<SwitchRow
			:label="__(service.label)"
			:description="__(service.description)"
			:caution="locked"
			:disabled="Boolean(locked)"
			:model-value="enabled"
			@update:model-value="(value: boolean) => toggleIntegration(service.key, value)"
		/>
		<div class="flex items-center justify-between gap-3">
			<span
				class="truncate text-p-sm"
				:class="line.warning ? 'text-ink-amber-8' : 'text-ink-gray-6'"
				data-testid="google-service-status"
			>
				{{ line.label }}
			</span>
			<Button
				size="sm"
				:label="line.action?.label ?? __(service.records!.label)"
				:disabled="!hasRecordsAvailable(service, status)"
				data-testid="google-service-records"
				@click="openRecords"
			>
				<template v-if="line.action" #prefix>
					<span class="lucide-circle-alert size-4 text-ink-amber-6" />
				</template>
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import SwitchRow from '@/components/Controls/SwitchRow.vue'
import { openSettings } from '@/utils'
import {
	hasRecordsAvailable,
	isSwitchOn,
	statusLine,
	switchLockedReason,
	toggleIntegration,
	type Integration,
	type IntegrationStatus,
} from './integrations'

/** A Google service's switch on Google's page, with a way to its records page. */
const props = defineProps<{
	service: Integration
	status: IntegrationStatus
}>()

const enabled = computed(() => isSwitchOn(props.service.key))
const locked = computed(() =>
	switchLockedReason(props.service.key, props.status)
)
const line = computed(() =>
	statusLine(props.service.key, props.status, enabled.value)
)

const openRecords = () =>
	openSettings(
		props.service.records!.slug,
		null,
		null,
		line.value.action?.record
	)
</script>
