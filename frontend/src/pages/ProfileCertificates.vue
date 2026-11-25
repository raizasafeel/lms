<template>
	<div class="mt-7 mb-10">
		<div class="mb-3 flex items-center gap-2">
			<h2 class="text-lg-semibold text-ink-gray-9">
				{{ __('Certificates') }}
			</h2>
			<span v-if="certificates.data?.length" class="text-lg text-ink-gray-6">
				{{ certificates.data.length }}
			</span>
		</div>
		<span class="sr-only" role="status">{{ loadingAnnouncement }}</span>
		<div
			v-if="isPending"
			class="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @4xl:grid-cols-3"
			data-testid="certificates-skeleton"
		>
			<ProfileCertificateCardSkeleton v-for="i in 3" :key="i" />
		</div>
		<div
			v-else-if="certificates.data?.length"
			class="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @4xl:grid-cols-3"
		>
			<div
				v-for="certificate in certificates.data"
				:key="certificate.name"
				class="flex flex-col overflow-hidden rounded-6 border border-outline-gray-2 hover:border-outline-gray-3"
			>
				<router-link
					:to="certificateRoute(certificate.name)"
					class="flex justify-center border-b border-outline-gray-1 bg-surface-gray-1 p-3"
					:aria-label="__('View certificate: {0}').format(titleOf(certificate))"
				>
					<CertificateThumbnail
						:certificate="certificate.name"
						:title="titleOf(certificate)"
						class="w-64 max-w-full"
					/>
				</router-link>
				<div class="flex flex-1 flex-col gap-1.5 p-3">
					<router-link
						:to="certificateRoute(certificate.name)"
						class="line-clamp-2 font-medium leading-5 text-ink-gray-9"
					>
						{{ titleOf(certificate) }}
					</router-link>
					<div class="text-p-sm text-ink-gray-6">
						{{ certificate.course ? __('Course') : __('Batch') }} ·
						{{
							__('Issued {0}').format(
								formatCertificateDate(certificate.issue_date)
							)
						}}
					</div>
					<div v-if="!certificate.published" class="mt-1 flex">
						<Badge theme="gray" variant="outline" size="sm">
							<template #prefix>
								<span class="lucide-eye-off size-2.5" aria-hidden="true" />
							</template>
							{{ __('Not published') }}
						</Badge>
					</div>
				</div>
				<div class="flex items-center gap-2 px-3 pb-3">
					<Button
						size="sm"
						:label="__('View')"
						:route="certificateRoute(certificate.name)"
					/>
					<span class="flex-1" />
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-download"
						:label="__('Download PDF')"
						:tooltip="__('Download PDF')"
						@click="downloadCertificate(certificate.name)"
					/>
					<Button
						v-if="certificate.published"
						size="sm"
						variant="ghost"
						icon="lucide-link"
						:label="__('Copy link')"
						:tooltip="__('Copy link')"
						@click="copyLink(certificate.name)"
					/>
				</div>
			</div>
		</div>
		<div v-else class="text-sm italic text-ink-gray-6">
			{{ __('You have not received any certificates yet.') }}
		</div>
	</div>
</template>
<script setup>
import { Badge, Button, createResource } from 'frappe-ui'
import { computed, onMounted } from 'vue'
import CertificateThumbnail from '@/components/Certificates/CertificateThumbnail.vue'
import ProfileCertificateCardSkeleton from '@/components/Skeletons/ProfileCertificateCardSkeleton.vue'
import { useLoadingAnnouncement } from '@/utils/a11y'
import {
	downloadCertificate,
	formatCertificateDate,
	useCopyCertificateLink,
} from '@/utils/certificates'

const props = defineProps({
	profile: {
		type: Object,
		required: true,
	},
})

const copyLink = useCopyCertificateLink()

onMounted(() => {
	if (props.profile.data?.username) {
		certificates.reload()
	}
})

const certificates = createResource({
	url: 'lms.lms.api.get_user_certificates',
	params: {
		username: props.profile.data?.username,
	},
	cache: ['certificates', props.profile.data?.username],
})

const isPending = computed(() => !certificates.data && !certificates.error)

const loadingAnnouncement = useLoadingAnnouncement(
	() => isPending.value,
	() => (certificates.data ? __('Certificates loaded') : '')
)

const titleOf = (certificate) =>
	certificate.course_title || certificate.batch_title

const certificateRoute = (name) => ({
	name: 'CertificateVerification',
	params: { certificateId: name },
})
</script>
