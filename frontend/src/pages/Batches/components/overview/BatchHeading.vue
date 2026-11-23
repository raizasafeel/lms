<template>
	<section class="space-y-4">
		<InlineText
			v-if="doc"
			v-model="doc.title"
			:placeholder="__('Batch title')"
			:missing="form?.isMissing('title')"
			class="text-4xl-semibold text-ink-gray-9"
			@enter="descriptionField?.focus()"
		/>
		<h1 v-else class="text-4xl-semibold text-ink-gray-9">
			{{ batch.title }}
		</h1>

		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-ink-gray-7">
			<div v-if="doc" class="flex items-center gap-1">
				<span class="lucide-tag size-4 shrink-0" />
				<Link
					v-model="doc.category"
					doctype="LMS Category"
					:placeholder="__('Add category')"
					:aria-label="__('Category')"
					:inlineCreate="true"
					inlineCreatePlaceholder="Category name"
					:onCreate="onCreateCategory"
					variant="ghost"
					class="w-40"
				/>
			</div>
			<span
				v-else-if="batch.category"
				class="flex items-center gap-1.5 font-medium"
			>
				<span class="lucide-tag size-4" />
				{{ batch.category }}
			</span>
			<span
				v-if="doc || batch.category || batch.instructors?.length"
				class="lucide-dot size-5"
			/>
			<BatchInstructorsField
				v-if="doc && batch.can_change_instructors"
				v-model="form!.instructors.value"
				:missing="form?.isMissing('instructors')"
			/>
			<div v-else-if="batch.instructors?.length" class="flex items-center">
				<span
					class="h-6 me-1"
					:class="{ 'avatar-group overlap': batch.instructors.length > 1 }"
				>
					<UserAvatar
						v-for="instructor in batch.instructors"
						:key="instructor.username"
						:user="instructor"
					/>
				</span>
				<CourseInstructors :instructors="batch.instructors" />
			</div>
			<template v-if="batch.student_count">
				<span class="lucide-dot size-5" />
				<span class="flex items-center gap-1.5">
					<span class="lucide-users-round size-4" />
					{{ __('{0} enrolled').format(batch.student_count) }}
				</span>
			</template>
		</div>

		<InlineText
			v-if="doc"
			ref="descriptionField"
			v-model="doc.description"
			:placeholder="
				__(
					'Short description: one line on who this batch is for and what they leave with'
				)
			"
			:missing="form?.isMissing('description')"
			class="leading-6 text-ink-gray-7"
		/>
		<p v-else-if="batch.description" class="leading-6 text-ink-gray-7">
			{{ batch.description }}
		</p>
	</section>
</template>

<script setup lang="ts">
import { useTemplateRef } from 'vue'
import { createLMSCategory } from '@/utils'
import { createHandler } from '@/utils/createHandler'
import Link from '@/components/Controls/Link.vue'
import CourseInstructors from '@/components/CourseInstructors.vue'
import InlineText from '@/components/Courses/InlineText.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import BatchInstructorsField from '@/pages/Batches/components/overview/BatchInstructorsField.vue'
import type { BatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** Title, meta row and short description: inline fields when `doc` is set. */
const props = defineProps<{
	batch: Record<string, any>
	doc: LMSBatch | null
	form: BatchForm | null
}>()

const descriptionField = useTemplateRef<{ focus: () => void }>(
	'descriptionField'
)

function onCreateCategory(value: string | null, done?: () => void): void {
	createHandler(value, done, (name) =>
		createLMSCategory(name).then((category: string | undefined) => {
			if (!category || !props.doc) return
			props.doc.category = category
			done?.()
		})
	)
}
</script>
