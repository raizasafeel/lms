// The one way out of settings and into Raven, as an entry both detail pages put
// in their header menu. It opens a tab rather than navigating, because either
// page may be sitting on an unsaved draft that a same-tab jump would discard.
import { openExternal } from '@/utils/openExternal'
import { ravenChannelUrl, ravenWorkspaceUrl } from './ravenUrl'
import type { DropdownOption } from '@/composables/raven/useMappingList'

export interface RavenTarget {
	/** The Raven workspace id. Absent on a mapping that was never adopted. */
	ravenWorkspace?: string | null
	/** The Raven channel id; leave it out entirely to address the workspace. */
	ravenChannel?: string | null
	/** The linked Raven record is gone, so there is nothing to open. */
	stale?: boolean
}

/** Empty when there is nothing to open, which is the caller's cue to offer nothing. */
export function ravenHref(target: RavenTarget): string {
	if (target.stale || !target.ravenWorkspace) return ''
	if (target.ravenChannel === undefined)
		return ravenWorkspaceUrl(target.ravenWorkspace)
	// An explicit null channel means "a channel was intended but is not there".
	if (!target.ravenChannel) return ''
	return ravenChannelUrl(target.ravenWorkspace, target.ravenChannel)
}

/**
 * The entry as a menu takes it, or nothing at all: a mapping with no Raven record
 * yet, or one whose record was deleted, would land on Raven's own 404.
 */
export function openInRavenOptions(target: RavenTarget): DropdownOption[] {
	const href = ravenHref(target)
	if (!href) return []
	return [
		{
			label: __('Open in Raven'),
			icon: 'lucide-external-link',
			// Through the helper, the app's only window.open: it passes `noopener` so
			// the opened page cannot reach back, and clears the href against the same
			// scheme allowlist every bound attribute uses.
			onClick: () => openExternal(href),
		},
	]
}
