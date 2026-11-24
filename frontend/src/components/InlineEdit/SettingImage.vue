<template>
	<SettingRow :label="label" :summary="summary">
		<template #control>
			<FileUploader
				file-types="image/*"
				:private="false"
				:validateFile="validate"
				@success="(file) => (model = file.file_url)"
			>
				<template #default="{ progress, uploading, openFileSelector }">
					<div class="group relative h-16 w-28">
						<button
							type="button"
							data-testid="setting-image-pick"
							class="flex size-full items-center justify-center overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-gray-1 text-ink-gray-6 hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							:aria-label="model ? __('Change image') : __('Upload image')"
							:disabled="uploading"
							@click="openFileSelector"
						>
							<img
								v-if="model"
								:src="safeUrl(model)"
								:alt="label"
								class="size-full object-cover"
							/>
							<span v-else class="flex items-center gap-1.5 text-p-sm">
								<span class="lucide-image-up size-4" aria-hidden="true" />
								{{ uploading ? `${progress}%` : __('Upload') }}
							</span>
							<span
								v-if="model"
								class="absolute inset-0 flex items-center justify-center rounded-6 bg-black-overlay-500 text-p-sm-medium text-white opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
							>
								{{ uploading ? `${progress}%` : __('Change') }}
							</span>
						</button>
						<button
							v-if="model"
							type="button"
							data-testid="setting-image-remove"
							class="absolute end-1 top-1 flex size-5 items-center justify-center rounded-full border border-outline-gray-2 bg-surface-base text-ink-gray-7 opacity-0 shadow-sm transition-opacity hover:text-ink-gray-9 focus-visible:opacity-100 group-focus-within:opacity-100 group-hover:opacity-100"
							:aria-label="__('Remove image')"
							@click="model = null"
						>
							<span class="lucide-x size-3" aria-hidden="true" />
						</button>
					</div>
				</template>
			</FileUploader>
		</template>
	</SettingRow>
</template>

<script setup lang="ts">
import { FileUploader } from 'frappe-ui'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import { validateFile } from '@/utils'
import { safeUrl } from '@/utils/safeUrl'

/** A settings row for one public image: a thumbnail on the end to upload, change or remove it. */
defineProps<{ label: string; summary?: string }>()
const model = defineModel<string | null | undefined>()

const validate = (file: File) => validateFile(file, true, 'image')
</script>
