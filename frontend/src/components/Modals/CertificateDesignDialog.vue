<template>
	<Dialog v-model:open="open" size="4xl" :title="__('Certificate design')">
		<template #default>
			<p class="-mt-3 mb-5 text-p-base text-ink-gray-6">
				{{
					__(
						'Used for every new certificate issued for {0}. Your site logo and name are added automatically.'
					).format(courseTitle)
				}}
			</p>
			<div class="grid gap-5 md:grid-cols-[minmax(15rem,1fr)_2fr]">
				<RadioGroup
					v-model="selected"
					:aria-label="__('Design')"
					class="max-h-[60vh] overflow-y-auto"
				>
					<Radio
						v-for="design in designs"
						:key="design.name"
						:value="design.name"
						class="w-full items-center rounded-6 p-2 hover:bg-surface-gray-2"
					>
						<template #label>
							<span class="flex items-center gap-3">
								<img
									v-if="design.thumbnail"
									:src="safeUrl(design.thumbnail)"
									alt=""
									class="h-[68px] w-24 shrink-0 rounded-1 border border-outline-gray-2 object-cover"
								/>
								<span
									v-else
									class="h-[68px] w-24 shrink-0 rounded-1 bg-surface-gray-3"
								/>
								<span class="flex min-w-0 flex-col gap-1">
									<span
										class="flex items-center gap-1.5 text-base-medium text-ink-gray-8"
									>
										{{ design.label }}
										<Badge
											v-if="design.name === inUse"
											size="sm"
											variant="outline"
										>
											{{ __('In use') }}
										</Badge>
									</span>
									<span class="text-p-sm text-ink-gray-6">
										{{ design.description }}
									</span>
								</span>
							</span>
						</template>
					</Radio>
				</RadioGroup>
				<div class="flex min-w-0 flex-col gap-3">
					<div
						class="rounded-6 border border-outline-gray-1 bg-surface-gray-1 p-4"
					>
						<div class="shadow-md">
							<CertificatePreview
								:html="preview.data?.html ?? null"
								:loading="preview.loading"
								:title="__('Preview of {0}').format(selectedLabel)"
							/>
						</div>
					</div>
					<fieldset class="flex flex-wrap items-center gap-x-5 gap-y-2">
						<legend class="mb-2 text-p-sm-medium text-ink-gray-6">
							{{ __('Preview with') }}
						</legend>
						<Switch
							v-for="option in PREVIEW_OPTIONS"
							:key="option.key"
							v-model="sample[option.key]"
							size="sm"
							:label="__(option.label)"
						/>
					</fieldset>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex flex-wrap items-center gap-2">
				<span class="flex-1 text-p-sm text-ink-gray-6">
					{{ __('New certificates use this design. Issued ones keep theirs.') }}
				</span>
				<Button variant="subtle" @click="open = false">
					{{ __('Cancel') }}
				</Button>
				<Button variant="solid" :disabled="!selected" @click="confirm">
					{{ confirmLabel }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
	Badge,
	Button,
	Dialog,
	Radio,
	RadioGroup,
	Switch,
	createResource,
} from 'frappe-ui'
import CertificatePreview from '@/components/CertificatePreview.vue'
import { safeUrl } from '@/utils/safeUrl'
import type {
	CertificateDesignList,
	CertificatePreviewOption,
	CertificatePreviewResponse,
	Resource,
} from '@/types/api'
import {
	PREVIEW_OPTIONS,
	describeDesign,
	sortDesigns,
	type CertificateDesign,
} from '@/utils/certificateDesigns'

const props = defineProps<{
	course: string
	courseTitle: string
	current: string | null
}>()

const emit = defineEmits<{ select: [design: string] }>()

const open = defineModel<boolean>('open', { default: false })
const selected = ref<string>('')
const sample = reactive<Record<CertificatePreviewOption, boolean>>({
	long: false,
	batch: false,
	expiry: false,
	no_logo: false,
	rtl: false,
})

const designList = createResource({
	url: 'lms.lms.api.get_certificate_designs',
	cache: 'certificateDesigns',
	auto: true,
}) as Resource<CertificateDesignList | null>

const preview = createResource({
	url: 'lms.lms.api.preview_certificate_template',
	makeParams() {
		return {
			print_format: selected.value,
			course: props.course,
			sample: JSON.stringify(sample),
		}
	},
}) as Resource<CertificatePreviewResponse | null>

const inUse = computed<string | null>(
	() => props.current || designList.data?.default || null
)

const designs = computed<CertificateDesign[]>(() =>
	sortDesigns(designList.data?.designs ?? []).map(describeDesign)
)

const selectedLabel = computed<string>(
	() => describeDesign(selected.value).label
)

const confirmLabel = computed<string>(() =>
	selected.value === inUse.value
		? __('Done')
		: __('Use {0}').format(selectedLabel.value)
)

watch(
	[open, inUse],
	([isOpen]) => {
		if (isOpen && !selected.value) selected.value = inUse.value ?? ''
		if (!isOpen) selected.value = ''
	},
	{ immediate: true }
)

watch(
	[selected, sample],
	() => {
		if (open.value && selected.value) preview.reload()
	},
	{ immediate: true }
)

function confirm(): void {
	if (selected.value !== inUse.value) emit('select', selected.value)
	open.value = false
}
</script>
