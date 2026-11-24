<template>
	<MultiSelect
		:modelValue="roles"
		:options="options"
		:hideSearch="true"
		variant="ghost"
		size="sm"
		class="w-52"
		:aria-label="__('Roles of {0}').format(name)"
		@update:modelValue="(value) => emit('update:roles', ordered(value))"
	>
		<template #summary>
			<span class="truncate text-ink-gray-8">{{ summary }}</span>
		</template>
		<template #footer>
			<p
				class="border-t border-outline-gray-1 px-2.5 py-1.5 text-p-xs text-ink-gray-6"
			>
				{{ __('Clear every role to take them off.') }}
			</p>
		</template>
	</MultiSelect>
</template>

<script setup lang="ts">
import { MultiSelect } from 'frappe-ui'
import { computed } from 'vue'
import {
	ineligibleReason,
	roleDescription,
	roleLabel,
	ROLES_BY_DOCTYPE,
	type PeopleDoctype,
} from '@/components/InlineEdit/People/people'
import type { PeopleRole } from '@/types/lms/LMSRoleAssignment'

/** Every role one person holds, picked from a checklist; roles they may not hold are disabled with the reason. */
const props = defineProps<{
	doctype: PeopleDoctype
	name: string
	roles: PeopleRole[]
	/** The roles this person may hold here. */
	eligible: PeopleRole[]
}>()
const emit = defineEmits<{ 'update:roles': [PeopleRole[]] }>()

// A role held before the rules changed stays listed, so it can be taken away.
const options = computed(() =>
	ROLES_BY_DOCTYPE[props.doctype].map((role) => {
		const allowed = props.eligible.includes(role)
		return {
			label: roleLabel(role),
			value: role,
			description: allowed
				? roleDescription(role, props.doctype)
				: ineligibleReason(role),
			disabled: !allowed && !props.roles.includes(role),
		}
	})
)

const summary = computed(() =>
	props.roles.length ? props.roles.map(roleLabel).join(', ') : __('No role')
)

const ordered = (value: (string | number)[]) =>
	ROLES_BY_DOCTYPE[props.doctype].filter((role) => value.includes(role))
</script>
