<template>
	<div
		class="flex w-full flex-col gap-2 rounded"
		:role="problem ? 'group' : undefined"
		:aria-labelledby="problem ? nameId : undefined"
		:aria-invalid="problem ? 'true' : undefined"
		:aria-describedby="problem ? problemMessageId : undefined"
	>
		<span :id="nameId" class="sr-only">{{ accessibleName }}</span>
		<span :id="typeWordId" class="sr-only">{{ __('Condition') }}</span>

		<div
			class="grid w-full grid-cols-1 items-start gap-2"
			:class="cellCount === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'"
			data-testid="condition-cells"
		>
			<div class="min-w-0" data-testid="condition-type">
				<Select
					v-if="!frozen"
					:model-value="rule.rule_type"
					:options="typeOptions"
					:placeholder="__('Condition')"
					:aria-labelledby="`${nameId} ${typeWordId}`"
					side="bottom"
					align="start"
					class="w-full"
					@update:model-value="setRuleType($event as string)"
				/>
				<p v-else class="pt-1 text-p-base text-ink-gray-7">{{ typeText }}</p>
			</div>

			<div
				v-for="field in slots.inline"
				:key="field.fieldname"
				class="min-w-0"
				data-testid="inline-field"
			>
				<span :id="wordId(field)" class="sr-only">{{ labelOf(field) }}</span>
				<RuleConditionField
					:field="field"
					:model-value="rule[field.fieldname]"
					:frozen="frozen"
					:aria-labelledby="`${nameId} ${wordId(field)}`"
					@update:model-value="setField(field, $event)"
				/>
			</div>
		</div>

		<div
			v-for="field in slots.blocks"
			:key="field.fieldname"
			class="flex w-full min-w-0 flex-wrap items-center gap-2"
			data-testid="block-field"
		>
			<span
				:id="wordId(field)"
				:class="
					frozen ? 'min-w-0 truncate text-p-base text-ink-gray-7' : 'sr-only'
				"
				>{{ labelOf(field) }}</span
			>
			<div class="min-w-0 flex-1 basis-56">
				<RuleConditionField
					:field="field"
					:model-value="rule[field.fieldname]"
					:frozen="frozen"
					:aria-labelledby="`${nameId} ${wordId(field)}`"
					@update:model-value="setField(field, $event)"
				/>
			</div>
		</div>

		<div
			v-if="foreign || paused"
			class="flex items-center gap-2"
			data-testid="row-status"
		>
			<Badge v-if="foreign" theme="gray" :label="managedByLabel" />
			<Badge v-if="paused" theme="orange" :label="__('Paused')" />
		</div>
	</div>
</template>

<script setup lang="ts">
// One condition row, rendered through ConditionBuilder's `#condition` slot. Our
// rule model is {provider, rule_type, config} rather than a field/operator/value
// triple, so providerSchema.conditionSlots bands the declared fields instead.

// Every control is named by `aria-labelledby`, the one attribute frappe-ui's
// Select passes through: it binds aria-invalid, aria-describedby and
// aria-errormessage after the caller's attrs and overwrites all three.

// The and/or cell, the overflow menu and the row's padding belong to
// ConditionBuilder. Drawing any of them here puts a second copy beside the real
// one, or floats the conjunction above the controls it joins.
import { Badge, Select } from 'frappe-ui'
import { computed, useId } from 'vue'
import RuleConditionField from './RuleConditionField.vue'
import {
	conditionSlots,
	defaultsOf,
	fieldsOf,
	isForeignRule,
	ruleTypesOf,
	useProviderDeclarations,
	useRuleTypeChoices,
	withoutHiddenFields,
} from '@/composables/raven/providerSchema'
import type { RuleProblem } from '@/composables/raven/useChannelRules'
import { LMS_PROVIDER } from '@/utils/raven/ruleAdapter'
import type {
	ProviderRuleType,
	RavenMemberRule,
	RuleField,
	RuleFieldValue,
} from '@/types'

interface Option {
	label: string
	value: string
}

const props = defineProps<{
	rule: RavenMemberRule
	/** Id of this row's name, owned by the host so its actions button shares it. */
	nameId: string
	/** Set when this is the row the section's warning is about. Marks it; the text
	 *  is not repeated here. */
	problem?: RuleProblem
	/** Id of the section's one warning, so a marked row can point at it. */
	problemMessageId?: string
	/** The builder's own read-only, handed down through the `#condition` slot. */
	readonly?: boolean
}>()

