import { onScopeDispose } from 'vue'

/*
 * Stack dialogs by the order they were opened, and expose only the top one.
 *
 * Every frappe-ui dialog overlay is z-index:auto and teleported to <body>, so
 * they paint in DOM order — and that is *anchor* order, not open order. Vue
 * places a Teleport's anchor when the component mounts, so Settings, mounted
 * with the sidebar at app start, is always first in <body> however late it
 * opens. No static z-index can fix it: Settings must sit above the dialog it was
 * opened from (a Link's "Create New" in the Create Program form) and below the
 * dialogs it opens (Users -> New Member). The two only agree on one rule — last
 * opened, top of the stack.
 *
 * The dialogs underneath stay in the DOM, so they also stay focusable and
 * readable: without this, tabbing out of Settings walks into the Create Program
 * form behind it, and a screen reader announces both at once. `inert` takes a
 * subtree out of the focus order and the accessibility tree in one go, which is
 * exactly the semantics a covered modal wants.
 */
const OVERLAY = '.dialog-overlay'

/*
 * A menu, select or combobox opened from inside a dialog. reka-ui teleports
 * one straight into <body> with `z-index: auto`, and giving the overlays an
 * explicit z-index is exactly what puts it behind them: a positioned element
 * at `auto` paints below one at `1` however late it was appended, and the
 * overlay is `fixed inset-0`, so it covers the menu entirely.
 *
 * These never enter the open-order stack. They sit one step above whichever
 * dialog is on top, which is the only dialog they can have been opened from —
 * every other one is inert.
 */
const POPPER = '[data-reka-popper-content-wrapper]'

/*
 * The popper's z-index cannot simply be assigned. reka writes `z-index: auto`
 * INLINE on that wrapper, and floating-ui rewrites the whole style object every
 * time it repositions, so anything set on `.style` is clobbered within a frame.
 *
 * An author `!important` rule outranks a normal inline declaration, which is
 * the one lever that survives. So the layer is carried on an attribute nothing
 * else writes, and a rule matching that attribute supplies the z-index. Vue's
 * style patching only removes style keys its own binding used to carry, and it
 * never touches an attribute it does not bind, so both stay put.
 */
const LAYER_ATTR = 'data-dialog-layer'
const STYLE_ID = 'dialog-layering'

// One rule per layer actually used, written with a literal value. A custom
// property would need only a single rule, but `var()` is the one part of this
// jsdom cannot resolve, and a mechanism that cannot be tested is a mechanism
// that quietly stops working.
const ruled = new Set<number>()

const sheet = (): HTMLStyleElement => {
	const found = document.getElementById(STYLE_ID)
	if (found) return found as HTMLStyleElement
	const style = document.createElement('style')
	style.id = STYLE_ID
	document.head.appendChild(style)
	// A fresh document (a test's, or a reload) has none of the rules the
	// previous one accumulated.
	ruled.clear()
	return style
}

const ensureLayerRule = (layer: number) => {
	if (ruled.has(layer)) return
	ruled.add(layer)
	sheet().textContent += `[${LAYER_ATTR}="${layer}"]{z-index:${layer} !important}`
}

// Open order, which DOM order does not give us. A WeakMap so a closed dialog's
// entry goes away with its node.
const openedAt = new WeakMap<HTMLElement, number>()
let opened = 0

// Two z-index steps per dialog, so a popper has an odd number of its own to sit
// on between its dialog and the next one opened above it.
const layerOf = (order: number) => order * 2

const bodyChildren = () =>
	[...document.body.children].filter(
		(el): el is HTMLElement => el instanceof HTMLElement
	)

const overlays = () => bodyChildren().filter((el) => el.matches(OVERLAY))

const poppers = () => bodyChildren().filter((el) => el.matches(POPPER))

const restack = () => {
	const open = overlays()

	// Nothing left: start the next stack from 1 again rather than let the
	// counter climb for the life of the page. A popper with no dialog under it
	// is back in the root stacking context, where DOM order already puts it on
	// top, so it is handed back its own `auto`.
	if (!open.length) {
		opened = 0
		for (const popper of poppers()) {
			popper.removeAttribute(LAYER_ATTR)
			popper.style.zIndex = ''
		}
		return
	}

	for (const overlay of open) {
		if (!openedAt.has(overlay)) {
			openedAt.set(overlay, ++opened)
			overlay.style.zIndex = String(layerOf(opened))
		}
	}

	// Only the newest dialog is interactive; everything under it is inert.
	const top = open.reduce((a, b) =>
		(openedAt.get(a) ?? 0) > (openedAt.get(b) ?? 0) ? a : b
	)
	for (const overlay of open) overlay.inert = overlay !== top

	// Fixed when the popper first appears, exactly as a dialog's own layer is.
	// A popper belongs to the dialog it was opened from, so a dialog opened
	// after it is a new top layer and has to come out above it — re-reading the
	// current top here would keep lifting the menu over the dialog that
	// replaced it.
	const ceiling = layerOf(openedAt.get(top) ?? 0)
	for (const popper of poppers()) {
		if (openedAt.has(popper)) continue
		openedAt.set(popper, opened)
		const layer = ceiling + 1
		ensureLayerRule(layer)
		popper.setAttribute(LAYER_ATTR, String(layer))
		// Belt and braces. The inline value is what holds until floating-ui's
		// next reposition rewrites the style object; the rule is what holds
		// after it.
		popper.style.zIndex = String(layer)
	}
}

export function useDialogLayering() {
	// Overlays are teleported straight into <body>, so its direct children are
	// the only place they appear — no subtree walk needed.
	sheet()
	const observer = new MutationObserver(restack)
	observer.observe(document.body, { childList: true })
	restack()
	onScopeDispose(() => observer.disconnect())
}
