<template>
	<Dropdown
		v-if="menu.length"
		:options="menu"
		:button="{
			icon: 'lucide-ellipsis',
			variant: 'ghost',
			label: __('Batch options'),
		}"
		side="bottom"
		align="end"
	/>
	<HeaderButton
		:label="__('Student view')"
		icon="lucide-eye"
		@click="emit('student-view')"
	/>
	<HeaderButton
		v-if="tab === 'dashboard'"
		:label="__('Enroll')"
		icon="lucide-plus"
		@click="openForm('NewBatchStudent')"
	/>
	<template v-if="tab === 'announcements' && !readOnlyMode">
		<Tooltip
			v-if="!batch.data?.student_count"
			:text="__('Add students to the batch to make an announcement')"
		>
			<HeaderButton
				:label="__('Make announcement')"
				icon="lucide-send"
				disabled
			/>
		</Tooltip>
		<HeaderButton
			v-else
			:label="__('Make announcement')"
			icon="lucide-send"
			@click="openForm('NewAnnouncement')"
		/>
	</template>
	<template v-if="isEditTab && form">
		<Button
			v-if="!isMobile && manage"
			variant="subtle"
			:loading="manage.publishing()"
			@click="manage.togglePublish()"
		>
			{{ batch.data?.published ? __('Unpublish') : __('Publish') }}
		</Button>
		<span
			@mouseenter="form.previewRequired(true)"
			@mouseleave="form.previewRequired(false)"
			@focusin="form.previewRequired(true)"
			@focusout="form.previewRequired(false)"
		>
			<ShortcutTooltip v-if="canSave" :label="__('Save')">
				<HeaderButton
					:label="__('Save')"
					variant="solid"
					@click="form.submitBatch()"
				/>
			</ShortcutTooltip>
			<Tooltip v-else :text="form.saveTooltip.value">
				<HeaderButton
					:label="__('Save')"
					variant="solid"
					:disabled="!form.isDirty.value"
					@click="form.submitBatch()"
				/>
			</Tooltip>
		</span>
	</template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dropdown, Tooltip } from 'frappe-ui'
import HeaderButton from '@/components/HeaderButton.vue'
import ShortcutTooltip from '@/components/ShortcutTooltip.vue'
import { openBatchForm } from '@/composables/useBatchForms'
import type { BatchRouteName } from '@/composables/useBatchForms'
import { useScreenSize } from '@/utils/composables'
import { injectBatchForm } from '@/pages/Batches/composables/useBatchForm'
import { injectBatchManage } from '@/pages/Batches/composables/useBatchManage'
import type { BatchDetails, Resource } from '@/types'

const props = defineProps<{
	tab?: string
	batch: Resource<BatchDetails | null>
}>()

const emit = defineEmits<{ 'student-view': [] }>()

const router = useRouter()
const route = useRoute()
const { isMobile } = useScreenSize()
const form = injectBatchForm()
const manage = injectBatchManage()
const readOnlyMode = window.read_only_mode

const isEditTab = computed(() =>
	['overview', 'settings'].includes(props.tab ?? 'overview')
)

const canSave = computed(
	() => Boolean(form?.isDirty.value) && !form?.missingFields.value.length
)

const openForm = (name: BatchRouteName) => {
	openBatchForm(router, name, props.batch.data?.name ?? '', route.hash)
}

const menu = computed(() => {
	if (!manage) return []
	const options = []
	if (props.batch.data?.certification) {
		options.push({
			label: __('Generate certificates'),
			icon: 'lucide-award',
			onClick: manage.generateCertificates,
		})
	}
	if (isMobile.value) {
		options.push({
			label: props.batch.data?.published
				? __('Unpublish batch')
				: __('Publish batch'),
			icon: props.batch.data?.published ? 'lucide-globe-lock' : 'lucide-globe',
			onClick: manage.togglePublish,
		})
	}
	options.push({
		label: __('Delete batch'),
		icon: 'lucide-trash-2',
		theme: 'red',
		onClick: manage.deleteBatch,
	})
	return options
})
</script>