const emit = defineEmits<{ update: [rule: RavenMemberRule] }>()

const uid = useId()
const typeWordId = `${uid}-type`

const choices = useRuleTypeChoices()

const declarations = useProviderDeclarations()

// A rule renders in its own provider's vocabulary, so a foreign rule reads as
// what it is instead of being mistranslated into LMS terms.
const ruleTypes = computed<ProviderRuleType[]>(() =>
	ruleTypesOf(declarations.data, props.rule.provider ?? LMS_PROVIDER)
)

const foreign = computed<boolean>(() => isForeignRule(props.rule))

// A foreign rule is frozen for good, because its own app is where it is edited,
// and a read-only builder freezes every row. Only the first is a status, so
// only it badges the row.
const frozen = computed<boolean>(() => foreign.value || !!props.readonly)

const managedByLabel = computed<string>(() =>
	__('Managed by {0}', [props.rule.provider ?? ''])
)

// Stored as Paused, which raven_integration's engine reads as "skip this rule".
// This screen has no control that turns it back on, so the state is said rather
// than normalised away. See emitEdited.
const paused = computed<boolean>(() => props.rule.status === 'Paused')

// One flat list across every provider: choosing a condition is also what decides
// which provider will evaluate the rule.
const typeOptions = computed<Option[]>(() =>
	choices.value.map((choice) => ({
		label:
			choices.value.some((c) => c.provider !== choice.provider) &&
			choice.providerLabel
				? `${__(choice.label)} · ${choice.providerLabel}`
				: __(choice.label),
		value: choice.type,
	}))
)

const slots = computed(() =>
	conditionSlots(ruleTypes.value, props.rule.rule_type, props.rule)
)

// The type picker plus the cascade answers beside it. Three of them fit a line;
// more than that pairs up, so a four-cell cascade reads as two rows of two
// rather than three and an orphan.
const cellCount = computed<number>(() => slots.value.inline.length + 1)

function labelOf(field: RuleField): string {
	return __(field.label ?? field.fieldname)
}

// Per field, not per slot. The row used to have three fixed cells with three
// fixed words; a cascade has as many controls as it has levels, and each still
// needs its own accessible name.
function wordId(field: RuleField): string {
	return `${uid}-field-${field.fieldname}`
}

const typeText = computed<string>(
	() =>
		choices.value.find((c) => c.type === props.rule.rule_type)?.label ??
		props.rule.rule_type ??
		''
)

/**
 * What a row is called in a list of eight: its type, plus its status where it
 * has one. Read-only says nothing about this row that is not true of every
 * other, so it is left out here as it is left out of the badge.
 */
const accessibleName = computed<string>(() => {
	const parts = [typeText.value]
	if (foreign.value) parts.push(managedByLabel.value)
	if (paused.value) parts.push(__('Paused'))
	return parts.join(', ')
})

// Every edit leaves through here as a whole object, because a nested write into
// `rule` does not reach the tree the builder holds. The status is carried, never
// rewritten: stamping `Active` turned any edit into a membership change.
function emitEdited(rule: RavenMemberRule): void {
	emit('update', { ...rule })
}

// Through withoutHiddenFields, because this is the edit that can hide another
// field. Leaving one behind stored a scope the row no longer shows, and
// switching back reinstated it without the user re-entering it.
function setField(field: RuleField | null, value: RuleFieldValue): void {
	if (!field) return
	emitEdited(
		withoutHiddenFields(ruleTypes.value, {
			...props.rule,
			[field.fieldname]: value,
		})
	)
}

// Retyping keeps only what the new type also declares, or a leftover key would
// still be sent as config. Read off the provider that declares the NEW type:
// the picker lists every provider's, so a retype can cross providers.
function setRuleType(ruleType: string): void {
	const choice = choices.value.find((c) => c.type === ruleType)
	const provider = choice?.provider ?? props.rule.provider ?? LMS_PROVIDER
	const declared = ruleTypesOf(declarations.data, provider)
	const next: RavenMemberRule = {
		label: props.rule.label,
		provider,
		rule_type: ruleType,
		// Carried: retyping a row is not a decision to switch it back on.
		status: props.rule.status,
		matches: props.rule.matches,
		...defaultsOf(declared, ruleType),
	}
	for (const field of fieldsOf(declared, ruleType)) {
		const carried = props.rule[field.fieldname]
		if (carried !== undefined) next[field.fieldname] = carried
	}
	emitEdited(next)
}
</script>
