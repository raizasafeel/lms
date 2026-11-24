import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { upload, toastError } = vi.hoisted(() => ({
	upload: vi.fn(),
	toastError: vi.fn(),
}))

vi.mock('frappe-ui', () => ({
	Button: {
		props: ['label'],
		emits: ['click'],
		template: '<button :aria-label="label" @click="$emit(\'click\')" />',
	},
	FileUploadHandler: class {
		upload = upload
	},
	toast: { error: toastError },
}))

import ImageDropzone from '@/components/InlineEdit/ImageDropzone.vue'

const mountZone = (image = '', stacked = false) => {
	const wrapper = mount(ImageDropzone, {
		props: {
			hint: '750 × 422 px',
			image,
			stacked,
			'onUpdate:image': (value: string) => wrapper.setProps({ image: value }),
		},
		global: { mocks: { __: (text: string) => text } },
	})
	return wrapper
}

const drop = (wrapper: ReturnType<typeof mountZone>, file: File) =>
	wrapper.trigger('drop', { dataTransfer: { files: [file] } })

describe('the image dropzone', () => {
	beforeEach(() => {
		upload.mockReset()
		toastError.mockReset()
	})

	it('uploads a dropped image as a public file and takes its URL', async () => {
		upload.mockResolvedValue({ file_url: '/files/cover.png' })
		const wrapper = mountZone()
		await drop(wrapper, new File(['x'], 'cover.png', { type: 'image/png' }))
		await flushPromises()
		expect(upload).toHaveBeenCalledWith(expect.any(File), { private: false })
		expect(wrapper.props('image')).toBe('/files/cover.png')
	})

	it('refuses a file that is not a JPG or PNG', async () => {
		const wrapper = mountZone()
		await drop(
			wrapper,
			new File(['x'], 'notes.pdf', { type: 'application/pdf' })
		)
		expect(upload).not.toHaveBeenCalled()
		expect(toastError).toHaveBeenCalled()
	})

	it('offers to replace or remove an image it already has', async () => {
		const wrapper = mountZone('/files/old.png')
		expect(wrapper.text()).toContain('Drop a new image to replace, or')
		await wrapper.get('[aria-label="Remove image"]').trigger('click')
		expect(wrapper.props('image')).toBe('')
	})

	it('stacks without its own thumbnail in a narrow column', async () => {
		const wrapper = mountZone('/files/old.png', true)
		expect(wrapper.find('img').exists()).toBe(false)
		expect(wrapper.classes()).toContain('flex-col')
		await wrapper.get('[aria-label="Remove image"]').trigger('click')
		expect(wrapper.props('image')).toBe('')
	})
})
