<template>
	<div class="flex items-center gap-3" data-testid="integration-intro">
		<div
			class="flex size-9 shrink-0 items-center justify-center rounded-5 border border-outline-gray-2 bg-surface-base"
		>
			<span :class="[integration.icon, 'size-4.5 text-ink-gray-8']" />
		</div>
		<p class="text-p-base text-ink-gray-7">
			{{ __(integration.description) }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { integrations, type IntegrationKey } from './integrations'

/** The icon and one-line purpose every integration page opens with. */
const props = defineProps<{ integrationKey: IntegrationKey }>()

const integration = computed(
	() => integrations.find((item) => item.key === props.integrationKey)!
)
</script>
