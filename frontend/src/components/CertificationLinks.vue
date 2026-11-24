<template>
	<Button
		v-if="certification.data && certification.data.certificate"
		:route="{
			name: 'CertificateVerification',
			params: { certificateId: certification.data.certificate.name },
		}"
	>
		<template #prefix>
			<span class="lucide-graduation-cap size-4" />
		</template>
		{{ __('View Certificate') }}
	</Button>
	<div
		v-else-if="
			certification.data &&
			certification.data.membership &&
			certification.data.paid_certificate &&
			user.data?.is_student
		"
	>
		<Button
			v-if="!certification.data.membership.purchased_certificate"
			:variant="price ? 'solid' : 'subtle'"
			:route="{
				name: 'Billing',
				params: {
					type: 'certificate',
					name: courseName,
				},
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
			v-else-if="!certification.data.membership.certificate"
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
import { inject } from 'vue'
import type { CertificationInfo, Resource, SessionUser } from '@/types'

const user = inject<SessionUser>('$user')!

const props = defineProps<{
	courseName: string
	/** Shown on the buy button when the certificate is sold on its own. */
	price?: string
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
</script>
