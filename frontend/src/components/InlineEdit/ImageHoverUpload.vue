<template>
	<div
		class="group/upload relative"
		@dragover.prevent="dragging = true"
		@dragleave.prevent="dragging = false"
		@drop.prevent="onDrop"
	>
		<slot />
		<div
			class="pointer-events-none absolute inset-0 grid place-items-center rounded-[inherit] transition-opacity"
			:class="
				dragging || uploading
					? 'bg-surface-base/80 opacity-100'
					: 'opacity-0 group-focus-within/upload:opacity-100 group-hover/upload:opacity-100'
			"
		>
			<Button
				class="pointer-events-auto shadow-sm"
				icon-left="lucide-upload"
				:loading="uploading"
				:label="image ? __('Replace image') : __('Upload image')"
				data-testid="hover-upload"
				@click="input?.click()"
			/>
		</div>
		<input
			ref="input"
			type="file"
			:accept="IMAGE_ACCEPT"
			class="hidden"
			@change="onPick"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { Button } from 'frappe-ui'
import { IMAGE_ACCEPT, useImageUpload } from '@/composables/useImageUpload'

/** Wraps a preview: hovering it offers an upload, and an image dropped on it is taken. */
const image = defineModel<string | null | undefined>('image')

const input = useTemplateRef<HTMLInputElement>('input')
const dragging = ref<boolean>(false)
const { uploading, onDrop: upload, onPick } = useImageUpload(image)

function onDrop(event: DragEvent): void {
	dragging.value = false
	upload(event)
}
</script>
