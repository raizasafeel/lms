import { onScopeDispose } from 'vue'

/*
 * Stack dialogs by the order they were opened, and expose only the top one.
 * Every frappe-ui overlay is z-index:auto and teleported to <body>, so they paint
 * in anchor order rather than open order. The ones underneath are made `inert`.
 */
const OVERLAY = '.dialog-overlay'

/*
 * A menu, select or combobox opened from inside a dialog. reka teleports one
 * into <body> at `z-index: auto`, which paints below the overlays. These never
 * enter the open-order stack; they sit one step above whichever dialog is top.
 */
const POPPER = '[data-reka-popper-content-wrapper]'

/*
 * The popper's z-index cannot simply be assigned. reka writes `z-index: auto`
 * inline, and floating-ui rewrites the style object on every reposition. An
 * author `!important` rule keyed off an attribute is the one lever that survives.
 */
const LAYER_ATTR = 'data-dialog-layer'

/*
 * reka gives every dismissable layer below the top one `pointer-events: none`,
 * so a click inside a dialog holding an open menu lands on the live overlay and
 * dismisses the dialog. Handing the content back its pointer events fixes it.
 */
const INTERACTIVE_ATTR = 'data-dialog-interactive'
const STYLE_ID = 'dialog-layering'

// One rule per layer actually used, written with a literal value. A custom
// property would need only one rule, but `var()` is the one part of this jsdom
// cannot resolve.
const ruled = new Set<number>()

const sheet = (): HTMLStyleElement => {
	const found = document.getElementById(STYLE_ID)
	if (found) return found as HTMLStyleElement
	const style = document.createElement('style')
	style.id = STYLE_ID
	style.textContent = `[${INTERACTIVE_ATTR}]{pointer-events:auto !important}`
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
// entry goes away with its node. The counter only ever climbs: it orders the
// open set rather than naming a layer, so restarting it would let an overlay
// that outlived its dialog take the same number as one opened later.
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

	// A popper with no dialog under it is back in the root stacking context and is
	// handed back its own `auto`.
	if (!open.length) {
		for (const popper of poppers()) {
			popper.removeAttribute(LAYER_ATTR)
			popper.style.zIndex = ''
		}
		return
	}

	for (const overlay of open) {
		if (!openedAt.has(overlay)) openedAt.set(overlay, ++opened)
	}

	// Layers come from the rank inside the open set, not from the open number
	// itself, so an overlay left behind by a dialog that has gone cannot tie with
	// a dialog opened after it and win the tie on document order.
	const ordered = [...open].sort(
		(a, b) => (openedAt.get(a) ?? 0) - (openedAt.get(b) ?? 0)
	)
	ordered.forEach((overlay, rank) => {
		overlay.style.zIndex = String(layerOf(rank + 1))
	})

	// Only the newest dialog is interactive; everything under it is inert.
	const top = ordered[ordered.length - 1]
	for (const overlay of open) overlay.inert = overlay !== top

	// An open menu turns the dialog holding it off along with everything else
	// below the top layer. Hand that one its pointer events back.
	const menuOpen = poppers().length > 0
	for (const overlay of open) {
		const content = overlay.querySelector('[role="dialog"]')
		if (!(content instanceof HTMLElement)) continue
		if (menuOpen && overlay === top) content.setAttribute(INTERACTIVE_ATTR, '')
		else content.removeAttribute(INTERACTIVE_ATTR)
	}

	// Fixed when the popper first appears, exactly as a dialog's own layer is. A
	// popper belongs to the dialog it was opened from, so re-reading the current
	// top would keep lifting the menu over whichever dialog replaced it.
	const ceiling = layerOf(ordered.length)
	for (const popper of poppers()) {
		if (openedAt.has(popper)) continue
		openedAt.set(popper, opened)
		const layer = ceiling + 1
		ensureLayerRule(layer)
		popper.setAttribute(LAYER_ATTR, String(layer))
		// Belt and braces. The inline value holds until floating-ui's next
		// reposition rewrites the style object; the rule holds after it.
		popper.style.zIndex = String(layer)
	}
}

/*
 * The click that now lands inside the dialog still has to close the menu, which
 * it cannot do on its own: DialogContent stops `pointerdown` before reka's
 * document listener sees it. So the dismissal is sent explicitly.
 */
const dismissMenu = (event: Event) => {
	const target = event.target
	if (!(target instanceof Element)) return
	if (!poppers().length) return
	if (target.closest(POPPER)) return
	if (!target.closest(`[${INTERACTIVE_ATTR}]`)) return
	document.dispatchEvent(
		new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
	)
}

export function useDialogLayering() {
	// Overlays are teleported straight into <body>, so its direct children are
	// the only place they appear, and no subtree walk is needed.
	sheet()
	const observer = new MutationObserver(restack)
	observer.observe(document.body, { childList: true })
	restack()
	// Capture, so it runs before DialogContent swallows the event.
	document.addEventListener('pointerdown', dismissMenu, true)
	onScopeDispose(() => {
		observer.disconnect()
		document.removeEventListener('pointerdown', dismissMenu, true)
	})
}
