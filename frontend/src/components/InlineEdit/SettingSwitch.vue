<template>
	<SettingRow :label="label" :summary="summary">
		<template #control>
			<BooleanSwitch v-model="model" :aria-label="label" :data-label="label" />
		</template>
	</SettingRow>
</template>

<script setup lang="ts">
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'

/** A settings row that turns one option on or off. Keeps 0/1 fields as numbers. */
defineProps<{ label: string; summary?: string }>()
const model = defineModel<number | boolean | null | undefined>()
</script>
