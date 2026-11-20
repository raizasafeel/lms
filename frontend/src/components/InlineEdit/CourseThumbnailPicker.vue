<template>
	<div class="flex flex-col gap-5 py-3 @lg:flex-row">
		<div class="flex shrink-0 flex-col gap-2 @lg:w-40">
			<div
				class="grid aspect-video w-full place-items-center overflow-hidden rounded-4 border border-outline-gray-1"
				:class="image ? 'bg-surface-gray-2' : courseTint(tint)"
				data-testid="thumbnail-preview"
			>
				<img
					v-if="image"
					:src="safeUrl(image)"
					alt=""
					class="size-full object-cover"
				/>
				<span
					v-else
					class="size-10 stroke-[1.5]"
					:class="courseIcon(icon)"
					aria-hidden="true"
				/>
			</div>
			<Button
				class="w-full"
				icon-left="lucide-shuffle"
				:label="__('Shuffle')"
				:tooltip="__('Pick a random colour and icon')"
				@click="shuffle"
			/>
		</div>
		<div class="min-w-0 max-w-xl flex-1 space-y-3">
			<div
				class="flex flex-wrap items-center gap-2 p-1"
				role="group"
				:aria-label="__('Thumbnail colour')"
			>
				<button
					v-for="(swatch, color) in COURSE_SWATCHES"
					:key="color"
					type="button"
					class="size-6 rounded-full"
					:class="[swatch, isPicked(color) && 'ring-2 ring-outline-gray-5']"
					:aria-label="__('{0} thumbnail').format(color)"
					:aria-pressed="isPicked(color)"
					@click="tint = courseColor(color)"
				/>
			</div>
			<CourseIconPicker v-model="icon" :columns="9" />
			<div class="flex flex-wrap items-center gap-2">
				<FileUploader
					:fileTypes="['.jpg,.jpeg,.png']"
					:private="false"
					@success="(file: { file_url: string }) => (image = file.file_url)"
					@failure="onUploadFailure"
				>
					<template #default="{ openFileSelector, uploading }">
						<Button
							variant="ghost"
							icon-left="lucide-upload"
							:loading="uploading"
							:label="
								image ? __('Change image') : __('Upload an image instead')
							"
							@click="openFileSelector"
						/>
					</template>
				</FileUploader>
				<Button
					v-if="image"
					variant="ghost"
					:label="__('Remove image')"
					@click="image = ''"
				/>
				<span class="text-p-xs text-ink-gray-6">
					{{ __('750 × 422, JPG or PNG') }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, FileUploader, UploadError, toast } from 'frappe-ui'
import CourseIconPicker from '@/components/InlineEdit/CourseIconPicker.vue'
import { courseColor, courseIcon, shuffleThumbnail } from '@/utils/courseIcons'
import { COURSE_SWATCHES, courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

/** The course card thumbnail: a colour and icon, or an uploaded image. */
const image = defineModel<string | null | undefined>('image')
const tint = defineModel<string | null | undefined>('tint')
const icon = defineModel<string | null | undefined>('icon')

const isPicked = (color: string): boolean =>
	(tint.value || '').toLowerCase() === color

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
