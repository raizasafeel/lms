<template>
	<Dialog
		v-model:open="open"
		:title="__('Change owner')"
		:actions="[
			{
				label: __('Change owner'),
				variant: 'solid',
				disabled: !picked || picked === owner,
				loading: saving,
				onClick: submit,
			},
		]"
	>
		<template #default>
			<div class="space-y-3">
				<p class="text-p-base text-ink-gray-7">
					{{ ownerRule }}
				</p>
				<FormControl
					v-model="query"
					type="text"
					:placeholder="__('Search people')"
					:aria-label="__('Search people')"
				>
					<template #prefix>
						<span class="lucide-search size-4 text-ink-gray-5" />
					</template>
				</FormControl>
				<ul class="max-h-64 overflow-y-auto" role="listbox">
					<li v-for="person in results.data || []" :key="person.value">
						<button
							type="button"
							role="option"
							:aria-selected="picked === person.value"
							class="flex w-full items-center gap-3 rounded-4 px-2 py-1.5 text-start hover:bg-surface-gray-2"
							:class="{ 'bg-surface-gray-3': picked === person.value }"
							@click="picked = person.value"
						>
							<Avatar
								:image="person.user_image"
								:label="person.label"
								size="sm"
							/>
							<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">
								{{ person.label }}
							</span>
							<span class="truncate text-p-xs text-ink-gray-6">
								{{ person.value }}
							</span>
						</button>
					</li>
				</ul>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import {
	Avatar,
	call,
	createResource,
	Dialog,
	FormControl,
	toast,
} from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import {
	OWNER_SITE_ROLE,
	type PeopleDoctype,
} from '@/components/InlineEdit/People/people'
import type { Resource } from '@/types'
import { cleanError } from '@/utils'

interface UserHit {
	value: string
	label: string
	user_image?: string
}

/** Hands the course to another Course Creator or the batch to another Batch Evaluator, straight away: owner is not a form field. */
const props = defineProps<{
	doctype: PeopleDoctype
	name: string
	owner: string
}>()
const emit = defineEmits<{ changed: [string] }>()
const open = defineModel<boolean>('open', { required: true })

const ownerRule = computed(() =>
	props.doctype === 'LMS Batch'
		? __(
				'The new owner can do everything, including deleting the batch. Only Batch Evaluators can own a batch.'
		  )
		: __(
				'The new owner can do everything, including deleting the course. Only Course Creators can own a course.'
		  )
)

const query = ref('')
const picked = ref<string | null>(null)
const saving = ref(false)

const results = createResource({
	url: 'lms.lms.api.search_users_by_role',
	method: 'POST',
	makeParams: () => ({
		txt: query.value,
		roles: JSON.stringify([OWNER_SITE_ROLE[props.doctype], 'Moderator']),
	}),
	auto: true,
}) as Resource<UserHit[] | null>

const search = useDebounceFn(() => results.reload(), 300)
watch(query, search)

function submit({ close }: { close: () => void }): void {
	if (!picked.value) return
	saving.value = true
	call('lms.lms.people.change_owner', {
		doctype: props.doctype,
		name: props.name,
		owner: picked.value,
	})
		.then((owner: string) => {
			toast.success(__('Owner changed'))
			emit('changed', owner)
			close()
		})
		.catch((error: { messages?: string[] }) =>
			toast.error(cleanError(error.messages?.[0] || error))
		)
		.finally(() => (saving.value = false))
}
</script>
