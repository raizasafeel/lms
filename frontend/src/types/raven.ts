// Wire format of the raven_integration API, plus the rule shapes the settings UI
// works in. Provider-agnostic only: a provider's own rule vocabulary stays in
// its app and crosses as `RavenMemberRule.rule_type`.

// This module stays free of runtime values, so the `@/types` barrel pulls no
// code into its importers' chunks. `RuleCombinator`'s runtime counterpart is
// `RULE_COMBINATORS` in `@/utils/raven/constants`.

/** What a group joins its children with. One per gap between two conditions. */
export type Conjunction = 'and' | 'or'
export type WorkspaceVisibility = 'Public' | 'Private'
export type ChannelVisibility = 'Public' | 'Private' | 'Open'
export type RuleStatus = 'Active' | 'Paused'

export interface RavenWorkspace {
	/** Mapping docname; null on an unmanaged Raven workspace with no mapping yet. */
	name: string | null
	/** False when this is a raw Raven workspace not yet adopted into a mapping. */
	mapped: boolean
	workspace_label: string
	workspace_type: WorkspaceVisibility
	/** Always present: the Raven workspace id, mapped or not; the adopt target. */
	raven_workspace: string
	/** The linked Raven workspace no longer exists; the mapping has stopped syncing. */
	stale: 0 | 1
	/** Channel mappings under this workspace; null when nothing is managed yet. */
	channel_count?: number | null
}

export interface RavenChannel {
	/** Mapping docname; null on an unmanaged Raven channel with no mapping yet. */
	name: string | null
	/** False when this is a raw Raven channel not yet adopted into a mapping. */
	mapped: boolean
	channel_label: string
	workspace: string
	channel_type: ChannelVisibility
	/** Always present: the Raven channel id, mapped or not; the adopt target. */
	raven_channel: string
	enabled: 0 | 1
	/** The linked Raven channel no longer exists; the mapping has stopped syncing. */
	stale: 0 | 1
}

export interface WorkspaceDetail extends RavenWorkspace {
	/** Derived: how many people are in at least one of the workspace's channels. */
	member_count: number
	channels_active: number
	channels_paused: number
	creation: string
}

/**
 * One row of `raven_integration.api.list_workspace_members`. Read-only by
 * construction, membership is a consequence of `channels`, not a stored fact.
 */
export interface WorkspaceMember {
	user: string
	full_name: string
	/** The User's avatar; null when they never set one. */
	user_image: string | null
	/** The channels that put this person in the workspace; never empty. */
	channels: string[]
	/** At least one of those channel memberships was created by a rule. */
	added_by_rule: boolean
}

export interface ChannelDetail extends RavenChannel {
	member_count: number
	/**
	 * The count above could not be worked out, so it reads 0 rather than a real
	 * total. An int with a flag beside it, so a consumer that ignores this still
	 * gets a number.
	 */
	member_count_unknown: boolean
	/** The channel's condition tree, exactly as ConditionBuilder models one. */
	rules: ApiRuleGroup
}

/**
 * A group of conditions as raven_integration stores one: joined by
 * `conjunctions`, one per gap. A child is a rule or another group, told apart
 * structurally, which is what lets the tree survive a JSON round-trip untouched.
 */
export interface ApiRuleGroup {
	conjunctions: Conjunction[]
	conditions: ApiRuleNode[]
}

export type ApiRuleNode = ApiRule | ApiRuleGroup

/**
 * The same tree as the editor holds one: every leaf flattened into the shape the
 * rule row edits, and one `conjunction` per group rather than one per gap, which
 * is ConditionBuilder's model. `ruleAdapter` converts at the boundary.
 */
export interface RuleGroup {
	conjunction: Conjunction
	conditions: RuleNode[]
	/**
	 * The per-gap joiners this group was loaded with, so a group the user never
	 * touched is written back as it was stored. A tree authored elsewhere can mix
	 * `and` with `or` at one level, which the single `conjunction` cannot say.
	 */
	storedConjunctions?: Conjunction[]
}

export type RuleNode = RavenMemberRule | RuleGroup

/** Child indices from the root of a tree. `[]` addresses the root itself. */
export type RulePath = number[]

/** Generic membership rule as the raven_integration API sends/accepts it on the wire. */
export interface ApiRule {
	name?: string
	label?: string
	provider: string
	rule_type: string
	status: RuleStatus
	config: Record<string, unknown>
	matches?: string
}

/** `raven_integration.api.is_setup` response. */
export interface RavenSetupState {
	raven: boolean
	raven_integration: boolean
	enabled: boolean
}

/** `raven_integration.api.compute_rule_diff` response. */
export interface RuleDiff {
	added: number
	removed: number
	removed_users: string[]
	/**
	 * No provider could evaluate the proposed tree, so the counts above are zero
	 * for want of an answer rather than because nobody moves. A channel that is
	 * switched off or stale reports zeros with this false.
	 */
	unknown: boolean
}

/** Every value a provider-declared field can hold. */
export type RuleFieldValue = string | string[] | number | null

/** One `fields[]` entry of a declared rule type. */
export interface RuleField {
	fieldname: string
	fieldtype: string
	/** On-screen wording; falls back to the fieldname when the provider omits it. */
	label?: string
	/** Declarable, but the condition row does not render it. See RuleConditionField. */
	description?: string
	/** A literal option list for `Select`; a doctype name for `MultiSelect`. */
	options?: string | string[]
	reqd?: 0 | 1
	default?: string
	/**
	 * Renders this field only while `field` holds one of the named values. `value`
	 * names one; `value_in` names a set, which is what a cascade needs when one
	 * scope applies to the same two multiselects that two others apply to singly.
	 */
	depends_on?:
		| { field: string; value: string }
		| { field: string; value_in: string[] }
}

export interface ProviderRuleType {
	type: string
	label?: string
	fields?: RuleField[]
}

/** One entry of the `raven_integration.api.list_providers` response. */
export interface ProviderDeclaration {
	name: string
	label?: string
	rule_types?: ProviderRuleType[]
}

export interface RavenMemberRule {
	name?: string
	label?: string
	/** Owning provider; absent on a rule this UI just created (defaults to LMS). */
	provider?: string
	rule_type: string
	status: RuleStatus
	/** Read-only human description from the backend (rules table "Matches" column). */
	matches?: string
	/** The provider's declared fields, flat; nested back under `config` on the wire. */
	[field: string]: RuleFieldValue | undefined
}
