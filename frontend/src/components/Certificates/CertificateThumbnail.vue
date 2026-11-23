<template>
	<div ref="root" class="leading-[0] shadow-sm ring-1 ring-outline-gray-1">
		<CertificatePreview
			:html="certificate.data?.html ?? null"
			:title="title"
			:loading="!certificate.data && !certificate.error"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { createResource } from 'frappe-ui'
import { useIntersectionObserver } from '@vueuse/core'
import CertificatePreview from '@/components/CertificatePreview.vue'
import type { Resource } from '@/types'
import type { CertificateDetails } from '@/utils/certificates'

const props = defineProps<{
	certificate: string
	title: string
}>()

const root = ref<HTMLElement | null>(null)

// A certificate's HTML carries its fonts, so a card fetches it only once it scrolls into view.
const certificate = createResource({
	url: 'lms.lms.api.get_certificate',
	params: { certificate: props.certificate },
	cache: ['certificate', props.certificate],
}) as Resource<CertificateDetails | null>

const { stop } = useIntersectionObserver(root, ([entry]) => {
	if (!entry?.isIntersecting) return
	stop()
	if (!certificate.data) certificate.fetch()
})
</script>
