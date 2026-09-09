<template>
	<header class="shrink-0 p-8 pb-0">
		<div class="flex items-start justify-between gap-4">
			<div class="flex min-w-0 flex-col gap-1">
				<div
					v-if="
						title ||
						$slots['title-badge'] ||
						saveState !== undefined ||
						unsaved !== undefined
					"
					class="flex min-h-5 items-center gap-2"
				>
					<Button
						v-if="showBack"
						variant="ghost"
						size="md"
						icon-left="lucide-chevron-left"
						:label="title"
						class="-ms-3.5 !max-w-96 !justify-start !pe-0 text-p-lg-semibold cursor-pointer hover:bg-transparent hover:opacity-70 focus:bg-transparent focus:outline-none focus:ring-0 active:bg-transparent active:text-ink-gray-5"
						@click="emit('back')"
					/>
					<h2 v-else-if="title" class="text-p-lg-semibold text-ink-gray-8">
						{{ title }}
					</h2>
					<slot name="title-badge" />
					<div
						v-if="saveState !== undefined || unsaved !== undefined"
						role="status"
						class="flex items-center"
					>
						<Badge
							v-if="marker"
							variant="subtle"
							:theme="marker.theme"
							:label="__(marker.label)"
						/>
					</div>
				</div>
				<p v-if="description" class="text-p-sm text-ink-gray-6 max-w-2xl">
					{{ description }}
				</p>
			</div>
			<div
				v-if="$slots.actions || enabled !== undefined"
				class="flex min-h-5 shrink-0 items-center gap-3"
			>
				<Switch
					v-if="enabled !== undefined"
					v-model="enabled"
					size="sm"
					:label="enabledLabel || __('Enabled')"
				/>
				<slot name="actions" />
			</div>
		</div>

		<div v-if="$slots.below" class="mt-4">
			<slot name="below" />
		</div>
	</header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge, Button, Switch } from 'frappe-ui'
import type { BadgeProps } from 'frappe-ui'
import type { AutosaveStatus } from '@/composables/useAutosave'

// The header of every settings panel, in two variants.
//
// **back** — the title itself is the control (CRM's EditEmailTemplate): a
// chevron and the label, no hover surface, pulled to the start so the label
// keeps the header's leading edge. Sub-pages use this.
//
// **plain** — an optional title, an optional description, and whatever the
// page needs in `#actions`: Save on a form, New on a list, Open the course on
// a detail page. Top-level panels use this.
//
// The title is optional in both: a panel whose sections all carry a heading of
// their own draws none, because the title and the first section heading sit at
// the same type token and would say the same thing twice. With no title the
// row goes entirely, unless a title-badge is slotted in — a marker belongs in
// the header whether or not there is a title beside it.
const props = defineProps<{
	title?: string
	description?: string
	/** Draws the title as a back control rather than a heading. */
	showBack?: boolean
	/** Marks the record as edited but not yet written. */
	unsaved?: boolean
	/** Set by a panel that writes on commit instead of on a Save button. */
	saveState?: AutosaveStatus
	/**
	 * Names the header switch when the record's state is not "enabled" — a
	 * payment is Received, not Enabled. Defaults to Enabled.
	 */
	enabledLabel?: string
}>()

const emit = defineEmits<{ back: [] }>()

// A record's own on/off state belongs beside the actions, not as the first
// field in the body. Undefined on panels with no such state, which hides it.
const enabled = defineModel<boolean | undefined>('enabled', {
	default: undefined,
})

// One status marker, drawn here and nowhere else so a panel that autosaves and
// a form that still has a Save button report themselves the same way. It is a
// frappe-ui Badge because that is how CRM reports the same thing on its own
// settings pages (`crm/.../Settings/SettingsPage.vue`: a subtle amber "Not
// Saved" beside the title) and how Helpdesk's UnsavedBadge does. Left
// untranslated: `__` belongs in the template, where the extractor looks for it.
//
// `error` gets its own word and its own colour rather than sharing amber with
// `dirty`. A failed write is not an unsaved edit, and since the write path
// raises no toast this badge is the only place the failure is ever reported —
// so it cannot be told apart by colour alone either.
//
// It sits beside the title rather than in the actions cluster, which is where
// CRM puts it too — between the Enabled switch and Save it read as a third
// control, and a status is not something you press.
//
// `idle` returns null and the badge goes, but its wrapper stays: it is the
// live region, and a region has to be in the DOM before its content changes
// for a screen reader to announce the change at all. `min-h-5` on the title
// row is what holds the height, so a marker appearing on every toggle does not
// push the body down and back each time.
const marker = computed<{ label: string; theme: BadgeProps['theme'] } | null>(
	() => {
		switch (props.saveState) {
			case 'saving':
				return { label: 'Saving…', theme: 'gray' }
			case 'saved':
				return { label: 'Saved', theme: 'green' }
			case 'error':
				return { label: 'Save failed', theme: 'red' }
			case 'dirty':
			case 'pending':
				return { label: 'Not saved', theme: 'amber' }
		}
		return props.unsaved ? { label: 'Not saved', theme: 'amber' } : null
	}
)
</script>
