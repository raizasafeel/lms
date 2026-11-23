<template>
	<div class="group relative">
		<FileUploader
			:fileTypes="['.jpg,.jpeg,.gif,.png,.webp']"
			:private="false"
			@success="(file: { file_url: string }) => (image = file.file_url)"
			@failure="onUploadFailure"
		>
			<template #default="{ openFileSelector, uploading }">
				<button
					type="button"
					class="relative grid aspect-video w-full place-items-center overflow-hidden rounded-5 border border-outline-gray-2 transition-colors hover:border-outline-gray-3"
					:class="image || !swatches ? 'bg-surface-gray-2' : courseTint(tint)"
					:aria-label="image ? __('Change image') : __('Upload an image')"
					@click="openFileSelector"
				>
					<img
						v-if="image"
						:src="safeUrl(image)"
						alt=""
						class="size-full object-cover"
					/>
					<span
						v-else-if="swatches"
						class="lucide-book-open size-10 stroke-[1.5]"
						aria-hidden="true"
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
			<div
				v-if="swatches && !image"
				class="flex items-center gap-1 rounded-full bg-surface-base px-1.5 py-1 shadow-sm"
			>
				<button
					v-for="(swatch, color) in COURSE_SWATCHES"
					:key="color"
					type="button"
					class="size-3.5 rounded-full"
					:class="[swatch, isPicked(color) && 'ring-2 ring-outline-gray-5']"
					:aria-label="__('{0} thumbnail').format(color)"
					:aria-pressed="isPicked(color)"
					@click="pickColor(color)"
				/>
			</div>
			<Button v-else-if="image" size="sm" @click="image = ''">
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
								:class="videoLink ? 'lucide-video' : 'lucide-video-off'"
							/>
						</template>
					</Button>
				</template>
				<template #default>
					<div class="w-[28rem] max-w-[90vw] p-1">
						<VideoPreviewField
							:modelValue="videoLink"
							:label="__('Preview video')"
							@update:modelValue="(url: string) => (videoLink = url)"
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
import { COURSE_SWATCHES, courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

/**
 * A card image with its preview video behind a popover. With `swatches`, an
 * empty image shows a colour tint the editor picks instead.
 */
defineProps<{ swatches?: boolean }>()

const image = defineModel<string | null | undefined>('image')
const videoLink = defineModel<string | null | undefined>('videoLink')
const tint = defineModel<string | null | undefined>('tint')

const isPicked = (color: string): boolean =>
	(tint.value || '').toLowerCase() === color

const pickColor = (color: string): void => {
	tint.value = color.charAt(0).toUpperCase() + color.slice(1)
}

function onUploadFailure(error: unknown): void {
	toast.error(
		error instanceof UploadError
			? error.messages[0] || error.message
			: __('Error uploading file')
	)
}
</script>
