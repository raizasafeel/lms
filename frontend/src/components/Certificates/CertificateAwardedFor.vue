<template>
	<section class="space-y-3">
		<h2 class="text-lg-semibold text-ink-gray-9">
			{{ kind === 'batch' ? __('About the batch') : __('About the course') }}
		</h2>
		<router-link
			:to="route"
			class="grid w-full gap-4 rounded-6 border border-outline-gray-2 p-3 text-start hover:border-outline-gray-3 @lg:grid-cols-[13rem_minmax(0,1fr)]"
		>
			<img
				v-if="awardedFor.image"
				:src="safeUrl(awardedFor.image)"
				alt=""
				class="aspect-video w-full rounded-4 object-cover"
			/>
			<div
				v-else
				class="flex aspect-video items-center justify-center rounded-4 bg-surface-gray-2 px-3 text-center text-lg-semibold text-ink-gray-6"
			>
				{{ awardedFor.title }}
			</div>
			<div class="flex min-w-0 flex-col gap-2">
				<Badge
					v-if="awardedFor.category"
					theme="gray"
					size="sm"
					class="self-start"
				>
					{{ awardedFor.category }}
				</Badge>
				<div class="text-base-semibold text-ink-gray-9">
					{{ awardedFor.title }}
				</div>
				<p
					v-if="awardedFor.description"
					class="line-clamp-2 text-p-sm text-ink-gray-7"
				>
					{{ awardedFor.description }}
				</p>
				<div v-if="evaluator" class="mt-1 flex items-center gap-2">
					<Avatar :label="evaluator" size="xs" />
					<span class="text-p-sm text-ink-gray-7">
						{{ __('Evaluated by {0}').format(evaluator) }}
					</span>
				</div>
			</div>
		</router-link>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, Badge } from 'frappe-ui'
import { safeUrl } from '@/utils/safeUrl'
import type { CertificateAwardedFor } from '@/utils/certificates'

const props = defineProps<{
	kind: 'course' | 'batch'
	awardedFor: CertificateAwardedFor
	evaluator: string | null
}>()

const route = computed(() =>
	props.kind === 'batch'
		? { name: 'BatchDetail', params: { batchName: props.awardedFor.name } }
		: { name: 'CourseDetail', params: { courseName: props.awardedFor.name } }
)
</script>
