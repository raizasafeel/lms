<template>
	<BooleanSwitch
		v-model="tracked"
		:label="__('Attendance tracking')"
		:description="__('Records who joined each Zoom class and for how long.')"
		data-testid="zoom-attendance"
	/>
</template>

<script setup lang="ts">
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'

/** The `track_zoom_attendance` flag of LMS Settings, saved by the page it sits on. */
const tracked = defineModel<number | boolean | null | undefined>()
</script>
