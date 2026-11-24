<template>
	<LmsSettingsConfig v-slot="{ doc }" integration-key="flow">
		<div
			class="flex items-center justify-between gap-4 rounded-6 border border-outline-gray-2 p-4"
			data-testid="flow-connection"
		>
			<div class="flex flex-col gap-1">
				<span class="text-p-base-medium text-ink-gray-8">
					{{ __('AI service') }}
				</span>
				<span
					class="text-p-sm"
					:class="isReady ? 'text-ink-gray-6' : 'text-ink-amber-8'"
				>
					{{
						isReady
							? __('Connected. Flow can chat on this site.')
							: __(
									'Not connected yet. Open Flow to connect ChatGPT, Claude or another service.'
							  )
					}}
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				<Button
					v-if="canManageFlow"
					:label="__('Flow settings')"
					@click="openExternal('/desk/flow-settings')"
				>
					<template #suffix>
						<span class="lucide-arrow-up-right size-4" />
					</template>
				</Button>
				<Button v-if="!isFlowOpen" :label="__('Open Flow')" @click="openFlow" />
			</div>
		</div>
		<BooleanSwitch
			v-model="doc.hide_flow_for_learners"
			:label="__('Hide Flow for learners')"
			:description="
				__(
					'People whose only role in the LMS is learner get no Flow panel, sidebar item or Ctrl+I, and cannot start a chat.'
				)
			"
		/>
	</LmsSettingsConfig>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import LmsSettingsConfig from './LmsSettingsConfig.vue'
import { integrationStatus } from './integrations'
import { openExternal } from '@/utils/openExternal'
import { useFlowDocked } from '@/composables/useFlowDocked'
import { canManageGoogleIntegrations as isSystemManager } from '@/components/Settings/GoogleApi/googleApi'

const isReady = computed(() => Boolean(integrationStatus.value?.flow.ready))

// Flow's own settings are System Manager-only in Desk.
const canManageFlow = isSystemManager()

const isFlowOpen = useFlowDocked()

const openFlow = () =>
	(window as { flow?: { toggle: () => void } }).flow?.toggle()
</script>
