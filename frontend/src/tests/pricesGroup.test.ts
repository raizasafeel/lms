import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { previews } = vi.hoisted(() => ({
	previews: { data: null as unknown, submit: vi.fn() },
}))

vi.mock('frappe-ui', () => ({
	createResource: () => previews,
	Button: {
		props: ['ariaLabel'],
		template: `<button v-bind="$attrs"><slot name="icon" /><slot /></button>`,
	},
	FormControl: {
		props: ['modelValue', 'type', 'options'],
		emits: ['update:modelValue'],
		template: `<input
			:data-type="type"
			:value="modelValue"
			@input="$emit('update:modelValue', $event.target.value)"
		/>`,
	},
	Tooltip: { template: '<div><slot /></div>' },
}))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: {
		name: 'Link',
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template: '<div data-testid="add-currency" />',
	},
}))
vi.mock('@vueuse/core', () => ({
	useDebounceFn: (fn: () => void) => fn,
}))

import PricesGroup from '@/components/InlineEdit/PricesGroup.vue'
import {
	isPriceable,
	priceResultLabel,
	withRowValue,
	type PriceRow,
} from '@/utils/prices'

function mountGroup(prices: PriceRow[]) {
	const state = reactive({ prices })
	const wrapper = mount(PricesGroup, {
		props: {
			amount: 100,
			currency: 'USD',
			prices: state.prices,
			'onUpdate:prices': (value: PriceRow[]) => {
				state.prices = value
				wrapper.setProps({ prices: value })
			},
		},
		global: { mocks: { __: globalThis.__ } },
	})
	return { wrapper, state }
}

beforeEach(() => {
	previews.data = null
	previews.submit.mockReset()
})

describe('the price a row shows', () => {
	const inr: PriceRow = { currency: 'INR', price_type: 'Fixed', amount: 4999 }

	it('shows a fixed price as is', () => {
		expect(
			priceResultLabel(inr, { currency: 'INR', formatted: '₹ 4,999' })
		).toBe('₹ 4,999')
	})

	it('shows the percent off and what it comes to', () => {
		const row: PriceRow = {
			currency: 'INR',
			price_type: 'Percent Off',
			percent_off: 40,
		}
		expect(
			priceResultLabel(row, { currency: 'INR', formatted: '₹ 3,210' })
		).toBe('−40% → ₹ 3,210')
	})

	it('keeps only the value its type uses', () => {
		const row = withRowValue({ ...inr, price_type: 'Percent Off' }, 30)
		expect(row).toMatchObject({ percent_off: 30, amount: 0 })
	})

	it('skips rows the server cannot price yet', () => {
		expect(isPriceable({ ...inr, amount: 0 })).toBe(false)
		expect(isPriceable({ currency: 'INR', price_type: 'Percent Off' })).toBe(
			true
		)
	})
})

describe('the pricing section', () => {
	it('adds a fixed row for a picked currency, but not the primary one', async () => {
		const { wrapper, state } = mountGroup([])
		const add = wrapper.getComponent({ name: 'Link' })

		add.vm.$emit('update:modelValue', 'USD')
		add.vm.$emit('update:modelValue', 'INR')
		await flushPromises()

		expect(state.prices).toEqual([
			{ currency: 'INR', price_type: 'Fixed', amount: 0 },
		])
		expect(wrapper.findAll('[data-testid="price-row"]')).toHaveLength(1)
	})

	it('asks the server what each row charges and shows it', async () => {
		previews.data = [{ currency: 'INR', formatted: '₹ 3,210', amount: 3210 }]
		const { wrapper } = mountGroup([
			{ currency: 'INR', price_type: 'Percent Off', percent_off: 40 },
		])
		await flushPromises()

		expect(previews.submit).toHaveBeenCalledWith({
			amount: 100,
			currency: 'USD',
			prices: [{ currency: 'INR', price_type: 'Percent Off', percent_off: 40 }],
		})
		expect(wrapper.get('[data-testid="price-result"]').text()).toBe(
			'−40% → ₹ 3,210'
		)
	})

	it('shows why a row has no price', async () => {
		previews.data = [{ currency: 'XTS', error: 'No exchange rate' }]
		const { wrapper } = mountGroup([
			{ currency: 'XTS', price_type: 'Percent Off', percent_off: 10 },
		])
		await flushPromises()

		expect(wrapper.get('[data-testid="price-result"]').text()).toBe(
			'No exchange rate'
		)
	})

	it('switches a row to a percent off and removes it', async () => {
		const { wrapper, state } = mountGroup([
			{ currency: 'INR', price_type: 'Fixed', amount: 4999 },
		])
		const [type, value] = wrapper.findAll('input')

		await type.setValue('Percent Off')
		await value.setValue('25')
		expect(state.prices[0]).toMatchObject({
			price_type: 'Percent Off',
			percent_off: 25,
			amount: 0,
		})

		await wrapper.get('button').trigger('click')
		expect(state.prices).toEqual([])
	})
})
