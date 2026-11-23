<template>
	<div class="space-y-4 rounded-6 border border-outline-gray-2 p-4">
		<div class="flex items-start gap-2.5">
			<span
				:class="[validity.icon, 'mt-0.5 size-5 shrink-0']"
				aria-hidden="true"
			/>
			<div>
				<div class="text-base-semibold text-ink-gray-9">
					{{ validity.title }}
				</div>
				<p class="text-p-sm text-ink-gray-6">{{ validity.description }}</p>
			</div>
		</div>
		<dl class="space-y-2.5 border-t border-outline-gray-1 pt-4">
			<div
				v-for="[label, value] in rows"
				:key="label"
				class="flex items-baseline gap-3"
			>
				<dt class="w-24 shrink-0 text-p-sm text-ink-gray-6">{{ label }}</dt>
				<dd
					class="min-w-0 flex-1 break-words text-p-sm text-ink-gray-8"
					:class="{ 'font-mono': label === __('Certificate ID') }"
				>
					{{ value }}
				</dd>
			</div>
		</dl>
		<div class="space-y-2 border-t border-outline-gray-1 pt-4">
			<Button
				variant="solid"
				class="w-full"
				icon-left="lucide-download"
				:label="__('Download PDF')"
				@click="downloadCertificate(certificate.name)"
			/>
			<Dropdown
				v-if="certificate.status !== 'unpublished'"
				class="w-full"
				:options="shareOptions"
			>
				<Button
					class="w-full"
					icon-left="lucide-share-2"
					icon-right="lucide-chevron-down"
					:label="__('Share')"
				/>
			</Dropdown>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dropdown } from 'frappe-ui'
import { openExternal } from '@/utils/openExternal'
import {
	downloadCertificate,
	emailShareUrl,
	formatCertificateDate,
	linkedInShareUrl,
	useCopyCertificateLink,
} from '@/utils/certificates'
import type { CertificateDetails } from '@/utils/certificates'

const props = defineProps<{ certificate: CertificateDetails }>()

const copyLink = useCopyCertificateLink()

const validity = computed(() => {
	const { status, issued_by, expiry_date, is_member } = props.certificate
	if (status === 'valid') {
		return {
			icon: 'lucide-shield-check text-ink-green-6',
			title: __('Valid certificate'),
			description: __('These details match {0}’s records.').format(issued_by),
		}
	}
	if (status === 'expired') {
		return {
			icon: 'lucide-shield-alert text-ink-amber-6',
			title: __('Verified, but expired'),
			description: __(
				'Issued by {0}, expired on {1}. It no longer counts as current.'
			).format(issued_by, formatCertificateDate(expiry_date!)),
		}
	}
	return {
		icon: 'lucide-shield-alert text-ink-amber-6',
		title: is_member ? __('Only you can see this') : __('Not published'),
		description: is_member
			? __(
					'It isn’t on your profile yet, so a shared link shows it as unavailable.'
			  )
			: __('Only its owner and staff can see it until it is published.'),
	}
})

const rows = computed<[string, string][]>(() => {
	const certificate = props.certificate
	const expired = certificate.status === 'expired'
	return [
		[__('Certificate ID'), certificate.name],
		[__('Awarded to'), certificate.member.full_name],
		[__('Issued on'), formatCertificateDate(certificate.issue_date)],
		[
			expired ? __('Expired on') : __('Valid till'),
			certificate.expiry_date
				? formatCertificateDate(certificate.expiry_date)
				: __('No expiry'),
		],
		...(certificate.evaluator_name
			? [[__('Evaluator'), certificate.evaluator_name] as [string, string]]
			: []),
		[__('Issued by'), certificate.issued_by],
	]
})

const shareOptions = computed(() => [
	{
		label: __('Copy link'),
		icon: 'lucide-link',
		onClick: () => copyLink(props.certificate.name),
	},
	{
		label: __('Share on LinkedIn'),
		icon: 'lucide-square-arrow-out-up-right',
		onClick: () => openExternal(linkedInShareUrl(props.certificate.name)),
	},
	{
		label: __('Email'),
		icon: 'lucide-mail',
		onClick: () => {
			window.location.href = emailShareUrl(
				props.certificate.name,
				props.certificate.title
			)
		},
	},
])
</script>
