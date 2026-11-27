<template>
	<SettingSwitch
		:modelValue="Boolean(doc.paid_course)"
		:label="__('Paid course')"
		:summary="
			doc.paid_course ? __('Learners pay to enroll.') : __('Free to enroll.')
		"
		@update:modelValue="(value) => setPaidCourse(Boolean(value))"
	/>
	<PriceInput
		v-if="doc.paid_course"
		:currency="doc.currency"
		:amount="doc.course_price"
		:missing="isMissing?.('price')"
		class="mb-3.5 rounded-6 border border-outline-gray-2"
		@update:currency="(value) => setField('currency', value)"
		@update:amount="(value) => setField('course_price', value)"
	/>
	<template v-else>
		<SettingSwitch
			:modelValue="Boolean(doc.paid_certificate)"
			:label="__('Paid certificate')"
			:summary="
				doc.paid_certificate
					? __('Learners pay for an evaluated certificate.')
					: __('The certificate is free.')
			"
			@update:modelValue="(value) => setPaidCertificate(Boolean(value))"
		/>
		<PriceInput
			v-if="doc.paid_certificate"
			:currency="doc.currency"
			:amount="doc.course_price"
			:missing="isMissing?.('price')"
			class="mb-3.5 rounded-6 border border-outline-gray-2"
			@update:currency="(value) => setField('currency', value)"
			@update:amount="(value) => setField('course_price', value)"
		/>
	</template>
</template>

<script setup lang="ts">
import { toast } from 'frappe-ui'
import { computed, inject } from 'vue'
import PriceInput from '@/components/InlineEdit/PriceInput.vue'
import SettingSwitch from '@/components/InlineEdit/SettingSwitch.vue'
import { useSettings } from '@/stores/settings'
import type { CourseFormContext } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

/** The course's regular price, or for a free course, its certificate's. */
const { resource, markDirty, isMissing } =
	inject<CourseFormContext>('courseForm')!

const doc = computed(() => resource.doc!)

function setField(field: keyof LMSCourse, value: unknown): void {
	;(doc.value as Record<string, unknown>)[field] = value
	markDirty()
}

// Same rule as the course page's card: selling needs the Payments app, and a
// paid course includes its certificate.
function canSell(): boolean {
	const settings = useSettings().settings?.data
	if (settings && !settings.is_payments_app_installed) {
		toast.error(__('Install the Payments app to sell courses.'))
		return false
	}
	return true
}

function setPaidCourse(paid: boolean): void {
	if (paid && !canSell()) return
	doc.value.paid_course = paid ? 1 : 0
	if (paid) doc.value.paid_certificate = 0
	markDirty()
}

// A sold certificate is the evaluated one, as in the Evaluations switch.
function setPaidCertificate(paid: boolean): void {
	if (paid && !canSell()) return
	doc.value.paid_certificate = paid ? 1 : 0
	if (paid) doc.value.enable_certification = 0
	markDirty()
}
</script>
