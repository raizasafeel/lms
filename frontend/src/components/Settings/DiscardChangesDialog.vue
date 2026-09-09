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
 * The prompt the settings dirty guard awaits before letting a navigation
 * discard an edited form.
 *
 * It reads its open state from the guard's module-level prompt rather than
 * taking a prop, because the guard has to be able to raise it from inside a
 * `router.beforeEach` — where there is no component to ask.
 *
 * Rendered once, by Settings.vue, beside the panel that installs the guard.
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

// Escape, the backdrop and the close control all just flip `show`. Without
// this the guard's promise is never settled and the navigation hangs for good,
// so a dismissal is read as "keep editing".
//
// answerDiscard's own re-entrant call through this watcher is harmless: it
// nulls the resolver before resolving, so the second call finds nothing left.
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
