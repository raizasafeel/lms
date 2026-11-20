<template>
	<div class="flex min-h-full flex-col">
		<PageHeader :breadcrumbs="breadcrumbs" />
		<div
			v-if="details"
			class="mx-auto grid w-full max-w-6xl items-start gap-8 px-5 py-6 @4xl:grid-cols-[minmax(0,1fr)_20rem]"
		>
			<div class="flex min-w-0 flex-col gap-6">
				<div class="space-y-2">
					<div class="flex flex-wrap items-center gap-2">
						<Badge :theme="status.theme" size="md">
							<template #prefix>
								<span :class="[status.icon, 'size-3']" aria-hidden="true" />
							</template>
							{{ status.label }}
						</Badge>
						<span class="text-p-sm text-ink-gray-6">
							{{
								details.kind === 'batch'
									? __('Batch certificate')
									: __('Course certificate')
							}}
						</span>
					</div>
					<h1 class="text-3xl-semibold text-ink-gray-9">{{ details.title }}</h1>
					<p class="text-p-base text-ink-gray-7">
						{{
							__('Awarded to {0} by {1} on {2}.').format(
								details.member.full_name,
								details.issued_by,
								dayjs(details.issue_date).format('D MMMM YYYY')
							)
						}}
					</p>
				</div>
				<div
					class="flex justify-center rounded-6 border border-outline-gray-1 bg-surface-gray-1 p-4 sm:p-8"
				>
					<div
						class="w-full max-w-[600px] leading-[0] shadow-lg ring-1 ring-outline-gray-1"
					>
						<CertificatePreview :html="details.html" :title="details.title" />
					</div>
				</div>
				<CertificateAwardedFor
					v-if="details.awarded_for"
					:kind="details.kind"
					:awarded-for="details.awarded_for"
					:evaluator="details.evaluator_name"
				/>
			</div>
			<aside class="flex flex-col gap-3 @4xl:sticky @4xl:top-16">
				<CertificateValidityCard :certificate="details" />
				<component
					:is="memberRoute ? 'router-link' : 'div'"
					:to="memberRoute"
					class="flex items-center gap-3 rounded-6 border border-outline-gray-2 p-3 text-start"
					:class="{ 'hover:border-outline-gray-3': memberRoute }"
				>
					<Avatar
						:label="details.member.full_name"
						:image="details.member.user_image ?? undefined"
						size="xl"
					/>
					<div class="min-w-0 flex-1">
						<div class="truncate font-semibold text-ink-gray-9">
							{{ details.member.full_name }}
						</div>
						<div
							v-if="details.member.headline"
							class="truncate text-sm text-ink-gray-7"
						>
							{{ details.member.headline }}
						</div>
					</div>
					<span
						v-if="memberRoute"
						class="lucide-chevron-right size-4 text-ink-gray-5"
						aria-hidden="true"
					/>
				</component>
			</aside>
		</div>
		<div
			v-else-if="certificate.error"
			class="flex flex-1 items-center justify-center px-6 py-24"
		>
			<div class="flex max-w-md flex-col items-center gap-3 text-center">
				<span
					class="lucide-search-x size-7 text-ink-gray-5"
					aria-hidden="true"
				/>
				<h1 class="text-lg-medium text-ink-gray-8">{{ missing.title }}</h1>
				<p class="text-p-base text-ink-gray-6">{{ missing.description }}</p>
				<Button
					icon-left="lucide-book-open"
					:label="__('Browse courses')"
					:route="{ name: 'Courses' }"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, Badge, Button, createResource, usePageMeta } from 'frappe-ui'
import CertificatePreview from '@/components/CertificatePreview.vue'
import CertificateAwardedFor from '@/components/Certificates/CertificateAwardedFor.vue'
import CertificateValidityCard from '@/components/Certificates/CertificateValidityCard.vue'
import PageHeader from '@/components/Layouts/pages/PageHeader.vue'
import { sessionStore } from '@/stores/session'
import dayjs from '@/utils/dayjs'
import { profileRoute } from '@/utils/routes'
import type { Resource } from '@/types'
import type { CertificateDetails } from '@/utils/certificates'

const props = defineProps<{ certificateId: string }>()

const { brand } = sessionStore()

const certificate = createResource({
	url: 'lms.lms.api.get_certificate',
	makeParams: () => ({ certificate: props.certificateId }),
	cache: ['certificate', props.certificateId],
	auto: true,
}) as Resource<CertificateDetails | null>

const details = computed(() => certificate.data)

const STATUSES = {
	valid: { theme: 'green', icon: 'lucide-badge-check', label: __('Verified') },
	expired: { theme: 'amber', icon: 'lucide-clock', label: __('Expired') },
	unpublished: {
		theme: 'gray',
		icon: 'lucide-eye-off',
		label: __('Not published'),
	},
} as const

const status = computed(() => STATUSES[details.value?.status ?? 'valid'])

const memberRoute = computed(() =>
	profileRoute(details.value?.member.username, 'ProfileCertificates')
)

const missing = computed(() => {
	const error = certificate.error as { exc_type?: string } | null
	if (error?.exc_type === 'PermissionError') {
		return {
			title: __('Certificate unavailable'),
			description: __('This certificate is not published yet.'),
		}
	}
	return {
		title: __('Certificate not found'),
		description: __(
			'No certificate on {0} has this ID. Check that the link was copied in full.'
		).format(brand.name || __('this site')),
	}
})

const breadcrumbs = computed(() => [
	{
		label: __('Certified members'),
		route: { name: 'CertifiedParticipants' },
	},
	{
		label: props.certificateId,
		route: {
			name: 'CertificateVerification',
			params: { certificateId: props.certificateId },
		},
	},
])

usePageMeta(() => ({
	title: details.value?.title || __('Certificate'),
	icon: brand.favicon,
}))
</script>
