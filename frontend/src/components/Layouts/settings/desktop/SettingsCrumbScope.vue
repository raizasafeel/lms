<template>
	<slot />
</template>

<script setup lang="ts">
import { provide } from 'vue'
import {
	settingsCrumbKey,
	type SettingsCrumb,
} from '@/components/Layouts/settings/desktop/settingsCrumb'

/** Hands one panel's breadcrumb to whichever header it renders. */
const props = defineProps<{ crumb: SettingsCrumb | null }>()

provide(settingsCrumbKey, props.crumb)
</script>
