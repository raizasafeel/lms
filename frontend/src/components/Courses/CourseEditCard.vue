<template>
	<div
		class="w-full overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-base"
	>
		<div class="p-2 pb-0">
			<CourseThumbnailField />
		</div>
		<div class="space-y-4 p-5">
			<div class="space-y-2">
				<Dropdown :options="priceOptions" align="start">
					<button
						type="button"
						class="-mx-1 flex items-center gap-1 rounded-3 px-1 text-3xl-semibold text-ink-gray-9 hover:bg-surface-gray-2"
						:aria-label="__('Course price')"
					>
						{{ doc.paid_course ? __('Paid') : __('Free') }}
						<span class="lucide-chevron-down size-4 text-ink-gray-5" />
					</button>
				</Dropdown>
				<CoursePriceRow v-if="doc.paid_course" />
			</div>
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
import { Button, Dialog, Dropdown } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import CourseCertificateBox from '@/components/Courses/CourseCertificateBox.vue'
import CourseIncludes from '@/components/Courses/CourseIncludes.vue'
import CoursePriceRow from '@/components/Courses/CoursePriceRow.vue'
import CourseThumbnailField from '@/components/Courses/CourseThumbnailField.vue'
import { useSettings } from '@/stores/settings'
import type { CourseDetails, CourseFormContext, Resource } from '@/types'
import { openExternal } from '@/utils/openExternal'

/** The enrol card as instructors edit it: learners see the same card. */
defineProps<{ course: Resource<CourseDetails | null> }>()

const { resource, markDirty } = inject<CourseFormContext>('courseForm')!
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

const priceOptions = computed(() => [
	{
		label: __('Free'),
		icon: doc.value.paid_course ? undefined : 'lucide-check',
		onClick: () => setPaidCourse(false),
	},
	{
		label: __('Paid'),
		icon: doc.value.paid_course ? 'lucide-check' : undefined,
		onClick: () => setPaidCourse(true),
	},
])

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
