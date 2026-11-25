/**
 * The settings dirty guard lets a query change through without asking, and
 * asks for anything that leaves the form.
 */
import { describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { installDirtyGuard, useDirtyGuard } from '@/composables/useDirtyGuard'

type Guard = (to: unknown, from: unknown) => Promise<boolean>

const route = (
	path: string,
	hash: string,
	query: Record<string, string> = {}
) => ({
	path,
	hash,
	query,
})

const setup = () => {
	let guard: Guard | null = null
	const router = {
		beforeEach: (fn: Guard) => {
			guard = fn
			return () => {}
		},
	}
	const confirm = vi.fn(async () => false)
	installDirtyGuard(router as never, confirm)
	const scope = effectScope()
	scope.run(() => useDirtyGuard(() => true))
	return { guard: () => guard!, confirm, stop: () => scope.stop() }
}

describe('the settings dirty guard', () => {
	it('lets a query change on the same page through', async () => {
		const { guard, confirm, stop } = setup()
		const result = await guard()(
			route('/courses', '#settings', { settings: 'general', title: 'vue' }),
			route('/courses', '#settings', { settings: 'general' })
		)
		expect(result).toBe(true)
		expect(confirm).not.toHaveBeenCalled()
		stop()
	})

	it.each([
		['another page', route('/batches', '', { settings: 'general' })],
		['another settings tab', route('/courses', '', { settings: 'branding' })],
		[
			'another page tab',
			route('/courses', '#students', { settings: 'general' }),
		],
	])('asks before %s', async (_label, to) => {
		const { guard, confirm, stop } = setup()
		const result = await guard()(
			to,
			route('/courses', '', { settings: 'general' })
		)
		expect(confirm).toHaveBeenCalledTimes(1)
		expect(result).toBe(false)
		stop()
	})
})
