<template>
	<Dialog
		v-model="open"
		:title="__('Discard changes?')"
		:message="__('This form has unsaved changes. Leaving now discards them.')"
		size="sm"
		:actions="dialogActions"
	/>
</template>

<script setup lang="ts">
/**
 * The prompt the settings dirty guard awaits before letting a navigation discard
 * an edited form. It reads its open state from the guard's module-level prompt,
 * because the guard raises it from inside a `router.beforeEach`.
 */
import { Dialog } from 'frappe-ui'
import { computed, watch } from 'vue'
import { answerDiscard, discardPrompt } from '@/composables/useDirtyGuard'

interface DialogAction {
	label: string
	variant?: 'solid'
	theme?: 'red'
	onClick: () => void
}

// Vue unwraps only top-level refs in a template and this one hangs off an
// object, so it is aliased here.
const open = discardPrompt.show

// Escape, the backdrop and the close control all just flip `show`. Without this
// the guard's promise is never settled and the navigation hangs, so a dismissal
// is read as "keep editing".
watch(open, (showing) => {
	if (!showing) answerDiscard(false)
})

const dialogActions = computed<DialogAction[]>(() => [
	{
		label: __('Keep editing'),
		onClick: () => answerDiscard(false),
	},
	{
		label: __('Discard'),
		variant: 'solid' as const,
		theme: 'red' as const,
		onClick: () => answerDiscard(true),
	},
])
</script>
