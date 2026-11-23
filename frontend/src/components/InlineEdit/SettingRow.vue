<template>
	<div class="py-3.5">
		<div class="flex items-center gap-6">
			<div class="min-w-0 flex-1">
				<div
					class="text-base-medium"
					:class="danger ? 'text-ink-red-6' : 'text-ink-gray-9'"
				>
					{{ label }}
				</div>
				<div v-if="summary" class="mt-0.5 text-p-sm text-ink-gray-6">
					{{ summary }}
				</div>
			</div>
			<div v-if="$slots.control" class="shrink-0">
				<slot name="control" />
			</div>
		</div>
		<div v-if="$slots.default" class="mt-3">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
/** One row in a settings box: label, one-line summary, control on the end. */
defineProps<{ label: string; summary?: string; danger?: boolean }>()
</script>
