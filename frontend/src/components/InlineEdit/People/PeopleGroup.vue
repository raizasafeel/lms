<template>
	<SettingsGroup
		:title="__('People')"
		icon="lucide-users"
		name="people"
		:info="info"
	>
		<ul class="divide-y divide-outline-gray-1">
			<PersonRow
				:name="describe(owner).full_name || owner"
				:image="describe(owner).user_image"
				:description="ownerDescription"
			>
				<template #actions>
					<Badge :label="__('Owner')" theme="gray" />
					<Button
						v-if="canChangeOwner"
						variant="subtle"
						size="sm"
						@click="showOwnerDialog = true"
					>
						{{ __('Change owner') }}
					</Button>
				</template>
			</PersonRow>
			<PersonRow
				v-for="member in members"
				:key="member"
				:name="nameOf(member)"
				:image="describe(member).user_image"
				:description="describeRoles(member)"
			>
				<template #actions>
					<RolesPicker
						:doctype="doctype"
						:name="nameOf(member)"
						:roles="rolesOf(doctype, people, member)"
						:eligible="eligibleRoles(doctype, describe(member).roles)"
						@update:roles="(roles) => setRoles(member, roles)"
					/>
					<Button
						variant="ghost"
						size="sm"
						:aria-label="__('Remove {0}').format(nameOf(member))"
						@click="setRoles(member, [])"
					>
						<template #icon>
							<span class="lucide-x size-4" aria-hidden="true" />
						</template>
					</Button>
				</template>
			</PersonRow>
		</ul>
		<div class="py-2.5">
			<MultiLink
				:modelValue="members"
				doctype="User"
				url="lms.lms.api.search_users_by_role"
				:placeholder="__('Search people')"
				:clearable="false"
				:searchParams="{ roles: JSON.stringify(STAFF_SITE_ROLES) }"
				:transform="toOptions"
				:extraOptions="knownMembers"
				variant="ghost"
				class="w-fit"
				:aria-label="__('Add someone')"
				@update:modelValue="setMembers"
			>
				<template #prefix>
					<span class="lucide-plus size-4 text-ink-gray-6" />
				</template>
				<template #summary>
					<span class="text-ink-gray-7">{{ __('Add someone') }}</span>
				</template>
				<template #item-prefix="{ item }">
					<Avatar :image="item.image" :label="item.label" size="sm" />
				</template>
				<template #item-label="{ item }">
					<PersonOption :label="item.label" :email="String(item.value)" />
				</template>
			</MultiLink>
		</div>
	</SettingsGroup>

	<ChangeOwnerDialog
		v-if="showOwnerDialog"
		v-model:open="showOwnerDialog"
		:doctype="doctype"
		:name="name"
		:owner="owner"
		@changed="(owner) => emit('ownerChanged', owner)"
	/>
</template>

<script setup lang="ts">
import { Avatar, Badge, Button } from 'frappe-ui'
import { computed, ref } from 'vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import ChangeOwnerDialog from '@/components/InlineEdit/People/ChangeOwnerDialog.vue'
import PersonOption from '@/components/InlineEdit/People/PersonOption.vue'
import PersonRow from '@/components/InlineEdit/People/PersonRow.vue'
import RolesPicker from '@/components/InlineEdit/People/RolesPicker.vue'
import {
	eligibleRoles,
	roleDescription,
	rolesOf,
	withMemberRoles,
	STAFF_SITE_ROLES,
	type PeopleDoctype,
	type PersonRow as Person,
} from '@/components/InlineEdit/People/people'
import { usePeopleDetails } from '@/components/InlineEdit/People/usePeopleDetails'
import type { PeopleRole } from '@/types/lms/LMSRoleAssignment'

interface UserHit {
	label?: string
	value?: string
	user_image?: string
	roles?: string[]
}

/** Who works on a course or batch: the owner, then each person and their role. */
const props = defineProps<{
	doctype: PeopleDoctype
	name: string
	owner: string
	canChangeOwner: boolean
}>()
const emit = defineEmits<{ ownerChanged: [string] }>()
const people = defineModel<Person[]>({ required: true })

const showOwnerDialog = ref(false)
const members = computed(() => [
	...new Set(people.value.map((row) => row.member)),
])
const { describe, remember, load } = usePeopleDetails(() => [
	props.owner,
	...members.value,
])

const isCourse = computed(() => props.doctype === 'LMS Course')
const info = computed(() =>
	isCourse.value
		? __(
				'Editors are shown as the course instructors. Only evaluators can grade.'
		  )
		: __(
				'Editors are shown as the batch instructors. Only evaluators can grade.'
		  )
)
const ownerDescription = computed(() =>
	isCourse.value
		? __('Everything, including deleting the course')
		: __('Everything, including deleting the batch')
)

function toOptions(rows: Record<string, unknown>[]) {
	const hits = rows as UserHit[]
	remember(
		hits.map((hit) => ({
			name: hit.value || '',
			full_name: hit.label,
			user_image: hit.user_image,
			roles: hit.roles || [],
		}))
	)
	return hits.map((hit) => ({
		label: hit.label || hit.value || '',
		value: hit.value || '',
		image: hit.user_image || '',
	}))
}

const knownMembers = computed(() =>
	members.value.map((member) => ({
		label: describe(member).full_name || member,
		value: member,
		image: describe(member).user_image || '',
	}))
)

// A new person starts in the first role their site roles allow, so wait for them.
async function setMembers(next: string[]): Promise<void> {
	const added = next.filter((member) => !members.value.includes(member))
	await load(added)
	const kept = people.value.filter((row) => next.includes(row.member))
	people.value = [
		...kept,
		...added.map((member) => ({
			member,
			role: eligibleRoles(props.doctype, describe(member).roles)[0] ?? 'Editor',
		})),
	]
}

const nameOf = (member: string): string => describe(member).full_name || member

const describeRoles = (member: string): string =>
	rolesOf(props.doctype, people.value, member)
		.map((role) => roleDescription(role, props.doctype))
		.join(' · ')

// Clearing every role takes the person off.
function setRoles(member: string, roles: PeopleRole[]): void {
	people.value = withMemberRoles(props.doctype, people.value, member, roles)
}
</script>
