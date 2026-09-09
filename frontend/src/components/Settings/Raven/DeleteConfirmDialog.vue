<template>
	<Dialog
		v-model="open"
		:title="__('Delete {0}?').format(name)"
		:message="
			message ||
			__(
				'This deletes the {0} mapping and its membership rules, and stops syncing members. This cannot be undone.'
			).format(entityName)
		"
		size="sm"
		:actions="dialogActions"
	/>
</template>

<script setup lang="ts">
// Deleting a mapping leaves the Raven record alone, so no
// type-the-name-to-confirm gate.
import { Dialog } from 'frappe-ui'
import { computed } from 'vue'
import { confirmActions } from '@/utils/raven/confirmDialog'

const props = defineProps<{
	/** Name of the thing being deleted, shown in the title. */
	name: string
	/** What kind of thing is being deleted ("workspace" / "channel"). */
	entity?: string
	message?: string
	loading?: boolean
}>()
const emit = defineEmits<{ confirm: [] }>()
const open = defineModel<boolean>('open')

const entityName = computed<string>(() => props.entity || 'workspace')

const dialogActions = computed(() =>
	confirmActions(__('Delete'), () => emit('confirm'), props.loading)
)
</script>
