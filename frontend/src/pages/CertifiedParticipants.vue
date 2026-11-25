<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:rows="rows"
		:total-count="memberCount"
		:loading="participants.list.loading"
		:has-next-page="participants.hasNextPage"
		row-key="key"
		v-model:page-length="pageLength"
		:empty-name="__('Certified Members')"
		empty-icon="lucide-badge-check"
		:empty-title="emptyState?.title"
		:empty-description="emptyState?.description"
		@load-more="participants.next()"
	>
		<template v-if="emptyState" #empty-actions>
			<EmptyStateActions
				list="certified_participants"
				:create-label="__('New Course')"
				docs="https://docs.frappe.io/learning/issue-a-certificate"
				@create="newCourseFromEmptyState"
			/>
		</template>

		<template #actions>
			<Button :route="{ name: 'Courses', query: { certification: true } }">
				<template #prefix>
					<span class="lucide-graduation-cap size-4" />
				</template>
				{{ __('Get Certified') }}
			</Button>
		</template>

		<template #name>
			{{ __('All certified members') }}
			<span class="ms-1 text-ink-gray-6">{{ memberCount }}</span>
		</template>

		<template #filters>
			<FormControl
				v-model="nameFilter"
				:placeholder="__('Search')"
				:aria-label="__('Search')"
				type="text"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" />
				</template>
			</FormControl>
			<ClearableCombobox
				v-if="categories.data?.length"
				v-model="currentCategory"
				:options="categories.data.filter((c) => c.value)"
				:placeholder="__('Category')"
				:ariaLabel="__('Category')"
				@update:modelValue="updateParticipants()"
			/>
			<ToggleFilter
				:modelValue="openToWork"
				:label="__('Open to Work')"
				@update:modelValue="setOpenToWork"
			/>
			<ToggleFilter
				:modelValue="hiring"
				:label="__('Hiring')"
				@update:modelValue="setHiring"
			/>
		</template>

		<template #card="{ row }">
			<component
				:is="row.username ? 'router-link' : 'div'"
				:to="profileRoute(row.username, 'ProfileAbout')"
				class="flex h-full flex-col rounded-6 border border-outline-gray-2 bg-surface-base p-2 text-start transition"
				:class="
					row.username ? 'hover:border-outline-gray-3 hover:shadow-sm' : ''
				"
				@pointerenter="playingCard = row.key"
				@pointerleave="playingCard = null"
				@focusin="playingCard = row.key"
				@focusout="playingCard = null"
			>
				<!-- The top sheet spans the frame and may run off its bottom edge. -->
				<div
					class="h-40 shrink-0 overflow-hidden rounded-4 bg-surface-gray-2 px-4 pt-3"
				>
					<CertificateStack
						v-if="row.certificates?.length"
						:certificates="row.certificates"
						:playing="playingCard === row.key"
					/>
				</div>
				<div class="flex items-center gap-2.5 px-2 pb-1.5 pt-3">
					<Avatar :label="row.full_name" :image="row.user_image" size="lg" />
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<div class="min-w-0 truncate text-base-semibold text-ink-gray-9">
								{{ row.full_name }}
							</div>
							<Badge
								v-if="OPEN_TO_BADGES[row.open_to]"
								class="ms-auto shrink-0"
								:theme="OPEN_TO_BADGES[row.open_to].theme"
								:label="OPEN_TO_BADGES[row.open_to].label"
							/>
						</div>
						<div
							class="truncate text-p-sm text-ink-gray-6"
							:title="row.headline || undefined"
						>
							{{
								shortHeadline(row.headline) ||
								__('Joined {0}').format(timeAgo(row.creation))
							}}
						</div>
					</div>
				</div>
			</component>
		</template>
	</ListPage>
</template>
<script setup>
import {
	Avatar,
	Badge,
	Button,
	call,
	createListResource,
	FormControl,
	usePageMeta,
} from 'frappe-ui'
import ClearableCombobox from '@/components/Controls/ClearableCombobox.vue'
import ToggleFilter from '@/components/Controls/ToggleFilter.vue'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { sessionStore } from '../stores/session'
import { useRouter } from 'vue-router'
import { setFormSource } from '@/composables/formTracking'
import CertificateStack from '@/components/Certificates/CertificateStack.vue'
import ListPage from '@/components/Layouts/pages/ListPage.vue'
import EmptyStateActions from '@/components/EmptyStateActions.vue'
import { profileRoute } from '@/utils/routes'
import { timeAgo } from '@/utils/format'

const filters = ref({})
const currentCategory = ref('')
const nameFilter = ref('')
const openToWork = ref(false)
const hiring = ref(false)
const { brand } = sessionStore()
const memberCount = ref(0)
const user = inject('$user')
const router = useRouter()
const playingCard = ref(null)

/** One badge per value of the User `open_to` field. */
const OPEN_TO_BADGES = {
	Work: { label: __('Open to work'), theme: 'green' },
	Hiring: { label: __('Hiring'), theme: 'blue' },
}

