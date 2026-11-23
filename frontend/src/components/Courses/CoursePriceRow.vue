<template>
	<div
		class="flex items-center gap-2 rounded-4"
		:class="
			isMissing?.('price') && 'bg-surface-red-1 ring-2 ring-outline-red-3'
		"
	>
		<span class="w-12 shrink-0 text-p-sm text-ink-gray-6">{{
			__('Price')
		}}</span>
		<Link
			v-model="doc.currency"
			doctype="Currency"
			query="lms.lms.api.search_currencies"
			:filters="{ enabled: 1 }"
			:placeholder="__('Currency')"
			:aria-label="__('Currency')"
			size="sm"
			class="w-24 shrink-0"
			@update:modelValue="markDirty()"
		/>
		<FormControl
			v-model="doc.course_price"
			type="number"
			min="0"
			size="sm"
			:placeholder="__('Amount')"
			:aria-label="__('Amount')"
			class="min-w-0 flex-1"
			@input="markDirty()"
		/>
	</div>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { computed, inject } from 'vue'
import Link from '@/components/Controls/Link.vue'
import type { CourseFormContext } from '@/types'

/** Currency and amount, shared by a paid course and a paid certificate. */
const { resource, markDirty, isMissing } =
	inject<CourseFormContext>('courseForm')!

const doc = computed(() => resource.doc!)
</script>
