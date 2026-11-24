<template>
	<IntegrationConfig
		:integration-key="integrationKey"
		:is-dirty="Boolean(lms.isDirty)"
		:saving="saving"
		@save="save"
	>
		<slot :doc="lms.doc ?? {}" />
	</IntegrationConfig>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import IntegrationConfig from './IntegrationConfig.vue'
import { loadIntegrationStatus, type IntegrationKey } from './integrations'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import {
	reportSaveFailure,
	useSettingsSource,
} from '@/composables/useSettingsSource'

/** An integration page whose fields all live on LMS Settings. */
defineProps<{ integrationKey: IntegrationKey }>()
defineSlots<{ default: (props: { doc: Record<string, any> }) => unknown }>()

const lms = useSettingsSource({ doc: 'LMS Settings' })

useDirtyGuard(
	() => Boolean(lms.isDirty),
	() => void lms.reload()
)

const saving = ref(false)

const save = async () => {
	if (saving.value) return
	saving.value = true
	try {
		await lms.save()
		await loadIntegrationStatus()
		toast.success(__('Settings saved'))
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
	} finally {
		saving.value = false
	}
}
</script>
