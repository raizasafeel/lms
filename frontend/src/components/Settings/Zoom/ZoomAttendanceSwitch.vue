<template>
	<Tooltip :text="__('Records who joined each Zoom class and for how long.')">
		<span class="flex items-center gap-2">
			<span class="text-p-sm text-ink-gray-7">
				{{ __('Attendance tracking') }}
			</span>
			<Switch
				size="sm"
				data-testid="zoom-attendance"
				:model-value="isOn"
				:disabled="!integrationStatus || saving"
				:aria-label="__('Attendance tracking')"
				@update:model-value="setAttendance"
			/>
		</span>
	</Tooltip>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Switch, Tooltip } from 'frappe-ui'
import type { FrappeResourceError } from 'frappe-ui'
import {
	integrationStatus,
	loadIntegrationStatus,
	saveIntegrations,
} from '@/components/Settings/Integrations/integrations'
import { reportSaveFailure } from '@/composables/useSettingsSource'

/** Writes on flip, like the account switches in the list below it. */
const saving = ref(false)
const isOn = computed(() => Boolean(integrationStatus.value?.zoom.attendance))

onMounted(() => {
	if (!integrationStatus.value) void loadIntegrationStatus()
})

const setAttendance = async (value: boolean) => {
	saving.value = true
	try {
		await saveIntegrations({ zoom_attendance: value })
	} catch (error) {
		reportSaveFailure(error as FrappeResourceError)
	} finally {
		saving.value = false
	}
}
</script>
