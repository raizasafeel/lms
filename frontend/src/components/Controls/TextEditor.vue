<template>
	<div class="flex flex-col gap-1.5" :style="height ? { height } : null">
		<InputLabel
			v-if="label"
			:id="labelId"
			:label="label"
			:required="required"
		/>
		<div
			class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-outline-gray-2 bg-surface-gray-2 transition-colors hover:border-outline-gray-3 focus-within:border-outline-gray-4 focus-within:shadow-sm"
		>
			<div
				v-if="showFixedMenu"
				role="group"
				:aria-label="toolbarName"
				class="shrink-0 overflow-x-auto border-b border-outline-gray-2 px-2 py-1.5"
			>
				<EditorFixedMenu
					:editor="editor"
					:items="variantSpec.toolbar"
					class="flex-wrap"
				/>
			</div>
			<EditorBubbleMenu
				v-if="editable"
				:editor="editor"
				:items="variantSpec.bubbleToolbar"
			/>
			<EditorFloatingMenu
				v-if="editable && variantSpec.floatingToolbar"
				:editor="editor"
				:items="variantSpec.floatingToolbar"
			/>
			<EditorTableMenu
				v-if="editable && variantSpec.hasTables"
				:editor="editor"
			/>
			<EditorContent
				:editor="editor"
				:aria-labelledby="labelledBy"
				:aria-describedby="describedBy"
				:aria-required="required ? 'true' : null"
				:aria-invalid="hasError ? 'true' : null"
				:style="contentStyle"
				class="prose-sm min-h-0 max-w-none flex-1 overflow-y-auto px-2 py-1 text-ink-gray-8"
			/>
		</div>
		<InputDescription
			v-if="showDescription"
			:id="descriptionId"
			:description="description"
		/>
		<InputError v-if="hasError" :id="errorMessageId" :lines="errorLines" />
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useFileUpload } from 'frappe-ui'
import {
	EditorBubbleMenu,
	EditorContent,
	EditorFixedMenu,
	EditorFloatingMenu,
	EditorTableMenu,
	setPlaceholder,
	useEditor,
	type UploadedFile,
} from 'frappe-ui/editor'
import {
	InputDescription,
	InputError,
	InputLabel,
	useInputLabeling,
} from '@/components/Form/labeling'
import {
	resolveTextEditorVariant,
	type TextEditorFeatures,
	type TextEditorVariant,
} from '@/components/Controls/textEditorVariants'

const props = withDefaults(
	defineProps<{
		modelValue?: string | null
		variant?: TextEditorVariant
		features?: TextEditorFeatures | null
		label?: string
		description?: string
		error?: string | Error
		required?: boolean
		editable?: boolean
		placeholder?: string
		/** Fixes the control's height; the content region scrolls inside it. */
		height?: string | null
		/** Floor and ceiling for the content region, when the height is not fixed. */
		minHeight?: string | null
		maxHeight?: string | null
		uploadArgs?: Record<string, unknown> | null
		/** Names the toolbar's button group. Defaults to the field label. */
		toolbarLabel?: string
	}>(),
	{
		modelValue: '',
		variant: 'rich',
		features: null,
		label: '',
		description: '',
		required: false,
		editable: true,
		placeholder: '',
		height: null,
		minHeight: null,
		maxHeight: null,
		uploadArgs: null,
		toolbarLabel: '',
	}
)

const emit = defineEmits<{
	'update:modelValue': [value: string]
	change: [value: string]
	focus: [event: FocusEvent]
	blur: [event: FocusEvent]
}>()

const {
	labelId,
	labelledBy,
	descriptionId,
	errorMessageId,
	describedBy,
	hasError,
	errorLines,
	showDescription,
} = useInputLabeling(props)

// Resolved once, not as a computed: `useEditor` builds its extension list when
// it creates the editor, so a later variant change could not reach it. Nothing
// swaps a variant at runtime.
const variantSpec = resolveTextEditorVariant(
	props.variant,
	props.features ?? {}
)

// `group`, not `toolbar`. A toolbar role tells a screen reader the buttons are
// arrowed between, and frappe-ui's MenuItems renders plain tabbable buttons with
// no roving tabindex.
const showFixedMenu = computed(() => variantSpec.fixedMenu && props.editable)

const contentStyle = computed(() => {
	const style: Record<string, string> = {}
	if (props.minHeight) style.minHeight = props.minHeight
	if (props.maxHeight) style.maxHeight = props.maxHeight
	return style
})

// Callers pass translated strings, as they do to InputLabel and FormControl.
// Only the fallback is this component's own text to translate.
const toolbarName = computed(
	() => props.toolbarLabel || props.label || __('Formatting')
)

// Private by default so an image pasted into a body is not served from the
// unauthenticated /files/ path. `publicImageUploads.test.ts` pins this.
const fileUpload = useFileUpload()

async function uploadFile(file: File): Promise<UploadedFile> {
	// Spread rather than returned directly: useFileUpload's own UploadedFile is
	// an interface, which TS never grants the implicit index signature the
	// editor's own (looser) UploadedFile declares.
	const uploaded = await fileUpload.upload(file, {
		private: true,
		...(props.uploadArgs ?? {}),
	})
	return { ...uploaded }
}

const html = ref<string>(props.modelValue ?? '')
const hasFocus = ref(false)

const editor = useEditor({
	content: html,
	format: 'html',
	editable: () => props.editable,
	uploadFunction: uploadFile,
	extensions: variantSpec.extensions,
	onFocus: (_editor, event) => {
		hasFocus.value = true
		emit('focus', event)
	},
	onBlur: (_editor, event) => {
		hasFocus.value = false
		emit('blur', event)
	},
})

// After mount, not immediately: `setPlaceholder` dispatches a transaction, and
// `editor.view` throws until EditorContent has mounted the view.
onMounted(() => setPlaceholder(editor.value, props.placeholder || null))

watch(
	() => props.placeholder,
	(text) => setPlaceholder(editor.value, text || null)
)

watch(html, (value) => {
	if (value === (props.modelValue ?? '')) return
	emit('update:modelValue', value)
	emit('change', value)
})

watch(
	() => props.modelValue,
	(value) => {
		// A parent echoing back what was just typed would reset the caret.
		if (hasFocus.value) return
		if ((value ?? '') !== html.value) html.value = value ?? ''
	}
)

defineExpose({ editor })
</script>
