<template>
	<div class="group relative">
		<FileUploader
			:fileTypes="['.jpg,.jpeg,.gif,.png']"
			:private="false"
			@success="(file) => setImage(file.file_url)"
			@failure="onUploadFailure"
		>
			<template #default="{ openFileSelector, uploading }">
				<button
					type="button"
					class="relative grid aspect-video w-full place-items-center overflow-hidden rounded-5"
					:class="
						doc?.image ? 'bg-surface-gray-2' : courseTint(doc?.card_gradient)
					"
					:aria-label="
						doc?.image ? __('Change thumbnail') : __('Upload a thumbnail')
					"
					@click="openFileSelector"
				>
					<img
						v-if="doc?.image"
						:src="safeUrl(doc.image)"
						alt=""
						class="size-full object-cover"
					/>
					<span
						v-else
						class="lucide-book-open size-10 stroke-[1.5]"
						aria-hidden="true"
					/>
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
				v-if="!doc?.image"
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
			<Button v-else size="sm" @click="setImage('')">
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
							<span class="lucide-video size-4" />
						</template>
					</Button>
				</template>
				<template #default>
					<div class="w-[28rem] max-w-[90vw] p-1">
						<VideoPreviewField
							:modelValue="doc?.video_link"
							:label="__('Preview video')"
							@update:modelValue="setVideoLink"
						/>
					</div>
				</template>
			</Popover>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, FileUploader, Popover, UploadError, toast } from 'frappe-ui'
import { computed, inject } from 'vue'
import VideoPreviewField from '@/components/Controls/VideoPreviewField.vue'
import type { CourseFormContext } from '@/types'
import { COURSE_SWATCHES, courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

const { resource, markDirty } = inject<CourseFormContext>('courseForm')!

const doc = computed(() => resource.doc)

const isPicked = (color: string): boolean =>
	(doc.value?.card_gradient || '').toLowerCase() === color

function pickColor(color: string): void {
	if (!doc.value) return
	doc.value.card_gradient = color.charAt(0).toUpperCase() + color.slice(1)
	markDirty()
}

function setImage(url: string): void {
	if (!doc.value) return
	doc.value.image = url
	markDirty()
}

function setVideoLink(url: string): void {
	if (!doc.value) return
	doc.value.video_link = url
	markDirty()
}

function onUploadFailure(error: unknown): void {
	const message =
		error instanceof UploadError
			? error.messages[0] || error.message
			: __('Error uploading file')
	toast.error(message)
}
</script>
