<template>
	<SettingsGroup
		v-if="manage"
		:title="__('Manage')"
		:description="__('Visibility, certificates and removal.')"
	>
		<SettingRow
			:label="published ? __('Unpublish batch') : __('Publish batch')"
			:summary="
				published
					? __(
							'Hide it from the batches list. Enrolled learners keep their access.'
					  )
					: __('List it on the batches page so learners can find it.')
			"
		>
			<template #control>
				<Button
					size="sm"
					variant="subtle"
					:loading="manage.publishing()"
					@click="manage.togglePublish()"
				>
					{{ published ? __('Unpublish') : __('Publish') }}
				</Button>
			</template>
		</SettingRow>
		<SettingRow
			v-if="batch.data?.certification"
			:label="__('Generate certificates')"
			:summary="__('Issue certificates to learners who completed the batch.')"
		>
			<template #control>
				<Button
					size="sm"
					variant="subtle"
					@click="manage.generateCertificates()"
				>
					{{ __('Generate') }}
				</Button>
			</template>
		</SettingRow>
		<SettingRow
			:label="__('Delete batch')"
			:summary="
				__(
					'Removes the batch with its students, courses, assessments, feedback and discussions.'
				)
			"
			danger
		>
			<template #control>
				<Button
					size="sm"
					variant="subtle"
					theme="red"
					@click="manage.deleteBatch()"
				>
					{{ __('Delete') }}
				</Button>
			</template>
		</SettingRow>
	</SettingsGroup>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import { injectBatchManage } from '@/pages/Batches/composables/useBatchManage'
import type { BatchDetails, Resource } from '@/types'

/** The final settings box: publish, certificates and delete. */
const props = defineProps<{ batch: Resource<BatchDetails | null> }>()

const manage = injectBatchManage()
const published = computed(() => Boolean(props.batch.data?.published))
</script>
