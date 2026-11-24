<template>
	<Button
		v-if="details?.certificate"
		:route="{
			name: 'CertificateVerification',
			params: { certificateId: details.certificate.name },
		}"
	>
		<template #prefix>
			<span class="lucide-graduation-cap size-4" />
		</template>
		{{ __('View Certificate') }}
	</Button>
	<div
		v-else-if="
			details?.membership &&
			details.paid_certificate &&
			(preview || user.data?.is_student)
		"
	>
		<Button
			v-if="!details.membership.purchased_certificate"
			:variant="price ? 'solid' : 'subtle'"
			:route="{
				name: 'Billing',
				params: {
					type: 'certificate',
					name: courseName,
				},
				query: studentViewQuery(preview ?? null),
			}"
			class="w-full"
		>
			<template #prefix>
				<span class="lucide-graduation-cap size-4" />
			</template>
			{{
				price ? __('Buy certificate · {0}').format(price) : __('Get Certified')
			}}
		</Button>
		<Button
			v-else-if="!details.membership.certificate"
			:route="{
				name: 'CourseCertification',
				params: {
					courseName: courseName,
				},
			}"
			class="w-full"
		>
			<template #prefix>
				<span class="lucide-graduation-cap size-4" />
			</template>
			{{ __('Get Certified') }}
		</Button>
	</div>
</template>
<script setup lang="ts">
import { Button, createResource } from 'frappe-ui'
import { computed, inject } from 'vue'
import {
	studentViewQuery,
	type StudentViewMode,
} from '@/composables/useStudentView'
import type { CertificationInfo, Resource, SessionUser } from '@/types'

const user = inject<SessionUser>('$user')!

const props = defineProps<{
	courseName: string
	/** Shown on the buy button when the certificate is sold on its own. */
	price?: string
	/** Student view: shows the links a learner in that state would see. */
	preview?: StudentViewMode | null
}>()

const certification = createResource({
	url: 'lms.lms.api.get_certification_details',
	makeParams() {
		return {
			course: props.courseName,
		}
	},
	auto: user.data ? true : false,
}) as Resource<CertificationInfo | null>

// A previewing instructor is no real enrolled learner, so act as a fresh one.
const details = computed(() =>
	props.preview === 'enrolled' && certification.data
		? { ...certification.data, certificate: null, membership: {} }
		: certification.data
)
</script>
