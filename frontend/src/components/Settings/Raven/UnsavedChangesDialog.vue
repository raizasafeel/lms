<template>
	<Dialog
		v-model="open"
		:title="__('Leave without saving?')"
		:message="__('You have unsaved changes, leave anyway?')"
		size="sm"
		:actions="dialogActions"
	/>
</template>

<script setup lang="ts">
// Leaving is the destructive half here, since the edits are what is lost, so it
// takes the red solid button that the delete confirmation's does.
import { Dialog } from 'frappe-ui'
import { computed } from 'vue'
import { confirmActions } from '@/utils/raven/confirmDialog'

const emit = defineEmits<{ confirm: [] }>()
const open = defineModel<boolean>('open')

const dialogActions = computed(() =>
	confirmActions(__('Leave'), () => emit('confirm'))
)
</script>
