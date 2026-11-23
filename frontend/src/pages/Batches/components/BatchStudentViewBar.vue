<template>
	<div
		class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-5 py-2"
		role="region"
		:aria-label="__('Student view')"
	>
		<div class="flex items-center gap-2 text-p-sm text-ink-gray-7">
			<span class="lucide-eye size-4" />
			<span class="text-p-sm-medium text-ink-gray-9">
				{{ __('Student view') }}
			</span>
			<span class="hidden sm:inline">
				· {{ __('Nothing you do here is saved to a real learner') }}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<TabButtons v-model="mode" :options="modes" />
			<Button variant="outline" @click="emit('exit')">
				<template #prefix>
					<span class="lucide-x size-4" />
				</template>
				{{ __('Exit') }}
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, TabButtons } from 'frappe-ui'
import type { StudentMode } from '@/pages/Batches/composables/batchStudentView'

const mode = defineModel<StudentMode>({ required: true })
const emit = defineEmits<{ exit: [] }>()

const modes = [
	{
		label: __('Not enrolled'),
		value: 'not-enrolled',
		iconLeft: 'lucide-user-round',
	},
	{
		label: __('Enrolled'),
		value: 'enrolled',
		iconLeft: 'lucide-user-round-check',
	},
]
</script>
