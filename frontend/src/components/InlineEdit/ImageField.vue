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
						class="size-10 stroke-[1.5]"
						:class="courseIcon(icon)"
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
			class="absolute inset-x-2 bottom-2 flex items-center gap-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
		>
			<div
				v-if="swatches && !image"
				class="flex h-7 items-center gap-1 rounded-full bg-surface-base px-2 shadow-sm"
			>
				<button
					v-for="(swatch, color) in COURSE_SWATCHES"
					:key="color"
					type="button"
					class="grid size-3 place-items-center rounded-full"
					:class="swatch"
					:aria-label="__('{0} thumbnail').format(color)"
					:aria-pressed="isPicked(color)"
					@click="tint = courseColor(color)"
				>
					<span
						v-if="isPicked(color)"
						class="size-1 rounded-full bg-surface-base"
						aria-hidden="true"
					/>
				</button>
			</div>
			<Button v-else-if="image" size="sm" @click="image = ''">
				{{ __('Remove image') }}
			</Button>
			<Button
				v-if="swatches && !image"
				size="sm"
				class="ms-auto"
				icon="lucide-shuffle"
				:label="__('Random colour and icon')"
				:tooltip="__('Random colour and icon')"
				@click="shuffle"
			/>
		</div>
		<div
			v-if="swatches && !image"
			class="absolute start-2 top-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
		>
			<Popover side="bottom" align="start">
				<template #trigger>
					<Button size="sm" :label="__('Thumbnail icon')" :tooltip="__('Icon')">
						<template #icon>
							<span class="size-4" :class="courseIcon(icon)" />
						</template>
					</Button>
				</template>
				<template #default="{ close }">
					<CourseIconPicker
						class="w-72 p-2"
						:modelValue="icon"
						@update:modelValue="(name) => pickIcon(name, close)"
					/>
				</template>
			</Popover>
		</div>
		<div
			class="absolute end-2 top-2 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
			:class="videoLink ? 'opacity-100' : 'opacity-0'"
		>
			<Button
				size="sm"
				:tooltip="__('Preview video')"
				@click="showVideoDialog = true"
			>
				<template #prefix>
					<span
						class="size-4"
						:class="videoLink ? 'lucide-video' : 'lucide-video-off'"
					/>
				</template>
				{{ videoLink ? __('Video') : __('Add video') }}
			</Button>
		</div>
		<VideoLinkDialog v-model:open="showVideoDialog" v-model="videoLink" />
	</div>
</template>

<script setup lang="ts">
import { Button, FileUploader, Popover, UploadError, toast } from 'frappe-ui'
import { ref } from 'vue'
import CourseIconPicker from '@/components/InlineEdit/CourseIconPicker.vue'
import VideoLinkDialog from '@/components/InlineEdit/VideoLinkDialog.vue'
import { courseColor, courseIcon, shuffleThumbnail } from '@/utils/courseIcons'
import { COURSE_SWATCHES, courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

/**
 * A card image with its preview video behind a dialog. With `swatches`, an
 * empty image shows a colour tint and icon the editor picks instead.
 */
defineProps<{ swatches?: boolean }>()

const image = defineModel<string | null | undefined>('image')
const videoLink = defineModel<string | null | undefined>('videoLink')
const tint = defineModel<string | null | undefined>('tint')
const icon = defineModel<string | null | undefined>('icon')

const showVideoDialog = ref(false)

const isPicked = (color: string): boolean =>
	(tint.value || '').toLowerCase() === color

function pickIcon(name: string | null | undefined, close: () => void): void {
	icon.value = name
	close()
}

function shuffle(): void {
	const next = shuffleThumbnail(tint.value, icon.value)
	tint.value = next.color
	icon.value = next.icon
}

function onUploadFailure(error: unknown): void {
	toast.error(
		error instanceof UploadError
			? error.messages[0] || error.message
			: __('Error uploading file')
	)
}
</script>
