<template>
	<SettingsLayout :title="title" :show-back="true" @back="requestBack">
		<template #title-badge>
			<Badge
				v-if="detail?.stale"
				variant="subtle"
				theme="orange"
				size="sm"
				:label="__('Stale')"
			/>
			<Badge
				v-if="form.dirty.value"
				variant="subtle"
				theme="orange"
				size="sm"
				:label="__('Not Saved')"
			/>
		</template>

		<template #header-actions>
			<Button
				variant="solid"
				:disabled="!form.canSubmit.value || form.locked.value"
				:loading="form.saving.value"
				:label="__('Save')"
				@click="form.save"
			/>
		</template>

		<div
			v-if="resource.loading && !detail && !isNew"
			class="flex h-full items-center justify-center"
		>
			<LoadingIndicator class="w-4" />
		</div>

		<template v-else-if="detail || isNew">
			<div class="grid shrink-0 grid-cols-1 items-start gap-5 md:grid-cols-2">
				<FormControl
					v-model="form.draft.label"
					type="text"
					size="sm"
					variant="subtle"
					:required="true"
					:label="__('Name')"
					:placeholder="__('Name')"
					:disabled="form.locked.value"
					maxlength="140"
				/>
				<FormControl
					v-model="form.draft.type"
					type="select"
					size="sm"
					variant="subtle"
					:required="true"
					:label="__('Visibility')"
					:options="visibilityOptions"
					:disabled="form.locked.value"
				/>
			</div>

			<Tabs
				v-model="tabIndex"
				as="div"
				:tabs="tabs"
				class="workspace-tabs mt-8"
			>
				<template #tab-panel="{ tab }">
					<div class="tab-panel-content mt-4">
						<WorkspaceChannels
							v-if="tab.label === tabs[0].label"
							:key="detail?.name ?? ''"
							:workspace="detail?.name ?? ''"
							:raven-workspace="detail?.raven_workspace"
							:unsaved="isNew"
							@open="(row) => emit('open-channel', row)"
							@new="emit('new-channel', detail?.name ?? '')"
						/>
						<WorkspaceMembers v-else :workspace="detail?.name ?? ''" />
					</div>
				</template>
			</Tabs>
		</template>

		<EmptyStateLayout
			v-else
			:name="__('Workspace')"
			:title="__('Could not load this workspace')"
			icon="lucide-messages-square"
			:description="
				__('It may have been deleted, or the request did not get through.')
			"
		>
			<Button
				variant="solid"
				:loading="resource.loading"
				:label="__('Retry')"
				@click="reload"
			/>
		</EmptyStateLayout>
	</SettingsLayout>

	<UnsavedChangesDialog v-model:open="leaveOpen" @confirm="leave" />
</template>

<script setup lang="ts">
// Workspace detail: CRM's SlaPolicyView shell around the tab set Raven's own
// ViewWorkspace.tsx uses. A record that does not exist yet is the same page, so
// the button never changes under the user and there is no Create.

