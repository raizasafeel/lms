<template>
	<SkeletonLoader v-if="!form.resource.doc" variant="form" class="flex-1" />
	<div v-else class="mx-auto w-full max-w-3xl space-y-10 px-5 py-8">
		<CoursePublishSettings />

		<SettingsGroup
			:title="__('Search and sharing')"
			:description="__('How the course shows up in search results.')"
		>
			<SettingRow
				:label="__('Meta description')"
				:summary="
					__('About 150 characters. Leave empty to use the short introduction.')
				"
			>
				<FormControl
					v-model="form.meta.description"
					type="textarea"
					:aria-label="__('Meta description')"
					variant="outline"
					@input="form.markDirty()"
				/>
			</SettingRow>
			<SettingRow
				:label="__('Meta keywords')"
				:summary="__('Comma separated keywords for search engines.')"
			>
				<FormControl
					v-model="form.meta.keywords"
					type="textarea"
					:aria-label="__('Meta keywords')"
					variant="outline"
					@input="form.markDirty()"
				/>
			</SettingRow>
		</SettingsGroup>

		<SettingsGroup v-if="actions" :title="__('Manage')">
			<SettingRow
				v-if="course.data?.published && user.data?.is_moderator"
				:label="__('Unpublish course')"
				:summary="
					__(
						'Hide it from the catalogue. Enrolled learners keep their access and progress.'
					)
				"
			>
				<template #control>
					<Button
						size="sm"
						:loading="actions.publish.loading"
						@click="actions.togglePublish()"
					>
						{{ __('Unpublish') }}
					</Button>
				</template>
			</SettingRow>
			<SettingRow
				:label="__('Export course')"
				:summary="
					__('Download a zip you can import on another Frappe Learning site.')
				"
			>
				<template #control>
					<Button size="sm" @click="actions.exportCourse()">
						{{ __('Export') }}
					</Button>
				</template>
			</SettingRow>
			<SettingRow
				:label="__('Delete course')"
				:summary="
					__(
						'Removes the course, its lessons and learner progress. This cannot be undone.'
					)
				"
				danger
			>
				<template #control>
					<Button
						size="sm"
						theme="red"
						variant="subtle"
						@click="actions.deleteCourse()"
					>
						{{ __('Delete') }}
					</Button>
				</template>
			</SettingRow>
		</SettingsGroup>
	</div>
</template>

<script setup lang="ts">
import { Button, FormControl } from 'frappe-ui'
import { inject } from 'vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import CoursePublishSettings from '@/pages/Courses/CoursePublishSettings.vue'
import { COURSE_ACTIONS } from '@/composables/useCourseActions'
import type {
	CourseDetails,
	CourseFormContext,
	Resource,
	SessionUser,
} from '@/types'

/** The Options tab: settings that have no place on the course page itself. */
defineProps<{ course: Resource<CourseDetails | null> }>()

const form = inject<CourseFormContext>('courseForm')!
const actions = inject(COURSE_ACTIONS, null)
const user = inject<SessionUser>('$user')!
</script>
