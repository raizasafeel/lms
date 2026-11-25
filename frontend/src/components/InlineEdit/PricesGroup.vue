<template>
	<SettingsGroup :title="__('Pricing')" icon="lucide-coins" name="pricing">
		<SettingRow :label="__('Prices in other currencies')" :summary="summary">
			<template #control>
				<Link
					:modelValue="''"
					doctype="Currency"
					query="lms.lms.api.search_currencies"
					:filters="{ enabled: 1 }"
					:placeholder="__('Add currency')"
					:aria-label="__('Add currency')"
					icon="lucide-plus"
					variant="subtle"
					trigger="button"
					align="end"
					@update:modelValue="addRow"
				/>
			</template>
			<ul
				v-if="prices.length"
				class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 px-3"
				:aria-label="__('Prices in other currencies')"
			>
				<li
					v-for="(row, index) in prices"
					:key="row.currency"
					class="flex items-center gap-2 py-2"
					data-testid="price-row"
				>
					<span class="w-12 shrink-0 text-base-medium text-ink-gray-9">
						{{ row.currency }}
					</span>
					<div class="w-28 shrink-0">
						<FormControl
							type="select"
							:modelValue="row.price_type"
							:options="PRICE_TYPES"
							variant="outline"
							:aria-label="__('Price type for {0}').format(row.currency)"
							@update:modelValue="
								(value: PriceRow['price_type']) => setType(index, value)
							"
						/>
					</div>
					<div class="w-32 shrink-0">
						<FormControl
							type="number"
							min="0"
							:max="row.price_type === 'Fixed' ? undefined : 99"
							:modelValue="rowValue(row) || ''"
							variant="outline"
							:aria-label="
								row.price_type === 'Fixed'
									? __('Price in {0}').format(row.currency)
									: __('Percent off in {0}').format(row.currency)
							"
							@update:modelValue="(value: string) => setValue(index, value)"
						>
							<template v-if="row.price_type !== 'Fixed'" #suffix>
								<span class="text-p-sm text-ink-gray-6">%</span>
							</template>
						</FormControl>
					</div>
					<span
						class="min-w-0 flex-1 truncate text-p-sm"
						:class="
							previewOf(row)?.error ? 'text-ink-red-6' : 'text-ink-gray-6'
						"
						data-testid="price-result"
					>
						{{ previewOf(row)?.error || priceResultLabel(row, previewOf(row)) }}
					</span>
					<Button
						variant="ghost"
						size="sm"
						:aria-label="__('Remove {0}').format(row.currency)"
						@click="removeRow(index)"
					>
						<template #icon>
							<span class="lucide-x size-4" aria-hidden="true" />
						</template>
					</Button>
				</li>
			</ul>
		</SettingRow>
	</SettingsGroup>
</template>

<script setup lang="ts">
import { Button, FormControl, createResource } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { computed, watch } from 'vue'
import Link from '@/components/Controls/Link.vue'
import SettingRow from '@/components/InlineEdit/SettingRow.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import {
	PRICE_TYPES,
	isPriceable,
	priceResultLabel,
	rowValue,
	withRowValue,
	type PricePreview,
	type PriceRow,
} from '@/utils/prices'

/** A course's or batch's prices in other currencies, each fixed or a percent off the primary price. */
const props = defineProps<{
	/** The primary price, and its currency. */
	amount?: number | null
	currency?: string | null
}>()
const prices = defineModel<PriceRow[]>('prices', { default: () => [] })

const summary = computed<string>(() =>
	__(
		'Learners billed in one of these currencies pay its price instead of the {0} one.'
	).format(props.currency || __('primary'))
)

const previews = createResource({ url: 'lms.lms.api.get_price_previews' })

const previewOf = (row: PriceRow): PricePreview | undefined =>
	isPriceable(row)
		? (previews.data as PricePreview[] | undefined)?.find(
				(preview) => preview.currency === row.currency
		  )
		: undefined

const loadPreviews = useDebounceFn(() => {
	const rows = prices.value.filter(isPriceable)
	if (!rows.length || !props.currency) return
	previews.submit({
		amount: props.amount || 0,
		currency: props.currency,
		prices: rows,
	})
}, 300)

watch(
	() => [prices.value, props.amount, props.currency],
	() => loadPreviews(),
	{ deep: true, immediate: true }
)

function addRow(currency: string): void {
	const taken = [props.currency, ...prices.value.map((row) => row.currency)]
	if (!currency || taken.includes(currency)) return
	prices.value = [...prices.value, { currency, price_type: 'Fixed', amount: 0 }]
}

function removeRow(index: number): void {
	prices.value = prices.value.filter((_row, other) => other !== index)
}

function update(index: number, row: PriceRow): void {
	prices.value = prices.value.map((current, other) =>
		other === index ? row : current
	)
}

function setType(index: number, price_type: PriceRow['price_type']): void {
	update(index, withRowValue({ ...prices.value[index], price_type }, 0))
}

function setValue(index: number, value: string): void {
	update(index, withRowValue(prices.value[index], Number(value) || 0))
}
</script>
