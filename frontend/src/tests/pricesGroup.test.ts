import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { previews } = vi.hoisted(() => ({
	previews: { data: null as unknown, submit: vi.fn() },
}))

vi.mock('frappe-ui', () => ({
	createResource: () => previews,
	Button: {
		props: ['ariaLabel', 'label'],
		template: `<button v-bind="$attrs">{{ label }}<slot name="icon" /><slot /></button>`,
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
}))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: {
		name: 'Link',
		props: ['modelValue', 'doctype', 'filters', 'placeholder'],
		emits: ['update:modelValue'],
		template: '<div :data-doctype="doctype">{{ placeholder }}</div>',
	},
}))
vi.mock('@/components/InlineEdit/SettingSwitch.vue', () => ({
	default: {
		name: 'SettingSwitch',
		props: ['modelValue', 'label'],
		emits: ['update:modelValue'],
		template: '<div data-testid="switch" />',
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

function mountGroup(prices: PriceRow[], { enabled = 1, paid = true } = {}) {
	const state = reactive({ prices, enabled })
	const wrapper = mount(PricesGroup, {
		props: {
			paid,
			amount: 100,
			currency: 'USD',
			prices: state.prices,
			enabled: state.enabled,
			'onUpdate:prices': (value: PriceRow[]) => {
				state.prices = value
				wrapper.setProps({ prices: value })
			},
			'onUpdate:enabled': (value: number) => {
				state.enabled = value
				wrapper.setProps({ enabled: value })
			},
		},
		slots: { default: '<div data-testid="regular-price" />' },
		global: { mocks: { __: globalThis.__ } },
	})
	return { wrapper, state }
}

const countryPicker = (wrapper: ReturnType<typeof mount>) =>
	wrapper
		.findAllComponents({ name: 'Link' })
		.find((link) => link.props('doctype') === 'Country')!

const india: PriceRow = {
	country: 'India',
	price_type: 'Fixed',
	amount: 4999,
	currency: 'INR',
}

beforeEach(() => {
	previews.data = null
	previews.submit.mockReset()
})

describe('the price a row shows', () => {
	const preview = (formatted: string) => ({
		country: 'India',
		currency: 'INR',
		amount: 0,
		formatted,
	})

	it('shows a fixed price as is', () => {
		expect(priceResultLabel(india, preview('₹ 4,999'))).toBe('₹ 4,999')
	})

	it('shows the percent off and what it comes to', () => {
		const row: PriceRow = {
			country: 'India',
			price_type: 'Percent Off',
			percent_off: 40,
		}
		expect(priceResultLabel(row, preview('$ 60'))).toBe('−40% → $ 60')
	})

	it('keeps only the value its type uses', () => {
		const row = withRowValue({ ...india, price_type: 'Percent Off' }, 30)
		expect(row).toMatchObject({ percent_off: 30, amount: 0, currency: null })
	})

	it('gives a fixed row the regular currency when it has none', () => {
		const row = withRowValue(
			{ country: 'India', price_type: 'Fixed', currency: null },
			30,
			'USD'
		)
		expect(row).toMatchObject({ amount: 30, currency: 'USD' })
	})

	it('skips rows the server cannot price yet', () => {
		expect(isPriceable({ ...india, amount: 0 })).toBe(false)
		expect(isPriceable({ country: 'India', price_type: 'Percent Off' })).toBe(
			true
		)
	})
})

describe('the pricing section', () => {
	it('puts the regular price first and hides subsidies for a free course', () => {
		const { wrapper } = mountGroup([india], { paid: false })

		expect(wrapper.find('[data-testid="regular-price"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="switch"]').exists()).toBe(false)
		expect(wrapper.findAll('[data-testid="price-row"]')).toHaveLength(0)
	})

	it('keeps the rows but hides them while subsidized pricing is off', () => {
		const { wrapper, state } = mountGroup([india], { enabled: 0 })

		expect(wrapper.findAll('[data-testid="price-row"]')).toHaveLength(0)
		expect(state.prices).toEqual([india])
	})

	it('offers Add countries when there are no rows yet', () => {
		const { wrapper } = mountGroup([])

		expect(wrapper.get('[data-testid="no-country-prices"]').text()).toContain(
			'Add countries'
		)
	})

	it('adds a fixed row in the regular currency for a picked country, once', async () => {
		const { wrapper, state } = mountGroup([])

		countryPicker(wrapper).vm.$emit('update:modelValue', 'India')
		await flushPromises()
		countryPicker(wrapper).vm.$emit('update:modelValue', 'India')
		await flushPromises()

		expect(state.prices).toEqual([
			{ country: 'India', price_type: 'Fixed', amount: 0, currency: 'USD' },
		])
		expect(countryPicker(wrapper).props('filters')).toEqual({
			name: ['not in', ['India']],
		})
	})

	it('lists the rows by country name', () => {
		const { wrapper } = mountGroup([
			{ ...india, country: 'Pakistan' },
			{ ...india, country: 'Bangladesh' },
			india,
		])

		expect(
			wrapper
				.findAll('[data-testid="price-row"] td:first-child')
				.map((cell) => cell.text())
		).toEqual(['Bangladesh', 'India', 'Pakistan'])
	})

	it('asks the server what each row charges and shows it', async () => {
		previews.data = [
			{ country: 'India', currency: 'USD', formatted: '$ 60', amount: 60 },
		]
		const row: PriceRow = {
			country: 'India',
			price_type: 'Percent Off',
			percent_off: 40,
		}
		const { wrapper } = mountGroup([row])
		await flushPromises()

		expect(previews.submit).toHaveBeenCalledWith({
			amount: 100,
			currency: 'USD',
			prices: [row],
		})
		expect(wrapper.get('[data-testid="price-result"]').text()).toBe(
			'−40% → $ 60'
		)
	})

	it('offers a currency only for a fixed row', () => {
		const { wrapper } = mountGroup([
			india,
			{ country: 'Kenya', price_type: 'Percent Off', percent_off: 50 },
		])
		const currencies = wrapper
			.findAllComponents({ name: 'Link' })
			.filter((link) => link.props('doctype') === 'Currency')

		expect(currencies.map((link) => link.props('modelValue'))).toEqual(['INR'])
	})

	it('switches a row to a percent off and removes it', async () => {
		const { wrapper, state } = mountGroup([india])
		const [type, value] = wrapper.findAll('input')

		await type.setValue('Percent Off')
		await value.setValue('25')
		expect(state.prices[0]).toMatchObject({
			price_type: 'Percent Off',
			percent_off: 25,
			amount: 0,
			currency: null,
		})

		await wrapper.get('[data-testid="price-row"] button').trigger('click')
		expect(state.prices).toEqual([])
	})
})
