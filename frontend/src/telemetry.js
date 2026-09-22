/**
 * Browser-side product telemetry.
 *
 * `useTelemetry().capture` from frappe-ui posts an event straight to Pulse. This
 * module is the one place the app calls it from, so that:
 *
 *  - every event carries the same standing context (the actor's role, and
 *    whether they are on a phone), which is what turns a count into something
 *    that can be compared between the people building a site and the people
 *    learning on it.
 *  - a screen that can be opened repeatedly does not report itself repeatedly.
 *    `captureOnce` keeps one event per page load, which is the unit that
 *    "did this site ever open the payment settings?" is actually asked in.
 *
 * Properties are flat, lower_snake_case, and never carry a title, an email or
 * anything else a person typed. Server-side events (lms/telemetry.py) also carry
 * the site's onboarding persona; join the two on the `site` column that every
 * Pulse event has.
 */
import { useTelemetry } from 'frappe-ui/frappe'
import { usersStore } from '@/stores/user'

// Events already sent this page load, for captureOnce. Cleared by a reload,
// which is the point: it counts sessions, not clicks.
const seen = new Set()

const MOBILE_BREAKPOINT = 640

/**
 * Send one product event.
 *
 * Never throws: an analytics call is not worth breaking a screen over, and this
 * runs inside success handlers that have real work after them.
 */
export function captureEvent(event, properties = {}) {
	try {
		const { capture } = useTelemetry()
		capture(event, { ...commonProperties(), ...properties })
	} catch (error) {
		// Telemetry is disabled, or the store is not ready yet. Either way the
		// screen carries on.
	}
}

/**
 * Send one product event, at most once per page load.
 *
 * For screens and panels that a person can flip back to a dozen times while
 * doing one thing: counting those repeats would make an idle tab look like
 * engagement.
 *
 * `dedupeKey` separates events that share a name but describe different things
 * -- one settings page opened is not the same visit as another -- so they are
 * counted once each rather than once between them.
 */
export function captureEventOnce(event, properties = {}, dedupeKey = event) {
	if (seen.has(dedupeKey)) return
	seen.add(dedupeKey)
	captureEvent(event, properties)
}

function commonProperties() {
	return {
		role: actorRole(),
		surface: window.innerWidth < MOBILE_BREAKPOINT ? 'mobile' : 'desktop',
	}
}

/**
 * The coarse role the event is attributed to, matching the server's
 * `lms.telemetry.get_actor_role` so both halves of a funnel group the same way.
 */
function actorRole() {
	let user
	try {
		user = usersStore().userResource?.data
	} catch (error) {
		return 'unknown'
	}

	if (!user) return 'unknown'
	if (user.is_moderator) return 'moderator'
	if (user.is_instructor) return 'course_creator'
	if (user.is_evaluator) return 'batch_evaluator'
	return 'student'
}

// Exported for tests, which need each case to start from a clean slate.
export function resetCapturedEvents() {
	seen.clear()
}
