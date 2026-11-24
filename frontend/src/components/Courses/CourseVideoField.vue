<template>
	<div class="group relative">
		<VideoPreview
			v-if="videoLink"
			:video-link="videoLink"
			:fallback-image="image"
			class="overflow-hidden rounded-5"
		/>
		<div
			v-else
			class="grid aspect-video w-full place-items-center overflow-hidden rounded-5 border border-outline-gray-2"
			:class="image ? 'bg-surface-gray-2' : courseTint(tint)"
			data-testid="course-thumbnail"
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
		<div
			class="absolute end-2 top-2 flex items-center gap-1.5 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
			:class="videoLink ? 'opacity-100' : 'opacity-0'"
		>
			<!-- The thumbnail is edited in Settings; this points the way there. -->
			<Button
				size="sm"
				icon-left="lucide-image"
				:label="__('Edit thumbnail')"
				:route="{ hash: '#settings', query: { section: 'thumbnail' } }"
				data-testid="edit-thumbnail"
			/>
			<Button
				size="sm"
				:tooltip="__('Preview video')"
				data-testid="video-button"
				@click="showDialog = true"
			>
				<template #prefix>
					<span
						class="size-4"
						:class="videoLink ? 'lucide-video' : 'lucide-video-off'"
					/>
				</template>
				{{ videoLink ? __('Change video') : __('Add video') }}
			</Button>
		</div>
		<VideoLinkDialog v-model:open="showDialog" v-model="videoLink" />
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button } from 'frappe-ui'
import VideoPreview from '@/components/VideoPreview.vue'
import VideoLinkDialog from '@/components/InlineEdit/VideoLinkDialog.vue'
import { courseIcon } from '@/utils/courseIcons'
import { courseTint } from '@/utils/courseTints'
import { safeUrl } from '@/utils/safeUrl'

/**
 * The top of the course card while editing: the preview video, or the
 * thumbnail until there is one. The thumbnail itself is set in Settings.
 */
defineProps<{
	image?: string | null
	tint?: string | null
	icon?: string | null
}>()
const videoLink = defineModel<string | null | undefined>('videoLink')

const showDialog = ref<boolean>(false)
</script>
