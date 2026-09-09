/**
 * The feature sets `Controls/TextEditor.vue` can be put into. A variant picks a
 * frappe-ui kit, the kit options that differ from its defaults, and the
 * toolbars.
 */

// It never prunes a toolbar to match the kit. Every menu item carries
// `isAvailable`, so turning a capability off at the kit removes its button; the
// other way round would leave paste and drag-drop working behind no button.
import {
	AlignCenter,
	AlignLeft,
	AlignRight,
	Blockquote,
	Bold,
	BulletList,
	CommentKit,
	FontColor,
	FontHighlight,
	HeadingGroup,
	HorizontalRule,
	InlineCode,
	InlineKit,
	InsertIframe,
	InsertImage,
	InsertLink,
	InsertTable,
	InsertVideo,
	Italic,
	OrderedList,
	Redo,
	RichTextKit,
	Separator,
	Strike,
	Undo,
	useEditor,
	type CommandMenuItem,
	type MenuItem,
	type RichTextKitOptions,
	type TiptapEditor,
} from 'frappe-ui/editor'

export type TextEditorVariant = 'rich' | 'email' | 'comment' | 'inline'

/**
 * Kit members a caller may override on top of a variant. `RichTextKitOptions` is
 * the widest of the three kits' option types and its keys cover the other two.
 */
export type TextEditorFeatures = Partial<RichTextKitOptions>

type Extensions = Parameters<typeof useEditor>[0]['extensions']

const hasMark =
	(name: string) =>
	(editor: TiptapEditor): boolean =>
		name in editor.schema.marks

const hasNode =
	(name: string) =>
	(editor: TiptapEditor): boolean =>
		name in editor.schema.nodes

/*
 * Desk's Text Editor offers underline, code block and check lists. beta.24 ships
 * the extension for all three and a menu item for none, so they are defined
 * here, each driving a core tiptap command rather than the extension's own.
 */

export const Underline: CommandMenuItem = {
	label: 'Underline',
	icon: 'lucide-underline',
	action: (editor) => editor.chain().focus().toggleMark('underline').run(),
	isActive: (editor) => editor.isActive('underline'),
	isAvailable: hasMark('underline'),
}

export const CodeBlock: CommandMenuItem = {
	label: 'Code Block',
	icon: 'lucide-square-code',
	action: (editor) =>
		editor.chain().focus().toggleNode('codeBlock', 'paragraph').run(),
	isActive: (editor) => editor.isActive('codeBlock'),
	isAvailable: hasNode('codeBlock'),
}

export const TaskList: CommandMenuItem = {
	label: 'Task List',
	icon: 'lucide-list-checks',
	action: (editor) =>
		editor.chain().focus().toggleList('taskList', 'taskItem').run(),
	isActive: (editor) => editor.isActive('taskList'),
	isAvailable: hasNode('taskList'),
}

const RICH_TOOLBAR: MenuItem[] = [
	HeadingGroup,
	Separator,
	Bold,
	Italic,
	Underline,
	Strike,
	InlineCode,
	Separator,
	FontColor,
	FontHighlight,
	Separator,
	BulletList,
	OrderedList,
	TaskList,
	Blockquote,
	CodeBlock,
	Separator,
	AlignLeft,
	AlignCenter,
	AlignRight,
	Separator,
	InsertLink,
	InsertImage,
	InsertVideo,
	InsertTable,
	InsertIframe,
	HorizontalRule,
	Separator,
	Undo,
	Redo,
]

/**
 * Desk's default Text Editor toolbar, in its own order, which is what an Email
 * Template's `response` field renders today. Four of its buttons have no beta.24
 * equivalent: font size, remove formatting, RTL direction and indent.
 */
const EMAIL_TOOLBAR: MenuItem[] = [
	HeadingGroup,
	Separator,
	Bold,
	Italic,
	Underline,
	Strike,
	Separator,
	FontColor,
	FontHighlight,
	Separator,
	Blockquote,
	CodeBlock,
	Separator,
	InsertLink,
	InsertImage,
	Separator,
	OrderedList,
	BulletList,
	TaskList,
	Separator,
	AlignLeft,
	AlignCenter,
	AlignRight,
	Separator,
	InsertTable,
]

const COMMENT_TOOLBAR: MenuItem[] = [
	Bold,
	Italic,
	Strike,
	Separator,
	BulletList,
	OrderedList,
	Separator,
	InsertLink,
	InsertImage,
]

const INLINE_TOOLBAR: MenuItem[] = [Bold, Italic, InsertLink]

/** What a text selection offers, wherever the variant shows a bubble menu. */
const SELECTION_TOOLBAR: MenuItem[] = [
	Bold,
	Italic,
	Underline,
	Strike,
	InsertLink,
]

interface VariantSpec {
	kit: 'rich' | 'comment' | 'inline'
	defaults: TextEditorFeatures
	toolbar: MenuItem[]
	bubbleToolbar: MenuItem[]
	floatingToolbar: MenuItem[] | null
	fixedMenu: boolean
}

const VARIANTS: Record<TextEditorVariant, VariantSpec> = {
	rich: {
		kit: 'rich',
		defaults: {},
		toolbar: RICH_TOOLBAR,
		bubbleToolbar: SELECTION_TOOLBAR,
		floatingToolbar: RICH_TOOLBAR,
		fixedMenu: true,
	},
	email: {
		kit: 'rich',
		// A mail body has nobody to mention and no slash palette worth carrying,
		// and desk's editor offers neither. Video, attachment and iframe go with
		// them, or a drop would insert what no button offers.
		defaults: {
			slashCommands: false,
			mention: false,
			tag: false,
			emoji: false,
			toc: false,
			video: false,
			attachment: false,
			iframe: false,
		},
		toolbar: EMAIL_TOOLBAR,
		bubbleToolbar: SELECTION_TOOLBAR,
		floatingToolbar: null,
		fixedMenu: true,
	},
	comment: {
		kit: 'comment',
		defaults: {},
		toolbar: COMMENT_TOOLBAR,
		bubbleToolbar: COMMENT_TOOLBAR,
		floatingToolbar: null,
		fixedMenu: true,
	},
	inline: {
		kit: 'inline',
		defaults: {},
		toolbar: INLINE_TOOLBAR,
		bubbleToolbar: INLINE_TOOLBAR,
		floatingToolbar: null,
		fixedMenu: false,
	},
}

export interface ResolvedTextEditorVariant {
	extensions: Extensions
	toolbar: MenuItem[]
	bubbleToolbar: MenuItem[]
	floatingToolbar: MenuItem[] | null
	fixedMenu: boolean
	hasTables: boolean
}

export function resolveTextEditorVariant(
	variant: TextEditorVariant,
	features: TextEditorFeatures = {}
): ResolvedTextEditorVariant {
	const spec = VARIANTS[variant]
	const options: TextEditorFeatures = { ...spec.defaults, ...features }

	const kit =
		spec.kit === 'rich'
			? RichTextKit.configure(options)
			: spec.kit === 'comment'
			? CommentKit.configure(options)
			: InlineKit.configure(options)

	// RichTextKit loads tables by default and CommentKit does not, so an untouched
	// `table` means different things per kit. InlineKit has no table member at all.
	const tableByDefault = spec.kit === 'rich'
	const hasTables =
		spec.kit === 'inline'
			? false
			: options.table === undefined
			? tableByDefault
			: options.table !== false

	return {
		extensions: [kit],
		toolbar: spec.toolbar,
		bubbleToolbar: spec.bubbleToolbar,
		floatingToolbar: spec.floatingToolbar,
		fixedMenu: spec.fixedMenu,
		hasTables,
	}
}
