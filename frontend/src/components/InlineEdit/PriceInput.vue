<template>
	<div class="flex items-center gap-2 rounded-4" :class="missingRing(missing)">
		<Link
			:modelValue="currency ?? ''"
			doctype="Currency"
			query="lms.lms.api.search_currencies"
			:filters="{ enabled: 1 }"
			:placeholder="__('Currency')"
			:aria-label="__('Currency')"
			variant="outline"
			class="w-24 shrink-0"
			@update:modelValue="(value: string) => emit('update:currency', value)"
		/>
		<FormControl
			:modelValue="amount || ''"
			type="number"
			min="0"
			variant="outline"
			:placeholder="__('Amount')"
			:aria-label="__('Amount')"
			class="min-w-0 flex-1"
			@update:modelValue="
				(value: string) => emit('update:amount', Number(value) || 0)
			"
		/>
	</div>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import { missingRing } from '@/components/InlineEdit/fieldClasses'

/** Currency and amount. Currencies come through the LMS search query. */
defineProps<{
	currency?: string | null
	amount?: number | null
	missing?: boolean
}>()

const emit = defineEmits<{
	'update:currency': [value: string]
	'update:amount': [value: number]
}>()
</script>
