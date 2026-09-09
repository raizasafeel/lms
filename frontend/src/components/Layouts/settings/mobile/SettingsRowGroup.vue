<template>
	<div class="flex flex-col gap-1.5">
		<span v-if="label" class="px-1.5 text-xs-medium text-ink-gray-5">
			{{ label }}
		</span>
		<div
			class="flex flex-col overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-base"
		>
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
// One card of settings rows under an optional group heading, the inset-grouped
// list every mobile OS uses for its own settings. Rows draw their own
// separator, so the card only owns the frame.

// The heading reuses the pair the desktop settings sidebar uses for its group
// labels. No `tracking-wide` alongside it: the token already carries 0.02em,
// and the utility silently overrode it with Tailwind's stock 0.025em.
defineProps<{ label?: string }>()
</script>
