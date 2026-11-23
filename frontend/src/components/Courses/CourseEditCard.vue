<template>
	<div
		class="w-full overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-base"
	>
		<div class="p-2 pb-0">
			<ImageField
				swatches
				:image="doc.image"
				:videoLink="doc.video_link"
				:tint="doc.card_gradient"
				@update:image="(value) => setField('image', value)"
				@update:videoLink="(value) => setField('video_link', value)"
				@update:tint="(value) => setField('card_gradient', value)"
			/>
		</div>
		<div class="space-y-4 p-5">
			<PriceField
				:paid="Boolean(doc.paid_course)"
				:currency="doc.currency"
				:amount="doc.course_price"
				:label="__('Course price')"
				:missing="isMissing?.('price')"
				@update:paid="setPaidCourse"
				@update:currency="(value) => setField('currency', value)"
				@update:amount="(value) => setField('course_price', value)"
			/>
			<div class="space-y-2">
				<Button variant="solid" size="md" class="w-full" disabled>
					<template #prefix>
						<span
							class="size-4"
							:class="
								doc.paid_course ? 'lucide-credit-card' : 'lucide-book-text'
							"
						/>
					</template>
					{{ doc.paid_course ? __('Buy this course') : __('Start learning') }}
				</Button>
				<p class="text-center text-p-xs text-ink-gray-6">
					{{
						doc.disable_self_learning
							? __('Self enrollment is off, so you enroll learners yourself.')
							: __('Learners see this button.')
					}}
				</p>
			</div>
			<CourseCertificateBox
				:paymentsAppMissing="paymentsAppMissing"
				@needsPayments="showPaymentsAppModal = true"
			/>
			<div class="border-t border-outline-gray-1 pt-4">
				<CourseIncludes
					:enrollments="doc.enrollments"
					:lessons="course.data?.lessons"
					:quizzes="course.data?.quiz_count"
					:hasVideo="Boolean(doc.video_link)"
					:certificate="certificate"
				/>
			</div>
		</div>
	</div>

	<Dialog
		v-model:open="showPaymentsAppModal"
		:title="__('Payments app required')"
		:actions="[
			{
				label: __('Get the Payments app'),
				variant: 'solid',
				onClick: ({ close }: { close: () => void }) => {
					openExternal('https://frappecloud.com/marketplace/apps/payments')
					close()
				},
			},
		]"
	>
		<template #default>
			<p class="text-p-base text-ink-gray-7">
				{{
					__(
						'Selling a paid course or certificate needs the Payments app. Install it from the Frappe Marketplace, then turn on pricing here.'
					)
				}}
			</p>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import CourseCertificateBox from '@/components/Courses/CourseCertificateBox.vue'
import CourseIncludes from '@/components/Courses/CourseIncludes.vue'
import ImageField from '@/components/InlineEdit/ImageField.vue'
import PriceField from '@/components/InlineEdit/PriceField.vue'
import { useSettings } from '@/stores/settings'
import type { CourseDetails, CourseFormContext, Resource } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'
import { openExternal } from '@/utils/openExternal'

/** The enrol card as instructors edit it: learners see the same card. */
defineProps<{ course: Resource<CourseDetails | null> }>()

const { resource, markDirty, isMissing } =
	inject<CourseFormContext>('courseForm')!
const settingsStore = useSettings()

const doc = computed(() => resource.doc!)
const showPaymentsAppModal = ref<boolean>(false)

// Blocks only when the app is known to be missing; the server is the hard guard.
const paymentsAppMissing = computed<boolean>(
	() =>
		Boolean(settingsStore.settings?.data) &&
		!settingsStore.settings.data.is_payments_app_installed
)

const certificate = computed<'free' | 'paid' | null>(() => {
	if (doc.value.paid_certificate) return 'paid'
	return doc.value.enable_certification ? 'free' : null
})

function setField(field: keyof LMSCourse, value: unknown): void {
	;(doc.value as Record<string, unknown>)[field] = value
	markDirty()
}

function setPaidCourse(paid: boolean): void {
	if (paid && paymentsAppMissing.value) {
		showPaymentsAppModal.value = true
		return
	}
	doc.value.paid_course = paid ? 1 : 0
	// The paid-certificate flow applies only to free courses.
	if (paid) doc.value.paid_certificate = 0
	markDirty()
}
</script>
