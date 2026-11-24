import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { upload } = vi.hoisted(() => ({ upload: vi.fn() }))

vi.mock('frappe-ui', () => ({
	Button: {
		props: ['label'],
		template: '<button data-testid="hover-upload">{{ label }}</button>',
	},
	FileUploadHandler: class {
		upload = upload
	},
	toast: { error: vi.fn() },
}))

import ImageHoverUpload from '@/components/InlineEdit/ImageHoverUpload.vue'

const mountUpload = (image = '') => {
	const wrapper = mount(ImageHoverUpload, {
		props: {
			image,
			'onUpdate:image': (value: string) => wrapper.setProps({ image: value }),
		},
		slots: { default: '<div class="preview" />' },
		global: { mocks: { __: (text: string) => text } },
	})
	return wrapper
}

describe('the hover uploader', () => {
	it('wraps the preview and offers an upload, or a replace once set', () => {
		expect(mountUpload().find('.preview').exists()).toBe(true)
		expect(mountUpload().get('button').text()).toBe('Upload image')
		expect(mountUpload('/files/a.png').get('button').text()).toBe(
			'Replace image'
		)
	})

	it('takes an image dropped on the preview as a public file', async () => {
		upload.mockResolvedValue({ file_url: '/files/b.png' })
		const wrapper = mountUpload()
		await wrapper.trigger('drop', {
			dataTransfer: {
				files: [new File(['x'], 'b.png', { type: 'image/png' })],
			},
		})
		await flushPromises()
		expect(upload).toHaveBeenCalledWith(expect.any(File), { private: false })
		expect(wrapper.props('image')).toBe('/files/b.png')
	})
})
