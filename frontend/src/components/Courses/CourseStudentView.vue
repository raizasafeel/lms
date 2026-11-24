<template>
	<div class="flex min-h-full flex-col">
		<PageHeader :breadcrumbs="breadcrumbs">
			<template #actions>
				<HeaderButton
					variant="outline"
					icon="lucide-x"
					:label="__('Exit student view')"
					@click="emit('exit')"
				/>
			</template>
		</PageHeader>
		<StudentViewBar
			belowHeader
			v-model="mode"
			doctype="LMS Course"
			:name="course.data?.name ?? ''"
			@change="refresh"
		/>
		<CourseOverview
			:key="version"
			:course="course"
			:preview="mode"
			@enroll="mode = 'enrolled'"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HeaderButton from '@/components/HeaderButton.vue'
import PageHeader from '@/components/Layouts/pages/PageHeader.vue'
import StudentViewBar from '@/components/StudentViewBar.vue'
import CourseOverview from '@/pages/Courses/CourseOverview.vue'
import type { Breadcrumb, CourseDetails, Resource } from '@/types'

type PreviewMode = 'not-enrolled' | 'enrolled'

/** The course page as a learner sees it, before and after enrolling. */
const props = defineProps<{
	course: Resource<CourseDetails | null>
	breadcrumbs: Breadcrumb[]
}>()
const emit = defineEmits<{ exit: [] }>()

const mode = defineModel<PreviewMode>({ default: 'not-enrolled' })

// Remounts the overview so its outline and progress refetch.
const version = ref(0)

function refresh(): void {
	props.course.reload()
	version.value++
}
</script>
