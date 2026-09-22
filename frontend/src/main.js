import './index.css'
import { createApp, watch } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'
import dayjs from '@/utils/dayjs'
import { createDialog } from '@/utils/dialogs'
import translationPlugin from './translation'
import { usersStore } from './stores/user'
import { initSocket } from './socket'
import { FrappeUI, setConfig, frappeRequest, pageMetaPlugin } from 'frappe-ui'
import { telemetryPlugin } from 'frappe-ui/frappe'
import { registerDirectives } from './directives'

let pinia = createPinia()
let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(FrappeUI)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
app.use(pageMetaPlugin)
registerDirectives(app)
app.provide('$dayjs', dayjs)
app.provide('$socket', initSocket())
app.mount('#app')

const { userResource, allUsers } = usersStore()
app.provide('$user', userResource)
app.provide('$allUsers', allUsers)

// Installed once, on the first resolved user. `watch` fires on every mutation of
// the resource, and each install refetches the telemetry boot config and rebuilds
// the Pulse client, so without the guard a few navigations cost a handful of
// pointless round trips.
let telemetryInstalled = false
watch(userResource, () => {
	if (userResource.data && !telemetryInstalled) {
		telemetryInstalled = true
		// Passing the router turns on Pulse's own pageview capture, one event per
		// navigation, scrubbed to the matched route pattern rather than the URL
		// (so `/courses/:courseName`, never a course name). frappe-ui limits it to
		// sites under 15 days old, which is the window the drop-off we are chasing
		// happens in, and it is the only way to see which screens a site reaches
		// before it stops coming back.
		app.use(telemetryPlugin, { app_name: 'lms', router })
	}
})

app.config.globalProperties.$user = userResource
app.config.globalProperties.$dialog = createDialog
