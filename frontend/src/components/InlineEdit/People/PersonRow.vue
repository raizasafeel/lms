<template>
	<li class="flex items-center gap-3 py-2.5">
		<Avatar :image="image" :label="name" size="lg" />
		<div class="min-w-0 flex-1">
			<div class="truncate text-base-medium text-ink-gray-9">{{ name }}</div>
			<div class="truncate text-p-sm text-ink-gray-6">{{ description }}</div>
		</div>
		<slot name="actions">
			<Select
				:modelValue="role"
				:options="roleOptions"
				variant="ghost"
				size="sm"
				:aria-label="__('Role of {0}').format(name)"
				class="w-44"
				@update:modelValue="(value) => emit('update:role', value as PeopleRole)"
			/>
			<Button
				variant="ghost"
				size="sm"
				:aria-label="__('Remove {0}').format(name)"
				@click="emit('remove')"
			>
				<template #icon>
					<span class="lucide-x size-4" aria-hidden="true" />
				</template>
			</Button>
		</slot>
	</li>
</template>

<script setup lang="ts">
import { Avatar, Button, Select } from 'frappe-ui'
import { computed } from 'vue'
import type { PeopleRole } from '@/types/lms/LMSRoleAssignment'
import { roleLabel } from '@/components/InlineEdit/People/people'

/** One person in a People list: who they are, what they do, and their role. */
const props = defineProps<{
	name: string
	image?: string
	description: string
	role?: PeopleRole
	/** The roles this person may hold here. */
	roles?: PeopleRole[]
}>()
const emit = defineEmits<{ 'update:role': [PeopleRole]; remove: [] }>()

// A legacy row can hold a role its person is no longer eligible for; keep it listed.
const roleOptions = computed(() =>
	[
		...new Set([...(props.roles ?? []), ...(props.role ? [props.role] : [])]),
	].map((value) => ({ label: roleLabel(value), value }))
)
</script>
