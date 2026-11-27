<template>
	<SettingsGroup :title="__('Pricing')" icon="lucide-coins" name="pricing">
		<slot />
		<template v-if="paid">
			<SettingSwitch
				v-model="enabled"
				:label="__('Subsidized pricing')"
				:summary="
					summary ||
					__(
						'Learners billed in the countries you add pay a lower price. Everyone else pays the regular price.'
					)
				"
			/>
			<div v-if="enabled" class="pb-3.5">
				<div
					v-if="!rows.length"
					class="flex flex-col items-center gap-2 rounded-6 border border-dashed border-outline-gray-2 px-4 py-6"
					data-testid="no-country-prices"
				>
					<span class="text-p-sm text-ink-gray-6">
						{{ __('No country prices yet') }}
					</span>
					<Link
						:modelValue="''"
						v-bind="countryPicker"
						:placeholder="__('Add countries')"
						:aria-label="__('Add countries')"
						align="center"
						@update:modelValue="addRow"
					/>
				</div>
				<template v-else>
					<div class="rounded-6 border border-outline-gray-2 px-3">
						<table class="w-full" :aria-label="__('Country prices')">
							<thead>
								<tr class="text-start text-p-sm text-ink-gray-6">
									<th class="py-2 text-start font-normal">
										{{ __('Country') }}
									</th>
									<th class="py-2 text-start font-normal">{{ __('Type') }}</th>
									<th class="py-2 text-start font-normal">{{ __('Value') }}</th>
									<th class="py-2 text-start font-normal">
										{{ __('Result') }}
									</th>
									<th class="w-8">
										<span class="sr-only">{{ __('Remove') }}</span>
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-outline-gray-1">
								<tr
									v-for="row in rows"
									:key="row.country"
									data-testid="price-row"
								>
									<td
										class="max-w-36 truncate py-2 pe-2 text-base-medium text-ink-gray-9"
										:title="row.country"
									>
										{{ row.country }}
									</td>
									<td class="w-28 py-2 pe-2">
										<FormControl
											type="select"
											:modelValue="row.price_type"
											:options="PRICE_TYPES"
											variant="outline"
											:aria-label="__('Price type for {0}').format(row.country)"
											@update:modelValue="
												(value: PriceRow['price_type']) => setType(row, value)
											"
										/>
									</td>
									<td class="py-2 pe-2">
										<div class="flex items-center gap-1">
											<FormControl
												type="number"
												min="0"
												:max="row.price_type === 'Fixed' ? undefined : 99"
												:modelValue="rowValue(row) || ''"
												variant="outline"
												class="w-24"
												:aria-label="
													row.price_type === 'Fixed'
														? __('Price for {0}').format(row.country)
														: __('Percent off for {0}').format(row.country)
												"
												@update:modelValue="(value: string) => setValue(row, value)"
											>
												<template v-if="row.price_type !== 'Fixed'" #suffix>
													<span class="text-p-sm text-ink-gray-6">%</span>
												</template>
											</FormControl>
											<Link
												v-if="row.price_type === 'Fixed'"
												:modelValue="row.currency || currency || ''"
												doctype="Currency"
												query="lms.lms.api.search_currencies"
												:filters="{ enabled: 1 }"
												:aria-label="__('Currency for {0}').format(row.country)"
												variant="subtle"
												trigger="button"
												@update:modelValue="
													(value: string) => setCurrency(row, value)
												"
											/>
										</div>
									</td>
									<td
										class="max-w-32 truncate py-2 pe-2 text-p-sm text-ink-gray-6"
										data-testid="price-result"
									>
										{{ priceResultLabel(row, previewOf(row)) }}
									</td>
									<td class="py-2 text-end">
										<Button
											variant="ghost"
											size="sm"
											:aria-label="__('Remove {0}').format(row.country)"
											@click="removeRow(row)"
										>
											<template #icon>
												<span class="lucide-x size-4" aria-hidden="true" />
											</template>
										</Button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<Link
						:modelValue="''"
						v-bind="countryPicker"
						:placeholder="__('Add country')"
						:aria-label="__('Add country')"
						class="mt-2"
						@update:modelValue="addRow"
					/>
				</template>
			</div>
		</template>
	</SettingsGroup>
</template>

<script setup lang="ts">
import { Button, FormControl, createResource } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { computed, watch } from 'vue'
import Link from '@/components/Controls/Link.vue'
import SettingSwitch from '@/components/InlineEdit/SettingSwitch.vue'
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

/**
 * The Pricing section: the regular price rows the form puts in the slot, then
 * subsidized prices per country, each fixed or a percent off the regular price.
 */
const props = defineProps<{
	/** Whether the course or batch is sold at all; subsidies apply only then. */
	paid?: boolean
	/** What the subsidy applies to, when it is not the course or batch itself. */
	summary?: string
	/** The regular price, and its currency. */
	amount?: number | null
	currency?: string | null
}>()
const prices = defineModel<PriceRow[]>('prices', { default: () => [] })
const enabled = defineModel<number | boolean | null | undefined>('enabled')

const rows = computed<PriceRow[]>(() =>
	[...prices.value].sort((a, b) => a.country.localeCompare(b.country))
)

const countryPicker = computed(() => ({
	doctype: 'Country',
	filters: rows.value.length
		? { name: ['not in', rows.value.map((row) => row.country)] }
		: {},
	icon: 'lucide-plus',
	variant: 'subtle',
	trigger: 'button',
}))

const previews = createResource({ url: 'lms.lms.api.get_price_previews' })

const previewOf = (row: PriceRow): PricePreview | undefined =>
	isPriceable(row)
		? (previews.data as PricePreview[] | undefined)?.find(
				(preview) => preview.country === row.country
		  )
		: undefined

const loadPreviews = useDebounceFn(() => {
	const priceable = prices.value.filter(isPriceable)
	if (!enabled.value || !priceable.length || !props.currency) return
	previews.submit({
		amount: props.amount || 0,
		currency: props.currency,
		prices: priceable,
	})
}, 300)

watch(
	() => [prices.value, props.amount, props.currency, enabled.value],
	() => loadPreviews(),
	{ deep: true, immediate: true }
)

function addRow(country: string): void {
	if (!country || prices.value.some((row) => row.country === country)) return
	prices.value = [
		...prices.value,
		{ country, price_type: 'Fixed', amount: 0, currency: props.currency },
	]
}

function removeRow(row: PriceRow): void {
	prices.value = prices.value.filter((other) => other.country !== row.country)
}

function update(row: PriceRow, changed: PriceRow): void {
	prices.value = prices.value.map((other) =>
		other.country === row.country ? changed : other
	)
}

function setType(row: PriceRow, price_type: PriceRow['price_type']): void {
	update(row, withRowValue({ ...row, price_type }, 0, props.currency))
}

function setValue(row: PriceRow, value: string): void {
	update(row, withRowValue(row, Number(value) || 0, props.currency))
}

function setCurrency(row: PriceRow, currency: string): void {
	if (currency) update(row, { ...row, currency })
}
</script>
