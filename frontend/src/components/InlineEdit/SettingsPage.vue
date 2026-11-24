<template>
	<div
		class="grid w-full items-start gap-x-12 gap-y-10 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]"
	>
		<div class="min-w-0 space-y-10">
			<slot />
		</div>
		<aside class="lg:sticky lg:top-[calc(var(--header-frame-h)+1.25rem)]">
			<slot name="aside" />
		</aside>
	</div>
</template>

<script setup lang="ts">
/** A settings tab: its sections in one column, a panel beside them from lg and under them below. */
</script>
