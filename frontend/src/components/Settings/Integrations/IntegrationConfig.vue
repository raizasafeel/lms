<template>
	<SettingsLayout
		:title="__(integration.label)"
		:unsaved="isDirty"
		:save-label="__('Save')"
		:can-save="isDirty"
		:saving="saving"
		:save-testid="`${integration.key}-save`"
		show-back
		@back="emit('back')"
		@save="emit('save')"
	>
		<IntegrationIntro :integration-key="integration.key" />
		<div class="mt-6 flex flex-col gap-5">
			<slot />
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import IntegrationIntro from './IntegrationIntro.vue'
import { integrations, type IntegrationKey } from './integrations'

/** An integration's page in the grid: back to it, what it does, its fields and a Save. */
const props = defineProps<{
	integrationKey: IntegrationKey
	isDirty: boolean
	saving: boolean
}>()

const emit = defineEmits<{ save: []; back: [] }>()

const integration = computed(
	() => integrations.find((item) => item.key === props.integrationKey)!
)
</script>
