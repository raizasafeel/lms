<template>
	<div
		class="flex items-center justify-between gap-8"
		role="group"
		:aria-labelledby="labelId"
	>
		<div
			:data-testid="testid"
			class="flex size-20 shrink-0 items-center justify-center rounded border border-outline-elevation-2"
		>
			<img
				v-if="image_url"
				:src="safeUrl(image_url)"
				:alt="label"
				class="size-8 rounded"
			/>
			<span
				v-else
				:class="icon"
				class="size-5 text-ink-gray-4"
				aria-hidden="true"
			/>
		</div>
		<div class="flex min-w-0 flex-1 flex-col gap-1">
			<InputLabel
				:id="labelId"
				:label="label"
				:required="required"
				color="gray-7"
				class="font-medium leading-normal"
			/>
			<span v-if="description" class="text-p-base text-ink-gray-6">
				{{ description }}
			</span>
		</div>
		<ImageUploader
			:image_url="image_url"
			:image_type="image_type"
			:is_private="is_private"
			:testid="testid"
			:disabled="disabled"
			@upload="(url) => emit('upload', url)"
			@remove="emit('remove')"
		/>
	</div>
</template>
<script setup lang="ts">
import { useId } from 'vue'
import ImageUploader from '@/components/Controls/ImageUploader.vue'
import { InputLabel } from '@/components/Form/labeling'
import { safeUrl } from '@/utils/safeUrl'

/**
 * A settings row for one image: a square preview, the name and description of
 * what the image is for, and the Upload / Change / Remove pair on the end.
 *
 * The buttons are ImageUploader rather than a second copy of them, and privacy
 * travels straight through to it — this row is layout, and layout has no
 * opinion on who may read the file.
 *
 * `testid`, when given, names the preview tile and prefixes the buttons
 * (`<testid>-upload`, `<testid>-remove`), so a page with more than one row can
 * still be addressed a row at a time.
 *
 * `is_private` is declared at runtime for the reason ImageUploader's is: an
 * absent Boolean prop is cast to false, and false here means public.
 *
 * The name is an InputLabel rather than a span so that `required` draws the
 * same red mark a FormControl does — the buttons on the end are not a labelable
 * control, so the row is a group named by that label instead.
 */
defineProps({
	is_private: { type: Boolean, required: true, default: undefined },
	label: { type: String, required: true },
	description: { type: String, default: '' },
	image_url: { type: String, default: '' },
	image_type: { type: String, default: 'image/*' },
	icon: { type: String, default: 'lucide-image' },
	testid: { type: String, default: undefined },
	disabled: { type: Boolean, default: false },
	required: { type: Boolean, default: false },
})

const labelId = useId()

const emit = defineEmits<{
	upload: [url: string]
	remove: []
}>()
</script>
