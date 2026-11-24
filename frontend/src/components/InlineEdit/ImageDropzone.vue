<template>
	<div
		v-if="stacked && image"
		class="grid grid-cols-2 gap-2"
		data-testid="image-dropzone"
		@dragover.prevent
		@drop.prevent="onDrop"
	>
		<Button
			icon-left="lucide-upload"
			:label="__('Replace')"
			:loading="uploading"
			@click="input?.click()"
		/>
		<Button
			icon-left="lucide-trash-2"
			:label="__('Remove')"
			@click="image = ''"
		/>
		<input
			ref="input"
			type="file"
			:accept="ACCEPT"
			class="hidden"
			@change="onPick"
		/>
	</div>
	<div
		v-else
		class="flex rounded-6 border border-dashed p-3 transition-colors"
		:class="[
			stacked
				? 'flex-col items-center gap-1.5 text-center'
				: 'items-center gap-4',
			dragging
				? 'border-outline-gray-4 bg-surface-gray-1'
				: 'border-outline-gray-3',
		]"
		data-testid="image-dropzone"
		@dragover.prevent="dragging = true"
		@dragleave.prevent="dragging = false"
		@drop.prevent="onDrop"
	>
		<div
			v-if="!stacked"
			class="grid size-14 shrink-0 place-items-center overflow-hidden rounded-4 border border-outline-gray-1 bg-surface-gray-2"
		>
			<img
				v-if="image"
				:src="safeUrl(image)"
				alt=""
				class="size-full object-cover"
			/>
			<span
				v-else
				class="lucide-image-plus size-5 text-ink-gray-6"
				aria-hidden="true"
			/>
		</div>
		<span
			v-if="stacked"
			class="lucide-image-plus size-5 text-ink-gray-6"
			aria-hidden="true"
		/>
		<div class="min-w-0 flex-1">
			<p class="text-p-base text-ink-gray-8">
				<template v-if="uploading">{{ __('Uploading…') }}</template>
				<template v-else>
					{{
						image
							? __('Drop a new image to replace, or')
							: __('Drop an image here, or')
					}}
					<button
						type="button"
						class="font-medium text-ink-gray-9 underline underline-offset-2"
						@click="input?.click()"
					>
						{{ __('browse') }}
					</button>
				</template>
			</p>
			<p class="text-p-sm text-ink-gray-6">{{ hint }}</p>
		</div>
		<Button
			v-if="image"
			variant="ghost"
			icon="lucide-x"
			:label="__('Remove image')"
			:tooltip="__('Remove image')"
			@click="image = ''"
		/>
		<input
			ref="input"
			type="file"
			:accept="ACCEPT"
			class="hidden"
			@change="onPick"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { Button } from 'frappe-ui'
import { IMAGE_ACCEPT, useImageUpload } from '@/composables/useImageUpload'
import { safeUrl } from '@/utils/safeUrl'

/**
 * A dashed drop target for one public image, with browse and remove. Stacked
 * with an image set, the preview above shows it: just Replace and Remove,
 * still taking a dropped file.
 */
defineProps<{
	hint: string
	/** Narrow column: no thumbnail of its own, text centred under each other. */
	stacked?: boolean
}>()
const image = defineModel<string | null | undefined>('image')

const ACCEPT = IMAGE_ACCEPT
const input = useTemplateRef<HTMLInputElement>('input')
const dragging = ref<boolean>(false)
const { uploading, onDrop: upload, onPick } = useImageUpload(image)

function onDrop(event: DragEvent): void {
	dragging.value = false
	upload(event)
}
</script>
