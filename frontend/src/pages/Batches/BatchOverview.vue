<template>
	<div class="p-5 pb-16">
		<div class="flex flex-col items-start gap-8 lg:flex-row">
			<div class="min-w-0 space-y-10 lg:w-[70%]">
				<BatchHeading :batch="batch.data" :doc="doc" :form="form" />
				<div class="w-full lg:hidden">
					<BatchEnrollCardEditor
						v-if="doc"
						:doc="doc"
						:form="form!"
						:studentCount="batch.data.student_count"
					/>
					<BatchOverlay v-else :batch="batch" />
				</div>

				<BatchCourseList
					:batchName="batch.data.name"
					:editable="Boolean(doc)"
					:hideProgress="isStudentView && !batch.data.is_student"
					:category="doc?.category ?? batch.data.category"
				/>

				<BatchSchedule
					v-if="doc || batch.data.is_student"
					:batchName="batch.data.name"
				/>

				<section v-if="doc" class="space-y-3">
					<h2 :id="aboutHeadingId" class="text-3xl-semibold text-ink-gray-9">
						{{ __('About this batch') }}
					</h2>
					<RichTextField
						v-model="doc.batch_details"
						:ariaLabelledby="aboutHeadingId"
						:placeholder="
							__(
								'What learners will do, who it is for and how evaluation works.'
							)
						"
						:missing="form?.isMissing('batch_details')"
					/>
				</section>
				<section v-else-if="batch.data.batch_details" class="space-y-3">
					<h2 class="text-3xl-semibold text-ink-gray-9">
						{{ __('About this batch') }}
					</h2>
					<div
						v-safe-html:rich="batch.data.batch_details"
						class="ProseMirror prose prose-sm max-w-none !whitespace-normal prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2"
					/>
				</section>

				<BatchAssessmentList v-if="doc" :batchName="batch.data.name" />

				<div
					v-if="batch.data.batch_details_raw"
					v-safe-html:rich="batch.data.batch_details_raw"
					class="batch-description"
				/>
			</div>

			<aside
				class="hidden w-full shrink-0 self-start lg:sticky lg:top-5 lg:block lg:w-[30%]"
			>
				<BatchEnrollCardEditor
					v-if="doc"
					:doc="doc"
					:form="form!"
					:studentCount="batch.data.student_count"
				/>
				<BatchOverlay v-else :batch="batch" />
			</aside>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import RichTextField from '@/components/InlineEdit/RichTextField.vue'
import BatchOverlay from '@/pages/Batches/components/BatchOverlay.vue'
import BatchAssessmentList from '@/pages/Batches/components/overview/BatchAssessmentList.vue'
import BatchCourseList from '@/pages/Batches/components/overview/BatchCourseList.vue'
import BatchEnrollCardEditor from '@/pages/Batches/components/overview/BatchEnrollCardEditor.vue'
import BatchHeading from '@/pages/Batches/components/overview/BatchHeading.vue'
import BatchSchedule from '@/pages/Batches/components/overview/BatchSchedule.vue'
import { useStudentView } from '@/composables/useStudentView'
import { injectBatchForm } from '@/pages/Batches/composables/useBatchForm'
import type { BatchDetails, Resource } from '@/types'

/** The batch page. Instructors edit it in place; learners and previews read it. */
defineProps<{ batch: Resource<BatchDetails> }>()

const form = injectBatchForm()
const isStudentView = useStudentView()
const aboutHeadingId = useId()

const doc = computed(() =>
	isStudentView.value ? null : form?.doc.value ?? null
)
</script>
