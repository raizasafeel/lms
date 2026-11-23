<template>
	<SettingRow :label="label" :summary="summary">
		<template #control>
			<ImageUploader
				:image_url="model || ''"
				image_type="image/*"
				:is_private="false"
				@upload="(url: string) => (model = url)"
				@remove="model = null"
			/>
		</template>
		<img
			v-if="model"
			:src="safeUrl(model)"
			:alt="label"
			class="h-24 rounded-4 border border-outline-gray-2 object-cover"
		/>
	</SettingRow>
</template>

<script setup lang="ts">
import ImageUploader from '@/components/Controls/ImageUploader.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import { safeUrl } from '@/utils/safeUrl'

/** A settings row for one public image, with Upload, Change and Remove. */
defineProps<{ label: string; summary?: string }>()
const model = defineModel<string | null | undefined>()
</script>
