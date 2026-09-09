<template>
	<div class="relative flex h-dvh flex-col">
		<a
			href="#scrollContainer"
			@click.prevent="skipToContent('scrollContainer')"
			class="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded focus:bg-surface-base focus:px-4 focus:py-2 focus:text-ink-gray-9 focus:shadow-md focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
		>
			{{ __('Skip to main content') }}
		</a>
		<main
			class="flex min-h-0 flex-1 flex-col overflow-y-auto focus:outline-none"
			id="scrollContainer"
			tabindex="-1"
		>
			<slot />
		</main>

		<div class="relative z-20 shrink-0">
			<nav
				v-if="!isSignedIn || sidebarSettings.data"
				:aria-label="__('Primary')"
				class="pb-safe-0 z-10 flex w-full items-stretch border-t border-outline-gray-2 bg-surface-base"
			>
				<button
					v-for="tab in primaryTabs"
					:key="tab.label"
					type="button"
					:aria-current="isActive(tab) ? 'page' : undefined"
					class="flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 py-2"
					@click="handleClick(tab)"
				>
					<Avatar
						v-if="tab.avatar"
						aria-hidden="true"
						data-testid="you-tab-avatar"
						:image="userResource.data?.user_image"
						:label="userResource.data?.full_name || __('You')"
						size="md"
						class="shrink-0"
						:class="[isActive(tab) ? 'ring-2 ring-outline-gray-5' : '']"
					/>
					<component
						v-else
						:is="icons[tab.icon]"
						class="h-6 w-6 stroke-1.5"
						:class="[isActive(tab) ? 'text-ink-gray-9' : 'text-ink-gray-5']"
						aria-hidden="true"
					/>
					<span
						class="max-w-full break-words text-center text-p-xs"
						:class="[
							isActive(tab) ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5',
						]"
					>
						{{ __(tabLabel(tab.label)) }}
					</span>
				</button>
			</nav>
		</div>
	</div>
</template>
<script setup>
// The frame is `h-dvh`, not `h-screen`: 100vh is the URL-bar-retracted viewport,
// so the tab bar would sit below the visible area on a phone, and nothing above
// main scrolls, so the browser never retracts the bar.

// `main` is `min-h-0` so the flex child can shrink and scroll its own overflow.
// Padding cannot do that job, because Chromium drops a flex column's bottom
// padding from the scrollable area and the last row stays hidden.
import { skipToContent } from '@/utils/a11y'
import { useRouter } from 'vue-router'
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { sessionStore } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { usersStore } from '@/stores/user'
import * as icons from 'lucide-vue-next'
import { Avatar } from 'frappe-ui'
import { ensureMobileNavLinks, sidebarLinks } from '@/stores/mobileNavLinks'
import { pickPrimaryTabs, tabLabel } from '@/utils/mobileNav'

const { isLoggedIn } = storeToRefs(sessionStore())
const settingsStore = useSettings()
const { sidebarSettings } = settingsStore
const router = useRouter()
let { userResource } = usersStore()
const isModerator = ref(false)
const isInstructor = ref(false)
const isEvaluator = ref(false)

const isSignedIn = computed(
	() => isLoggedIn.value || Boolean(userResource.data)
)

// Five real routes and no overflow affordance. Whatever the bar does not hold is
// reached from the You page.

// The captions wrap rather than `truncate`, because `text-p-xs` is a fixed
// 12px inside a viewport-proportional column, so under OS text scaling an
// ellipsis would eat half the word with no way to read the rest (WCAG 1.4.4).
const primaryTabs = computed(() =>
	pickPrimaryTabs(sidebarLinks.value, isSignedIn.value, sidebarSettings.data)
)

// The active You tab rings its avatar with `ring-outline-gray-5`. The token has
// to come from the `outline-*` family: frappe-ui extends `ringColor` with
// `outline` only, so an `ink-*` ring falls back to Tailwind's stock blue.

// gray-5 rather than Gameplan's gray-4, because this ring is the only
// indicator here that WCAG 1.4.11 counts, and gray-4 measures 2.85:1 against
// `surface-base` where gray-5 reaches 4.17.

// The links live in `stores/mobileNavLinks`, because the You page lists the
// same set. Both watchers below announce a viewer rather than commanding a
// load, and `ensureMobileNavLinks` turns their repeats into one run.
const updateSidebarLinks = () =>
	ensureMobileNavLinks({
		isSignedIn: isSignedIn.value,
		isModerator: isModerator.value,
		isInstructor: isInstructor.value,
		isEvaluator: isEvaluator.value,
		hasUserInfo: Boolean(userResource.data),
	})

watch(
	userResource,
	async () => {
		await userResource.promise
		if (userResource.data) {
			isModerator.value = userResource.data.is_moderator
			isInstructor.value = userResource.data.is_instructor
			isEvaluator.value = userResource.data.is_evaluator
		}
		updateSidebarLinks()
	},
	{ immediate: true }
)

watch(() => sidebarSettings.data, updateSidebarLinks, { deep: true })

// Against the whole matched chain, not just the leaf name. A tab may point at a
// parent route that redirects to a child, so the leaf never equals the tab's
// own name and it could never light up.
let isActive = (tab) => {
	if (!tab.activeFor?.length) return false
	return router.currentRoute.value.matched.some((route) =>
		tab.activeFor.includes(route.name)
	)
}

// Every tab is a route, because the session actions live on the You page. Log
// in is the one exception, leaving the SPA for Frappe's own /login.
const handleClick = (tab) => {
	if (tab.label == 'Log in') window.location.href = '/login'
	else router.push({ name: tab.to })
}
</script>
