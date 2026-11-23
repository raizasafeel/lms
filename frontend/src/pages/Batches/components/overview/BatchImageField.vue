<template>
	<div class="group relative">
		<FileUploader
			:fileTypes="['.jpg,.jpeg,.gif,.png,.webp']"
			:private="false"
			@success="
				(file: { file_url: string }) => (doc.meta_image = file.file_url)
			"
			@failure="onUploadFailure"
		>
			<template #default="{ openFileSelector, uploading }">
				<button
					type="button"
					class="relative grid aspect-video w-full place-items-center overflow-hidden rounded-5 bg-surface-gray-2"
					:aria-label="
						doc.meta_image ? __('Change image') : __('Upload an image')
					"
					@click="openFileSelector"
				>
					<img
						v-if="doc.meta_image"
						:src="safeUrl(doc.meta_image)"
						alt=""
						class="size-full object-cover"
					/>
					<span
						v-else
						class="flex flex-col items-center gap-2 text-p-sm text-ink-gray-6"
					>
						<span class="lucide-image-plus size-8 stroke-[1.5]" />
						{{ __('Add an image') }}
					</span>
					<span
						v-if="uploading"
						class="absolute inset-0 grid place-items-center bg-surface-base/90 text-p-sm text-ink-gray-7"
					>
						{{ __('Uploading') }}
					</span>
				</button>
			</template>
		</FileUploader>
		<div
			class="absolute inset-x-0 bottom-0 flex items-center gap-1.5 p-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
		>
			<Button v-if="doc.meta_image" size="sm" @click="doc.meta_image = ''">
				{{ __('Remove image') }}
			</Button>
			<Popover side="bottom" align="end">
				<template #trigger>
					<Button
						size="sm"
						class="ms-auto"
						:label="__('Preview video')"
						:tooltip="__('Preview video')"
					>
						<template #icon>
							<span
								class="size-4"
								:class="doc.video_link ? 'lucide-video' : 'lucide-video-off'"
							/>
						</template>
					</Button>
				</template>
				<template #default>
					<div class="w-[28rem] max-w-[90vw] p-1">
						<VideoPreviewField
							v-model="doc.video_link"
							:label="__('Preview video')"
						/>
					</div>
				</template>
			</Popover>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, FileUploader, Popover, UploadError, toast } from 'frappe-ui'
import VideoPreviewField from '@/components/Controls/VideoPreviewField.vue'
import { safeUrl } from '@/utils/safeUrl'
import type { LMSBatch } from '@/types/lms/LMSBatch'

/** The enrol card's image, with the preview video behind a popover. */
defineProps<{ doc: LMSBatch }>()

function onUploadFailure(error: unknown): void {
	toast.error(
		error instanceof UploadError
			? error.messages[0] || error.message
			: __('Error uploading file')
	)
}
</script>
