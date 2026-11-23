<template>
	<SettingsGroup
		:title="__('Access')"
		:description="
			__('Who can find the course, how they join and how they move through it.')
		"
	>
		<SettingRow
			v-for="row in accessRows"
			:key="row.label"
			:label="row.label"
			:summary="row.summary"
		>
			<template #control>
				<BooleanSwitch
					:modelValue="row.value"
					:aria-label="row.label"
					:data-label="row.label"
					@update:modelValue="row.set"
				/>
			</template>
		</SettingRow>
	</SettingsGroup>

	<SettingsGroup
		:title="__('Evaluation and certificate')"
		:description="__('Certificate type and price are on the Overview page.')"
	>
		<template v-if="hasCertificate">
			<SettingRow
				:label="__('Certificate design')"
				:summary="certificateDesignLabel"
			>
				<template #control>
					<Button size="sm" @click="showDesignDialog = true">
						{{ __('Change') }}
					</Button>
				</template>
			</SettingRow>
			<SettingRow
				v-if="doc.paid_certificate"
				:label="__('Evaluator')"
				:summary="__('Learners book a session with them after finishing.')"
			>
				<Link
					ref="evaluatorLinkRef"
					v-model="doc.evaluator"
					doctype="Course Evaluator"
					:aria-label="__('Evaluator')"
					:placeholder="__('Select evaluator')"
					variant="outline"
					:onCreate="openEvaluatorModal"
					@update:modelValue="markDirty()"
				/>
			</SettingRow>
			<SettingRow
				v-if="doc.paid_certificate"
				:label="__('Timezone')"
				:summary="__('Evaluation slots are shown in this timezone.')"
			>
				<FormControl
					v-model="doc.timezone"
					type="combobox"
					:aria-label="__('Timezone')"
					:options="timezoneOptions"
					:placeholder="__('Select timezone')"
					variant="outline"
					@update:modelValue="markDirty()"
				/>
			</SettingRow>
		</template>
		<SettingRow
			v-else
			:label="__('No certificate')"
			:summary="__('Turn on a certificate on the Overview page first.')"
		/>
	</SettingsGroup>

	<CertificateDesignDialog
		v-if="showDesignDialog"
		v-model:open="showDesignDialog"
		:course="doc.name"
		:courseTitle="doc.title"
		:current="doc.certificate_template || null"
		@select="setCertificateDesign"
	/>

	<NewMemberModal
		v-model="showMemberModal"
		:defaultRoles="['batch_evaluator']"
		@created="onEvaluatorCreated"
	/>
</template>

<script setup lang="ts">
import { Button, FormControl, createResource } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import Link from '@/components/Controls/Link.vue'
import SettingRow from '@/components/Courses/settings/SettingRow.vue'
import SettingsGroup from '@/components/Courses/settings/SettingsGroup.vue'
import CertificateDesignDialog from '@/components/Modals/CertificateDesignDialog.vue'
import NewMemberModal from '@/components/Modals/NewMemberModal.vue'
import type { CourseFormContext, Resource } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'
import type { CertificateDesignList } from '@/types/api'
import { describeDesign } from '@/utils/certificateDesigns'

/** The Access and certificate sections of the Options tab. */
const { resource, markDirty } = inject<CourseFormContext>('courseForm')!

const doc = computed(() => resource.doc!)
const evaluatorLinkRef = ref<{ reload: () => void } | null>(null)
const showMemberModal = ref<boolean>(false)
const showDesignDialog = ref<boolean>(false)

type Flag = 'upcoming' | 'featured' | 'enforce_lesson_completion'

function setFlag(field: Flag | 'disable_self_learning', value: boolean): void {
	;(doc.value as LMSCourse)[field] = value ? 1 : 0
	markDirty()
}

const flagRow = (field: Flag, label: string, summary: string) => ({
	label,
	summary,
	value: Boolean(doc.value[field]),
	set: (value: boolean) => setFlag(field, value),
})

const accessRows = computed(() => [
	{
		label: __('Self enrollment'),
		summary: doc.value.disable_self_learning
			? __('Off: you enroll people from the Dashboard.')
			: __('Learners enroll themselves.'),
		value: !doc.value.disable_self_learning,
		set: (value: boolean) => setFlag('disable_self_learning', !value),
	},
	flagRow(
		'enforce_lesson_completion',
		__('Lessons in sequence'),
		__('Each lesson opens only after the previous one is complete.')
	),
	flagRow(
		'upcoming',
		__('Upcoming'),
		__('Show the course before it opens. Learners can ask to be notified.')
	),
	flagRow(
		'featured',
		__('Featured'),
		__('Highlight the course on the homepage.')
	),
])

const hasCertificate = computed<boolean>(() =>
	Boolean(doc.value.enable_certification || doc.value.paid_certificate)
)

const timezoneResource = createResource({
	url: 'frappe.geo.country_info.get_country_timezone_info',
	auto: true,
	transform: (data: { all_timezones: string[] }) => data.all_timezones,
}) as Resource<string[] | null>

const timezoneOptions = computed<{ label: string; value: string }[]>(() =>
	(timezoneResource.data || []).map((zone) => ({ label: zone, value: zone }))
)

const certificateDesigns = createResource({
	url: 'lms.lms.api.get_certificate_designs',
	cache: 'certificateDesigns',
	auto: true,
}) as Resource<CertificateDesignList | null>

const certificateDesignLabel = computed<string>(() => {
	const design =
		doc.value.certificate_template || certificateDesigns.data?.default
	return design ? describeDesign(design).label : __('Site default')
})

function setCertificateDesign(design: string): void {
	doc.value.certificate_template = design
	markDirty()
}

function openEvaluatorModal(): void {
	showMemberModal.value = true
}

function onEvaluatorCreated(created: { name: string }): void {
	doc.value.evaluator = created.name
	evaluatorLinkRef.value?.reload()
	markDirty()
}
</script>
