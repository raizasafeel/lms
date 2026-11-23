<template>
	<div class="p-5 pb-16">
		<div class="flex flex-col items-start gap-8 lg:flex-row">
			<div class="min-w-0 space-y-10 lg:w-[70%]">
				<BatchHeading :batch="batch.data" :doc="doc" :form="form" />
				<div class="w-full lg:hidden">
					<BatchEnrollCardEditor v-if="doc" :doc="doc" :form="form!" />
					<BatchOverlay v-else :batch="batch" />
				</div>

				<BatchCourseList
					:batchName="batch.data.name"
					:editable="Boolean(doc)"
				/>

				<section v-if="doc" class="space-y-3">
					<h2 :id="aboutHeadingId" class="text-3xl-semibold text-ink-gray-9">
						{{ __('About this batch') }}
					</h2>
					<div
						class="-mx-2.5 rounded-5 px-2.5 py-1.5 hover:bg-surface-gray-2 focus-within:hover:bg-transparent"
						:class="
							form?.isMissing('batch_details') &&
							'bg-surface-red-1 ring-2 ring-outline-red-3'
						"
					>
						<RichTextEditor
							:ariaLabelledby="aboutHeadingId"
							:content="doc.batch_details"
							variant="ghost"
							:placeholder="
								__(
									'What learners will do, who it is for and how evaluation works.'
								)
							"
							minHeight="5rem"
							@change="(value: string) => (doc!.batch_details = value)"
						/>
					</div>
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

				<section v-if="doc">
					<Assessments :batch="batch.data.name" :can-manage="true" />
				</section>

				<div
					v-if="batch.data.batch_details_raw"
					v-safe-html:rich="batch.data.batch_details_raw"
					class="batch-description"
				/>
			</div>

			<aside
				class="hidden w-full shrink-0 self-start lg:sticky lg:top-5 lg:block lg:w-[30%]"
			>
				<BatchEnrollCardEditor v-if="doc" :doc="doc" :form="form!" />
				<BatchOverlay v-else :batch="batch" />
			</aside>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import Assessments from '@/pages/Batches/components/Assessments.vue'
import BatchOverlay from '@/pages/Batches/components/BatchOverlay.vue'
import BatchCourseList from '@/pages/Batches/components/overview/BatchCourseList.vue'
import BatchEnrollCardEditor from '@/pages/Batches/components/overview/BatchEnrollCardEditor.vue'
import BatchHeading from '@/pages/Batches/components/overview/BatchHeading.vue'
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