const HEADLINE_WORDS = 3

/** The first few words of a headline, without emoji or stray symbols. */
function shortHeadline(headline) {
	const words = (headline || '')
		.replace(/[\p{S}\p{Extended_Pictographic}\u200d\ufe0f]/gu, ' ')
		.split(/\s+/)
		.filter((word) => /[\p{L}\p{N}]/u.test(word))
	const short = words.slice(0, HEADLINE_WORDS).join(' ')
	return words.length > HEADLINE_WORDS ? `${short}…` : short
}

// Learners keep the default wording and the Get Certified button above.
const emptyState = computed(() => {
	// The same people canCreateCourse allows; importing it drags in the router.
	if (window.read_only_mode) return null
	if (!user.data?.is_instructor && !user.data?.is_moderator) return null
	return {
		title: __('No one is certified yet'),
		description: __(
			'Learners who finish a course with a certificate show up here. Add one to a course to begin.'
		),
	}
})

function newCourseFromEmptyState() {
	setFormSource('empty_state')
	router.push({ name: 'NewCourse' })
}

onMounted(() => {
	if (!user.data) {
		router.push({ name: 'Courses' })
		return
	}
	setFiltersFromQuery()
	updateParticipants()
	// TextInput emits on input and change; watched after query hydration to avoid a refetch.
	watch(nameFilter, () => updateParticipants())
})

const participants = createListResource({
	doctype: 'LMS Certificate',
	url: 'lms.lms.api.get_certified_participants',
	start: 0,
	pageLength: 24,
	cache: ['certified_participants'],
})

// get_certified_participants pops `member`, so no row carries a `name` and
// ListPage's default row key would be "undefined" for every card. `username` is
// unique on User, but Frappe leaves it blank when it collides, so fall back to
// the position to keep the keys distinct.
const rows = computed(() =>
	(participants.data || []).map((participant, index) => ({
		...participant,
		key: participant.username ? `u:${participant.username}` : `i:${index}`,
	}))
)

const pageLength = computed({
	get: () => participants.pageLength,
	set: (value) => {
		// reload() keeps the already-loaded row count when start > 0, so the new
		// page size would be ignored after a Load More unless paging resets too.
		participants.update({ pageLength: value, start: 0 })
		participants.reload()
	},
})

const getMemberCount = () => {
	call('lms.lms.api.get_count_of_certified_members', {
		filters: filters.value,
	}).then((data) => {
		memberCount.value = data
	})
}

const setOpenToWork = (value) => {
	openToWork.value = value
	updateParticipants()
}

const setHiring = (value) => {
	hiring.value = value
	updateParticipants()
}

const categories = createListResource({
	doctype: 'LMS Certificate',
	url: 'lms.lms.api.get_certification_categories',
	cache: ['certification_categories'],
	auto: user.data ? true : false,
	transform(data) {
		data.unshift({ label: __(' '), value: ' ' })
		return data
	},
})

const updateParticipants = () => {
	updateFilters()
	getMemberCount()
	setQueryParams()

	participants.update({
		filters: filters.value,
	})
	participants.reload()
}

const updateFilters = () => {
	filters.value = {
		...(currentCategory.value.trim('') && {
			category: currentCategory.value,
		}),
		...(nameFilter.value && {
			member_name: ['like', `%${nameFilter.value}%`],
		}),
		...(openToWork.value && {
			open_to_work: true,
		}),
		...(hiring.value && {
			hiring: true,
		}),
	}
}

const setQueryParams = () => {
	let queries = new URLSearchParams(location.search)
	let filterKeys = {
		category: currentCategory.value,
		name: nameFilter.value,
		'open-to-work': openToWork.value,
		hiring: hiring.value,
	}

	Object.keys(filterKeys).forEach((key) => {
		if (filterKeys[key] && hasValue(filterKeys[key])) {
			queries.set(key, filterKeys[key])
		} else {
			queries.delete(key)
		}
	})
	history.replaceState(
		{},
		'',
		`${location.pathname}${queries.size > 0 ? `?${queries.toString()}` : ''}`
	)
}

const hasValue = (value) => {
	if (typeof value === 'string') {
		return value.trim() !== ''
	}
	return true
}

const setFiltersFromQuery = () => {
	let queries = new URLSearchParams(location.search)
	nameFilter.value = queries.get('name') || ''
	currentCategory.value = queries.get('category') || ''
	// Read the key setQueryParams writes; `open-to-opportunities` was never
	// written, so the filter could not survive a reload.
	openToWork.value = queries.get('open-to-work') === 'true'
	hiring.value = queries.get('hiring') === 'true'
}

const breadcrumbs = computed(() => [
	{
		label: __('Certified Members'),
		route: { name: 'CertifiedParticipants' },
	},
])

usePageMeta(() => {
	return {
		title: __('Certified Members'),
		icon: brand.favicon,
	}
})
</script>
