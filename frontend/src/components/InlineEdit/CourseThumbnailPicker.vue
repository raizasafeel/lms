<template>
	<div class="py-3">
		<div class="flex flex-col gap-5 @lg:flex-row">
			<div class="flex shrink-0 flex-col gap-2 @lg:w-56">
				<ImageHoverUpload v-model:image="image" class="rounded-4">
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
				</ImageHoverUpload>
				<Button
					class="w-full"
					icon-left="lucide-shuffle"
					:label="__('Shuffle')"
					:tooltip="__('Pick a random colour and icon')"
					@click="shuffle"
				/>
				<Button
					v-if="image"
					class="w-full"
					variant="ghost"
					icon-left="lucide-trash-2"
					:label="__('Remove image')"
					@click="image = ''"
				/>
			</div>
			<div class="min-w-0 flex-1 space-y-4">
				<p
					v-if="image"
					class="flex items-center gap-2 text-p-base text-ink-gray-7"
				>
					<span class="lucide-info size-4 shrink-0" aria-hidden="true" />
					{{
						__(
							"The colour and icon show if the image is removed or doesn't load."
						)
					}}
				</p>
				<div
					class="flex flex-wrap items-center gap-3 p-1"
					role="group"
					:aria-label="__('Thumbnail colour')"
				>
					<button
						v-for="(swatch, color) in COURSE_SWATCHES"
						:key="color"
						type="button"
						class="size-9 rounded-full ring-offset-2 transition-shadow"
						:class="[swatch, isPicked(color) && 'ring-2 ring-outline-gray-5']"
						:aria-label="__('{0} thumbnail').format(color)"
						:aria-pressed="isPicked(color)"
						@click="tint = courseColor(color)"
					/>
				</div>
				<CourseIconPicker v-model="icon" :columns="16" large :tint="tint" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import CourseIconPicker from '@/components/InlineEdit/CourseIconPicker.vue'
import ImageHoverUpload from '@/components/InlineEdit/ImageHoverUpload.vue'
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
