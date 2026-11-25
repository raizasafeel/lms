<template>
	<LmsSettingsConfig v-slot="{ doc }" integration-key="zoom">
		<ZoomAttendanceSwitch v-model="doc.track_zoom_attendance" />
	</LmsSettingsConfig>
</template>

<script setup lang="ts">
import LmsSettingsConfig from './LmsSettingsConfig.vue'
import ZoomAttendanceSwitch from '@/components/Settings/Zoom/ZoomAttendanceSwitch.vue'
</script>
