<template>
	<HoverCard :hoverDelay="200">
		<template #trigger>
			<slot />
		</template>
		<div class="w-72 space-y-3 p-4" data-testid="instructor-card">
			<div class="flex items-center gap-3">
				<UserAvatar :user="instructor" size="2xl" />
				<span class="truncate text-p-base-medium text-ink-gray-9">
					{{ instructor.full_name }}
				</span>
			</div>
			<p v-if="bio" class="line-clamp-3 text-p-sm text-ink-gray-7">
				{{ bio }}
			</p>
			<Button
				v-if="instructor.username"
				class="w-full"
				:route="{
					name: 'Profile',
					params: { username: instructor.username },
				}"
			>
				{{ __('View profile') }}
			</Button>
		</div>
	</HoverCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, HoverCard } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import { decodeEntities, htmlToText } from '@/utils'
import type { CourseInstructorInfo } from '@/types'

/** An instructor's avatar, name and bio, shown on hovering their name or avatar. */
const props = defineProps<{ instructor: CourseInstructorInfo }>()

const bio = computed(() =>
	htmlToText(decodeEntities(props.instructor.bio || '')).trim()
)
</script>
