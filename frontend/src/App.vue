<template>
	<FrappeUIProvider>
		<Layout class="isolate text-p-base">
			<router-view :route="background" />
		</Layout>
		<router-view v-if="background" />
		<NotificationPanel />
		<InstallPrompt v-if="isMobile && !settings.data?.disable_pwa" />
		<Dialogs />
	</FrappeUIProvider>
</template>
<script setup>
import { FrappeUIProvider } from 'frappe-ui'
import { Dialogs } from '@/utils/dialogs'
import { computed } from 'vue'
import { useScreenSize } from './utils/composables'
import { useSettings } from '@/stores/settings'
import { useRoute, useRouter } from 'vue-router'
import { formBackgroundPath } from '@/composables/useFormRoute'
import { useDialogLayering } from '@/composables/dialogLayering'
import DesktopLayout from './components/Layouts/pages/desktop/DesktopLayout.vue'
import MobileLayout from './components/Layouts/pages/mobile/MobileLayout.vue'
import NoSidebarLayout from './components/Layouts/pages/desktop/NoSidebarLayout.vue'
import InstallPrompt from './components/InstallPrompt.vue'
import NotificationPanel from '@/components/Notifications/NotificationPanel.vue'

const { isMobile } = useScreenSize()
const route = useRoute()

// Settings is mounted with the sidebar at app start, so its teleport anchor is
// always first in <body> however late it opens. Order the overlays by when they
// were opened instead, and make the covered ones inert.
useDialogLayering()
const router = useRouter()
const { settings } = useSettings()

const isAncestorOfCurrent = (resolved) =>
	resolved.matched.length <= route.matched.length &&
	resolved.matched.every((record, index) => route.matched[index] === record)

const isLoaded = (resolved) =>
	resolved.matched.every((record) =>
		Object.values(record.components ?? {}).every(
			(component) => typeof component !== 'function'
		)
	)

// A form route renders a Dialog. Reaching it is a real navigation, so without
// this the page it was opened from unmounts and the dialog floats over a blank
// app. openFormRoute stamps the location it left into history.state; when one
// is stamped the router-view inside the Layout is told to render THAT location
// (RouterView's `route` prop — the supported mechanism) and a second
// router-view renders the current route, the modal, on top of it.
//
// history.state is a plain object vue-router swaps out per navigation and never
// makes reactive, so touching `route.fullPath` first is what re-runs this: the
// current route changes on every navigation, and vue-router writes the new
// entry's state BEFORE it assigns currentRoute, so the state read here always
// belongs to the route we just landed on. Reading it through the router rather
// than window.history is what keeps it working under createMemoryHistory, which
// never touches window.history at all.
const background = computed(() => {
	void route.fullPath
	const stored = formBackgroundPath(router)
	if (!stored) return undefined

	const resolved = router.resolve(stored)
	// A background that no longer matches anything real would paint the 404 page
	// under the dialog.
	if (!resolved.matched.length || resolved.name === 'NotFound') {
		return undefined
	}
	// Never render the modal twice.
	if (resolved.fullPath === route.fullPath) return undefined
	// Most form routes are CHILDREN of the page that opens them, so the page is
	// already mounted as the modal's own ancestor; rendering it here as well
	// would draw the list twice.
	if (isAncestorOfCurrent(resolved)) return undefined
	// Only pages whose lazy chunk is already loaded can be rendered
	// synchronously. Awaiting the import instead would blank the layout for a
	// tick and remount the very page this exists to keep mounted. Unloaded is
	// the reload case (web history keeps the stamp across an F5), which then
	// behaves exactly like a cold deep link: the modal stands alone.
	if (!isLoaded(resolved)) return undefined

	return resolved
})

// The Layout wraps the background when there is one, so it is that page — not
// the modal floating above it — that decides whether a sidebar belongs here.
const layoutRoute = computed(() => background.value ?? route)

// Derive the layout from the route, not a navigation guard. Flipping it in
// beforeEach swaps the layout the instant a navigation starts (before a lazy
// route component resolves), which re-mounts <router-view> while the old page is
// still showing, flashing it back into view. A route-driven computed changes in
// the same tick as the route, so the swap and the page change happen together.
const noSidebar = computed(
	() =>
		Boolean(layoutRoute.value.query.fromLesson) ||
		layoutRoute.value.path === '/persona'
)

const Layout = computed(() => {
	if (noSidebar.value) {
		return NoSidebarLayout
	}
	if (isMobile.value) {
		return MobileLayout
	}
	return DesktopLayout
})
</script>
