import { call } from 'frappe-ui'
import { ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

export interface PersonDetails {
	name: string
	full_name?: string
	user_image?: string
	/** Staff site roles: Course Creator, Batch Evaluator, Moderator. */
	roles: string[]
}

/** Names, avatars and site roles of `users`, fetched once per user. */
export function usePeopleDetails(users: MaybeRefOrGetter<string[]>) {
	const details = ref(new Map<string, PersonDetails>())
	const pending = new Map<string, Promise<void>>()

	function remember(rows: PersonDetails[]): void {
		const next = new Map(details.value)
		for (const row of rows) if (row.name) next.set(row.name, row)
		details.value = next
	}

	/** Resolves once every one of `ids` is known, or has been asked for. */
	function load(ids: string[]): Promise<void> {
		const fresh = ids.filter(
			(id) => id && !details.value.has(id) && !pending.has(id)
		)
		if (fresh.length) {
			const request = call('lms.lms.people.get_people_details', {
				users: JSON.stringify(fresh),
			}).then((rows: PersonDetails[]) => remember(rows || []))
			fresh.forEach((id) => pending.set(id, request))
		}
		return Promise.all(ids.map((id) => pending.get(id))).then(() => {})
	}

	watch(() => toValue(users), load, { immediate: true })

	const describe = (id: string): PersonDetails =>
		details.value.get(id) ?? { name: id, full_name: id, roles: [] }

	return { details, describe, load }
}