// Name and Visibility sit above the tab strip because they describe the record
// rather than something it contains, which keeps the unsaved marker and Save on
// screen wherever you are. The draft lives in useWorkspaceGeneral.
import {
	Badge,
	Button,
	FormControl,
	LoadingIndicator,
	Tabs,
	createResource,
	toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import { useWorkspaceGeneral } from '@/composables/raven/useWorkspaceGeneral'
import UnsavedChangesDialog from './UnsavedChangesDialog.vue'
import WorkspaceChannels from './WorkspaceChannels.vue'
import WorkspaceMembers from './WorkspaceMembers.vue'
import type { MappingRow } from '@/composables/raven/useMappingList'
import type { WorkspaceDetail, WorkspaceVisibility } from '@/types'

// An empty name is the new-record page: nothing is written until Create is
// clicked. Clicking New in the list used to POST create_workspace, so an
// accidental click left a live Raven workspace behind.
const props = defineProps<{ name: string; label: string }>()
const emit = defineEmits<{
	back: []
	/** Saving a rename moves the mapping's docname; the owner has to adopt it. */
	renamed: [name: string]
	/** The docname Create produced. Adopted the same way a rename is, which is
	 *  what turns this page into the detail page for what was just made. */
	created: [name: string]
	// The Raven workspace id rides along because a channel's Raven URL is nested
	// under it, and the channel payload carries only its mapping's workspace.
	'open-channel': [row: MappingRow]
	/** Create on the Channels tab: a new-channel page, not a write. Carries the
	 *  workspace mapping's docname, which create_channel needs. */
	'new-channel': [workspace: string]
}>()

const isNew = computed<boolean>(() => !props.name)

const tabIndex = ref(0)

const VISIBILITIES: WorkspaceVisibility[] = ['Public', 'Private']

const visibilityOptions = VISIBILITIES.map((value) => ({
	label: __(value),
	value,
}))

// What the workspace *contains*. What it is, its name and its visibility, sits
// above the strip, and what can be done to the record itself lives on its row in
// the list, so there is no General tab holding one field and two buttons.
const tabs = [
	{ label: __('Channels'), icon: 'lucide-hash' },
	{ label: __('Members'), icon: 'lucide-users' },
]

// Three states, not two: in flight, loaded, and failed. onError only toasts, so
// a failed fetch leaves `data` null with `loading` false, and a spinner gated on
// the data alone would spin for as long as the tab is open.
const resource = createResource<WorkspaceDetail>({
	url: 'raven_integration.api.get_workspace',
	onError(err: { messages?: string[] }) {
		toast.error(err?.messages?.[0] ?? __('Could not load the workspace'))
	},
})

const detail = computed<WorkspaceDetail | null>(() => resource.data ?? null)

function reload(): void {
	if (isNew.value) return
	resource.submit({ name: props.name })
}

watch(() => props.name, reload, { immediate: true })

const title = computed<string>(() =>
	isNew.value
		? __('New Workspace')
		: detail.value?.workspace_label ?? props.label
)

const form = useWorkspaceGeneral(detail, reload, {
	onRenamed: (next) => emit('renamed', next),
	isNew: () => isNew.value,
	onCreated: (next) => emit('created', next),
})

// Going back with edits in hand asks first. A half-filled new record counts:
// `form.dirty` reads true on any typed name or changed visibility while there is
// no record behind the page.
const leaveOpen = ref(false)

function requestBack(): void {
	if (!form.dirty.value) {
		emit('back')
		return
	}
	leaveOpen.value = true
}

function leave(): void {
	leaveOpen.value = false
	emit('back')
}
</script>

<style scoped>
/* Only a tab's own row list scrolls, the Name/Visibility fields above the
   tabs, the tab strip, each tab's own heading row and its table's column
   header all stay in view. That used to mean one scroller for the whole page
   (see git history): frappe-ui's TabsRoot is `flex-1 overflow-hidden` and its
   panel `overflow-auto` by default, so letting the panel scroll dragged the
   Channels/Members heading away with the list, which read as broken on a long
   one. Disabling that nested scroll entirely fixed it, at the cost of the
   Name/Visibility fields and the tab strip scrolling away too on a long list
   worse for the same reason.
   Rather than re-enabling frappe-ui's panel scroll, the scroll is pushed one
   level deeper still, into SettingsTable's own row list
   (SettingsTable.vue), the one element that actually has nothing above it
   worth keeping in view. Every layer between here and there stays a bounded,
   non-scrolling flex column (`min-h-0` so it can shrink below its content,
   which `overflow: hidden` gets for free per spec) so the height it is given
   actually reaches that bottom layer instead of collapsing to content size. */
/* These two bound the height, which is what lets the row list below be the only
   thing that scrolls, take that away and the whole panel scrolls as one again.
   `overflow: hidden` is how they bound it, so it stays.
   What it must not do is clip a hovered row's surface. That surface is 12px
   wider than the content column on each side (SettingsTable's `-mx-3`, which is
   what lets it float free of its own text) and both these boxes sit on exactly
   that column, so either one is enough to slice it square, which is why only
   the tabs ever showed the cut, while the same table on Settings > Zoom and on
   the workspace list, neither inside a tab panel, always rounded correctly.
   The clip edge is the padding box, so widening that is enough and the clipping
   itself can stay strict: each takes 12px as padding and gives it back as a
   negative margin. The content box lands exactly where it did, the box that
   clips grows by the overhang, and the inner one still fits its parent's.
   `overflow: clip` with `overflow-clip-margin` reads as the tidier answer and is
   a trap, clip is not a scroll container, so the height stops being bounded and
   the panel scrolls as one again. */
.workspace-tabs,
.workspace-tabs :deep([role='tabpanel']) {
	margin-inline: -0.75rem;
	padding-inline: 0.75rem;
	overflow: hidden;
}

/* frappe-ui pins the tablist only when the panel asks for the room; this page's
   panels are intrinsically tall, so hold the strip at its content height. */
.workspace-tabs :deep([role='tablist']) {
	flex-shrink: 0;
	/* A horizontal tablist carries px-5 on top of its p-1 (frappe-ui Tabs.vue), so
	   the labels start 20px in, not the 4px p-1 alone suggests, and the cascade
	   gives px-5 the win. Zeroing the inline start padding is what actually puts
	   the first label on the container's edge, beside the header chevron and above
	   the panel. The strip's own border still spans the full width. */
	padding-inline-start: 0;
}

.tab-panel-content {
	display: flex;
	min-height: 0;
	flex: 1 1 auto;
	flex-direction: column;
}
</style>
