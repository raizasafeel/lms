<template>
	<Avatar
		class="avatar border border-outline-gray-2 cursor-auto"
		v-if="user"
		:label="user.full_name"
		:image="user.user_image"
		:size="size"
		v-bind="$attrs"
	>
		<template v-if="status" #indicator>
			<Tooltip :text="status.label" :side="inlineEndSide()">
				<div
					role="img"
					:aria-label="status.label"
					class="status-dot grid place-items-center rounded-full"
					:class="status.fill"
				>
					<span
						class="status-glyph text-white"
						:class="status.icon"
						aria-hidden="true"
					/>
				</div>
			</Tooltip>
		</template>
	</Avatar>
</template>
<script setup lang="ts">
import { Avatar, Tooltip } from 'frappe-ui'
import { inlineEndSide } from '@/utils/textDirection'
import { computed } from 'vue'
import type { UserInfo } from '@/types'

const props = defineProps<{
	/** `open_to` draws the status dot on the avatar's corner. */
	user?: Pick<UserInfo, 'full_name' | 'user_image' | 'open_to'> | null
	size?: string
}>()

const STATUSES: Record<string, { label: string; icon: string; fill: string }> =
	{
		Work: {
			label: __('Open to Work'),
			icon: 'lucide-check',
			fill: 'bg-surface-green-7',
		},
		Hiring: {
			label: __('Hiring'),
			icon: 'lucide-briefcase',
			fill: 'bg-surface-violet-7',
		},
	}

const status = computed(() => STATUSES[props.user?.open_to || ''])
</script>

<style scoped>
/* frappe-ui sizes the dot's ring and fill in fixed steps; these scale with the
   avatar instead: a 2px ring in the surface colour around a dot ~35% wide. */
.avatar > :deep(.bottom-0) {
	width: 45%;
	height: 45%;
	min-width: 0.75rem;
	min-height: 0.75rem;
	margin: 0 -0.125rem -0.125rem 0;
	padding: 2px;
}
.avatar > :deep(.bottom-0 > div),
.status-dot {
	width: 100%;
	height: 100%;
}
.status-glyph {
	width: 65%;
	height: 65%;
}
.avatar:dir(rtl) > :deep(.bottom-0) {
	right: auto;
	left: 0;
	margin: 0 0 -0.125rem -0.125rem;
}
</style>
