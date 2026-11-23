<template>
	<Dropdown :options="menuOptions">
		<Button variant="subtle" :class="isActive && '!bg-surface-gray-4'">
			<template #prefix>
				<span :class="[icon, 'size-4']" aria-hidden="true" />
			</template>
			{{ isActive ? selected?.label : label }}
		</Button>
	</Dropdown>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dropdown } from 'frappe-ui'

type FilterValue = string | number | boolean | null

/** A filter chip: shows its label until a value other than `emptyValue` is picked. */
const props = withDefaults(
	defineProps<{
		label: string
		icon: string
		options: { label: string; value: FilterValue }[]
		emptyValue?: FilterValue
	}>(),
	{ emptyValue: '' }
)

const model = defineModel<FilterValue>()

const isActive = computed(() => model.value !== props.emptyValue)

const selected = computed(() =>
	props.options.find((option) => option.value === model.value)
)

const menuOptions = computed(() =>
	props.options.map((option) => ({
		label: option.label,
		icon: option.value === model.value ? 'lucide-check' : undefined,
		onClick: () => (model.value = option.value),
	}))
)
</script>
