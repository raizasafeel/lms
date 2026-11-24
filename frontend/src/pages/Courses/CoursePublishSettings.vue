<template>
	<SettingsGroup :title="__('Access')" icon="lucide-door-open">
		<SettingSwitch
			v-for="row in accessRows"
			:key="row.label"
			:label="row.label"
			:summary="row.summary"
			:modelValue="row.value"
			@update:modelValue="row.set"
		/>
	</SettingsGroup>

	<PeopleGroup
		v-model="people"
		doctype="LMS Course"
		:name="doc.name"
		:owner="doc.owner"
		:canChangeOwner="canChangeOwner"
		@ownerChanged="(owner) => (doc.owner = owner)"
	/>

	<EvaluationGroup
		v-model:people="people"
		v-model:enabled="evaluated"
		v-model:format="doc.evaluation_format"
		v-model:duration="doc.evaluation_duration"
		doctype="LMS Course"
		@update:format="markDirty()"
		@update:duration="markDirty()"
	>
		<SettingField
			v-model="doc.timezone"
			type="combobox"
			:label="__('Timezone')"
			:summary="__('Evaluation slots are shown in this timezone.')"
			:options="timezoneOptions"
			:placeholder="__('Select timezone')"
			@update:modelValue="markDirty()"
		/>
		<template #certificate>
			<SettingSwitch
				:modelValue="Boolean(doc.enable_certification)"
				:label="__('Issue automatically on completion')"
				:summary="__('Learners press Get certificate after finishing.')"
				@update:modelValue="setAutomatic"
			/>
			<SettingAction
				v-if="hasCertificate"
				:label="__('Certificate design')"
				:summary="certificateDesignLabel"
				:action="__('Change')"
				@click="showDesignDialog = true"
			/>
		</template>
	</EvaluationGroup>

	<CertificateDesignDialog
		v-if="showDesignDialog"
		v-model:open="showDesignDialog"
		:course="doc.name"
		:courseTitle="doc.title"
		:current="doc.certificate_template || null"
		@select="setCertificateDesign"
	/>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import SettingAction from '@/components/InlineEdit/SettingAction.vue'
import SettingField from '@/components/InlineEdit/SettingField.vue'
import SettingSwitch from '@/components/InlineEdit/SettingSwitch.vue'
import SettingsGroup from '@/components/InlineEdit/SettingsGroup.vue'
import CertificateDesignDialog from '@/components/Modals/CertificateDesignDialog.vue'
import EvaluationGroup from '@/components/InlineEdit/People/EvaluationGroup.vue'
import PeopleGroup from '@/components/InlineEdit/People/PeopleGroup.vue'
import type { CourseFormContext, Resource, SessionUser } from '@/types'
import type { PersonRow } from '@/types/lms/LMSRoleAssignment'
import type { LMSCourse } from '@/types/lms/LMSCourse'
import type { CertificateDesignList } from '@/types/api'
import { describeDesign } from '@/utils/certificateDesigns'

/** The Access, People and evaluation sections of the Settings tab. */
const form = inject<CourseFormContext>('courseForm')!
const { resource, markDirty } = form
const user = inject<SessionUser>('$user')!

const doc = computed(() => resource.doc!)
const showDesignDialog = ref<boolean>(false)

const people = computed<PersonRow[]>({
	get: () => form.people.value,
	set: (rows) => {
		form.people.value = rows
		markDirty()
	},
})

const canChangeOwner = computed<boolean>(() =>
	Boolean(user.data?.is_moderator || user.data?.name === doc.value.owner)
)

// An evaluated certificate is the course's paid certificate; the automatic one is free.
const evaluated = computed<boolean>({
	get: () => Boolean(doc.value.paid_certificate),
	set: (on) => {
		doc.value.paid_certificate = on ? 1 : 0
		if (on) doc.value.enable_certification = 0
		markDirty()
	},
})

function setAutomatic(on: boolean): void {
	doc.value.enable_certification = on ? 1 : 0
	if (on) doc.value.paid_certificate = 0
	markDirty()
}

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
</script>
