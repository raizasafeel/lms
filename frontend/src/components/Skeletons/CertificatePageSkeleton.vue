<template>
	<div
		class="mx-auto grid w-full max-w-6xl items-start gap-8 px-5 py-6 motion-safe:animate-pulse @4xl:grid-cols-[minmax(0,1fr)_20rem]"
		aria-hidden="true"
	>
		<div class="flex min-w-0 flex-col gap-6">
			<div class="space-y-2">
				<div class="flex items-center gap-2">
					<div class="h-5 w-20 rounded-4 bg-surface-gray-2" />
					<SkeletonText width="w-28" class="w-28" />
				</div>
				<SkeletonText text="text-3xl-semibold" width="w-2/3" strong />
				<SkeletonText text="text-p-base" width="w-1/2" />
			</div>
			<div
				class="flex justify-center rounded-6 border border-outline-gray-1 bg-surface-gray-1 p-4 sm:p-8"
			>
				<div
					class="aspect-[1122/793] w-full max-w-[600px] bg-surface-gray-2 ring-1 ring-outline-gray-1"
				/>
			</div>
		</div>
		<div class="flex flex-col gap-3">
			<div class="space-y-4 rounded-6 border border-outline-gray-2 p-4">
				<div class="flex items-start gap-2.5">
					<div class="mt-0.5 size-5 shrink-0 rounded-full bg-surface-gray-2" />
					<div class="flex-1">
						<SkeletonText text="text-base-semibold" width="w-24" strong />
						<SkeletonText :lines="2" />
					</div>
				</div>
				<div class="space-y-2.5 border-t border-outline-gray-1 pt-4">
					<div v-for="i in 5" :key="i" class="flex gap-3">
						<SkeletonText width="w-16" class="w-24 shrink-0" />
						<SkeletonText
							:text="i === 1 ? 'text-p-sm font-mono' : 'text-p-sm'"
							width="w-2/3"
							class="flex-1"
						/>
					</div>
				</div>
				<div class="space-y-2 border-t border-outline-gray-1 pt-4">
					<div class="h-7 w-full rounded-4 bg-surface-gray-3" />
					<div class="h-7 w-full rounded-4 bg-surface-gray-2" />
				</div>
			</div>
			<div
				class="flex items-center gap-3 rounded-6 border border-outline-gray-2 p-3"
			>
				<div class="size-8 shrink-0 rounded-full bg-surface-gray-2" />
				<SkeletonText text="" width="w-32" class="flex-1" strong />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import SkeletonText from '@/components/Skeletons/SkeletonText.vue'

/** pages/CertificateVerification.vue: title block, preview and the side cards. */
</script>
