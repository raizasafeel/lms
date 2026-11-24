<template>
	<SettingRow :label="label" :summary="summary">
		<template v-if="!isLong" #control>
			<div class="w-60">
				<FormControl
					v-model="model"
					:type="type"
					:options="options"
					:placeholder="placeholder"
					:aria-label="label"
					variant="outline"
				/>
			</div>
		</template>
		<template v-if="isLong || $slots.default" #default>
			<div class="space-y-3">
				<slot />
				<FormControl
					v-if="isLong"
					v-model="model"
					type="textarea"
					:placeholder="placeholder"
					:aria-label="label"
					variant="outline"
				/>
			</div>
		</template>
	</SettingRow>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'

/** A settings row with one outline input: short ones sit on the end, a textarea under the label and any slotted content. */
const props = withDefaults(
	defineProps<{
		label: string
		summary?: string
		type?: 'text' | 'number' | 'textarea' | 'select' | 'combobox'
		options?: { label: string; value: string }[]
		placeholder?: string
	}>(),
	{ type: 'text', summary: undefined, options: undefined, placeholder: '' }
)
const model = defineModel<string | number | null | undefined>()

const isLong = computed(() => props.type === 'textarea')
</script>
