<template>
	<div class="py-3">
		<div class="flex flex-col gap-5 @lg:flex-row">
			<div class="flex shrink-0 flex-col gap-2 @lg:w-56">
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
				<ImageDropzone
					v-model:image="image"
					stacked
					:hint="__('750 × 422 px, JPG or PNG.')"
				/>
			</div>
			<div class="min-w-0 flex-1 space-y-3">
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
				<CourseIconPicker v-model="icon" :columns="16" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import CourseIconPicker from '@/components/InlineEdit/CourseIconPicker.vue'
import ImageDropzone from '@/components/InlineEdit/ImageDropzone.vue'
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
</script>
