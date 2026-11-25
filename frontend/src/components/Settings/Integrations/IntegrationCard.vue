<template>
	<div
		class="flex flex-col gap-3 rounded-6 border border-outline-gray-2 p-4"
		:class="enabled ? 'bg-surface-base' : 'bg-surface-gray-1'"
		:data-testid="`integration-${integration.key}`"
		:data-enabled="enabled ? 'true' : 'false'"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="flex min-w-0 items-center gap-3">
				<div
					class="flex size-9 shrink-0 items-center justify-center rounded-5 border border-outline-gray-2 bg-surface-base"
				>
					<span
						:class="[
							integration.icon,
							'size-4.5',
							enabled ? 'text-ink-gray-8' : 'text-ink-gray-6',
						]"
					/>
				</div>
				<h3
					class="truncate text-p-base-medium"
					:class="enabled ? 'text-ink-gray-8' : 'text-ink-gray-6'"
				>
					{{ __(integration.label) }}
				</h3>
			</div>
			<Tooltip v-if="!install" :text="lockedReason" :disabled="!lockedReason">
				<span>
					<Switch
						size="sm"
						:model-value="enabled"
						:disabled="Boolean(lockedReason)"
						:aria-label="__('Enable {0}').format(__(integration.label))"
						@update:model-value="(value: boolean) => emit('toggle', value)"
					/>
				</span>
			</Tooltip>
		</div>
		<p class="text-p-sm text-ink-gray-6">{{ __(integration.description) }}</p>
		<div class="mt-auto flex items-center justify-between gap-3">
			<Button
				v-if="status.action && !install"
				size="sm"
				:label="status.action.label"
				:tooltip="status.label"
				data-testid="integration-action"
				@click="emit('action', status.action)"
			>
				<template #prefix>
					<span class="lucide-circle-alert size-4 text-ink-amber-6" />
				</template>
			</Button>
			<span
				v-else
				class="truncate text-p-sm"
				:class="status.warning ? 'text-ink-amber-8' : 'text-ink-gray-6'"
				data-testid="integration-status"
			>
				{{ status.label }}
			</span>
			<Button
				v-if="install"
				size="sm"
				:label="__(install.action)"
				data-testid="integration-install"
				@click="emit('install')"
			>
				<template #suffix>
					<span class="lucide-arrow-up-right size-3.5" />
				</template>
			</Button>
			<div v-else class="flex shrink-0 items-center gap-2">
				<Button
					v-if="integration.configure && status.action?.opens !== 'configure'"
					size="sm"
					:label="__('Configure')"
					:disabled="!canConfigure"
					data-testid="integration-configure"
					@click="emit('configure')"
				/>
				<Button
					v-if="integration.records && status.action?.opens !== 'records'"
					size="sm"
					:label="__(integration.records.label)"
					:disabled="!canOpenRecords"
					data-testid="integration-records"
					@click="emit('openRecords')"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Switch, Tooltip } from 'frappe-ui'
import type {
	CardAction,
	CardLine,
	Integration,
	MissingApp,
} from './integrations'

defineProps<{
	integration: Integration
	enabled: boolean
	status: CardLine
	/** Why the switch is locked, or '' when it can be flipped. */
	lockedReason: string
	/** The next app to install, shown in place of the switch and pages. */
	install: MissingApp | null
	canConfigure: boolean
	canOpenRecords: boolean
}>()

const emit = defineEmits<{
	toggle: [value: boolean]
	install: []
	configure: []
	openRecords: []
	action: [action: CardAction]
}>()
</script>
