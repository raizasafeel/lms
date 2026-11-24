import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useFlowDocked } from '@/composables/useFlowDocked'

export interface FoldablePanel {
	isOpen: Ref<boolean>
	fold: () => void
	open: () => void
}

/**
 * A side panel that folds away by hand, and on its own while Flow is docked
 * beside the app; it comes back when Flow closes unless it was folded by hand.
 */
export function useFoldablePanel(): FoldablePanel {
	const isOpen = ref<boolean>(true)
	let closedForFlow = false

	const fold = (): void => {
		isOpen.value = false
		closedForFlow = false
	}

	const open = (): void => {
		isOpen.value = true
		closedForFlow = false
	}

	watch(
		useFlowDocked(),
		(isDocked) => {
			if (isDocked && isOpen.value) {
				isOpen.value = false
				closedForFlow = true
			} else if (!isDocked && closedForFlow) open()
		},
		{ immediate: true }
	)

	return { isOpen, fold, open }
}
