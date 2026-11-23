<template>
	<MultiLink
		v-model="instructors"
		doctype="User"
		url="lms.lms.api.search_users_by_role"
		:searchParams="{ roles: JSON.stringify(ROLES) }"
		:transform="toOptions"
		:extraOptions="knownSelected"
		:placeholder="__('Add instructors')"
		:aria-label="__('Instructors')"
		variant="ghost"
		class="rounded-4"
		:class="missing && 'bg-surface-red-1 ring-2 ring-outline-red-3'"
		:onCreate="openMemberModal"
	>
		<template #prefix>
			<div
				v-if="instructors.length"
				class="flex -space-x-1.5 rtl:space-x-reverse"
			>
				<Avatar
					v-for="person in visibleAvatars"
					:key="person.value"
					:image="person.image"
					:label="person.label"
					size="sm"
				/>
			</div>
			<span v-else class="lucide-user-plus size-4 text-ink-gray-5" />
		</template>
		<template #summary>
			<span :class="instructors.length ? 'text-ink-gray-7' : 'text-ink-gray-4'">
				{{ summary }}
			</span>
		</template>
		<template #item-prefix="{ item }">
			<Avatar :image="item.image" :label="item.label" size="sm" />
		</template>
	</MultiLink>
	<NewMemberModal
		v-model="showMemberModal"
		:defaultRoles="['batch_evaluator']"
		@created="
			(user: { name: string }) => (instructors = [...instructors, user.name])
		"
	/>
</template>

<script setup lang="ts">
import { Avatar, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import NewMemberModal from '@/components/Modals/NewMemberModal.vue'
import { summarisePeople } from '@/utils/peopleSummary'

interface PersonOption {
	label: string
	value: string
	image: string
}
interface UserHit {
	label?: string
	value?: string
	name?: string
	user_image?: string
	description?: string
}

/** The batch's instructors as avatars and a name summary, picked in place. */
defineProps<{ missing?: boolean }>()
const instructors = defineModel<string[]>({ required: true })

const ROLES = ['Batch Evaluator', 'Course Creator']
const showMemberModal = ref(false)
const known = ref(new Map<string, PersonOption>())

function toOptions(rows: Record<string, unknown>[]): PersonOption[] {
	return (rows as UserHit[]).map((row) => ({
		label: row.label || row.description || row.value || row.name || '',
		value: row.value || row.name || '',
		image: row.user_image || '',
	}))
}

// Saved instructors arrive as bare user ids; look up their names and avatars.
const lookup = createResource({
	url: 'lms.lms.api.search_users_by_role',
	method: 'POST',
	makeParams: () => ({
		roles: JSON.stringify(ROLES),
		names: JSON.stringify(instructors.value),
	}),
	onSuccess(rows: UserHit[]) {
		const next = new Map(known.value)
		for (const option of toOptions(rows as Record<string, unknown>[])) {
			if (option.value) next.set(option.value, option)
		}
		known.value = next
	},
})

watch(
	instructors,
	(ids) => {
		if (ids.some((id) => !known.value.has(id))) lookup.reload()
	},
	{ immediate: true }
)

const describe = (id: string): PersonOption =>
	known.value.get(id) ?? { label: id, value: id, image: '' }

const knownSelected = computed(() =>
	instructors.value.filter((id) => known.value.has(id)).map(describe)
)
const visibleAvatars = computed(() =>
	instructors.value.slice(0, 3).map(describe)
)
const summary = computed(() =>
	instructors.value.length
		? summarisePeople(instructors.value.map((id) => describe(id).label))
		: __('Add instructors')
)

function openMemberModal(close: () => void): void {
	close()
	showMemberModal.value = true
}
</script>
