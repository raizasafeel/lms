import {
	computed,
	getCurrentScope,
	onScopeDispose,
	reactive,
	ref,
	watch,
	type Ref,
} from 'vue'
import { createListResource, createResource } from 'frappe-ui'

export const SETTINGS_PAGE_LENGTH = 13

/**
 * The settings lists on screen, by doctype.
 *
 * A row action on a data-driven page lives in that page's config module, which
 * is handed the row and nothing else — so a delete from a row menu has no way
 * to tell the list it deleted from to refetch. frappe-ui keeps exactly this
 * registry internally (`resourcesByDocType`) and exports nothing that reaches
 * it.
 */
const liveLists = new Map<string, Set<{ reload: () => Promise<unknown> }>>()

/** Refetches every list showing `doctype`, first page first. */
export function reloadSettingsLists(doctype: string): Promise<unknown> {
	const lists = liveLists.get(doctype)
	if (!lists?.size) return Promise.resolve()
	return Promise.all([...lists].map((list) => list.reload()))
}

export interface ResourceCallbacks<T = unknown> {
	onSuccess?: (data: T) => void
	onError?: (error: { messages?: string[] }) => void
}

/**
 * The slice of frappe-ui's list resource the settings panels touch. Declared
 * here because the package ships `ListResource` only as an internal .d.ts and
 * re-exports neither it nor the path, so there is nothing to import.
 */
export interface SettingsListResource<TRow = Record<string, any>> {
	data: TRow[] | null
	start: number
	pageLength: number
	hasNextPage: boolean
	list: { loading: boolean; fetch: () => Promise<unknown> }
	delete: { submit: (name: string, callbacks?: ResourceCallbacks) => void }
	insert: {
		submit: (values: Partial<TRow>, callbacks?: ResourceCallbacks) => void
	}
	setValue: {
		submit: (values: Partial<TRow>, callbacks?: ResourceCallbacks) => void
	}
	update: (options: Record<string, unknown>) => void
	reload: () => Promise<TRow[] | null>
}

export type SettingsListFilters = Record<string, any> | any[][]

export interface SettingsListResourceOptions {
	doctype: string
	fields: string[]
	searchFields?: string[]
	orderBy?: string
	filters?: SettingsListFilters
	cache?: string | string[]
	auto?: boolean
	transform?: (data: any[]) => any[]
}

/**
 * What a rendered list needs, and nothing about where the rows came from.
 *
 * A doctype list and a method-backed one differ in how they fetch and in what
 * they can be asked to do besides — only a doctype list has a `delete` or
 * server-side filters — but a panel renders them identically. Taking the narrow
 * type is what lets SettingsListPanel hold either.
 */
export interface SettingsListView<TRow = Record<string, any>> {
	search: string
	rows: TRow[]
	loading: boolean
	hasNextPage: boolean
	loadMore: () => Promise<unknown>
	reload: () => Promise<unknown>
}

export interface SettingsListSource<TRow = Record<string, any>>
	extends SettingsListView<TRow> {
	resource: SettingsListResource<TRow>
	applyFilters: (filters: SettingsListFilters) => Promise<unknown>
	remove: (
		name: string,
		callbacks?: {
			onSuccess?: () => void
			onError?: (error: { messages?: string[] }) => void
		}
	) => Promise<unknown>
}

export function useSettingsListResource<TRow = Record<string, any>>(
	options: SettingsListResourceOptions
): SettingsListSource<TRow> {
	const search = ref('')
	const baseFilters = options.filters ?? {}

	const resource = createListResource({
		doctype: options.doctype,
		fields: options.fields,
		orderBy: options.orderBy,
		filters: baseFilters,
		cache: options.cache,
		transform: options.transform,
		pageLength: SETTINGS_PAGE_LENGTH,
		auto: false,
	}) as unknown as SettingsListResource<TRow>

	// Requests are serialised because frappe-ui's resources carry no sequence
	// number: whichever response lands last wins. A Load More issued before a
	// search would otherwise overwrite the search results with unfiltered rows.
	let inFlight: Promise<unknown> = Promise.resolve()
	const enqueue = (run: () => unknown) => {
		const next = inFlight.catch(() => {}).then(() => run())
		inFlight = next
		return next
	}

	const searchFilters = (term: string) => {
		if (!term || !options.searchFields?.length) return []
		return options.searchFields.map((field) => [field, 'like', `%${term}%`])
	}

	// `reload()` rewrites pageLength to the number of rows already loaded
	// whenever start > 0, so narrowing the list after Load More would ask for 26
	// rows in one page and leave paging skewed. Going back to start 0 prevents it.
	const fetchFirstPage = () =>
		enqueue(() => {
			resource.start = 0
			return resource.reload()
		})

	// A cached resource comes back carrying the previous mount's orFilters and
	// start, and createListResource returns it before applying any new option,
	// so the panel would reopen filtered by a search its box no longer shows.
	resource.update({ orFilters: [], filters: baseFilters })
	if (options.auto ?? true) fetchFirstPage()

	watch(search, (term) => {
		resource.update({ orFilters: searchFilters(term) })
		fetchFirstPage()
	})

	const applyFilters = (filters: SettingsListFilters) => {
		resource.update({ filters })
		return fetchFirstPage()
	}

	// The offset moves before the request goes out, so a failed fetch has to put
	// it back: `list.onSuccess` never runs, the rows and hasNextPage are
	// untouched, and leaving `start` advanced makes the NEXT Load More ask for
	// the page after the one that failed -- silently skipping it. The rejection
	// is contained here too; `@load-more="list.loadMore()"` binds no handler, so
	// rethrowing only produced an unhandled rejection nobody saw.
	const loadMore = () =>
		enqueue(async () => {
			const loaded = resource.start
			resource.start = loaded + resource.pageLength
			try {
				return await resource.list.fetch()
			} catch (error) {
				resource.start = loaded
				return undefined
			}
		})

	// frappe-ui's own delete handler refetches with `fetch()` from its own
	// onSuccess, before this one runs, and that fetch keeps the current start;
	// past page one it concatenates onto the rows already shown and the deleted
	// row stays. Rewinding afterwards is too late: `list.onSuccess` reads `start`
	// when the response LANDS, so the in-flight page-two request then takes the
	// replace branch and renders rows 14-26 as page one. Rewind first, so the
	// refetch frappe-ui starts is itself a page-one request.
	const remove: SettingsListSource<TRow>['remove'] = (name, callbacks = {}) =>
		enqueue(
			() =>
				new Promise((resolve) => {
					resource.start = 0
					resource.delete.submit(name, {
						onSuccess: () => {
							resolve(resource.reload())
							callbacks.onSuccess?.()
						},
						onError: (error: { messages?: string[] }) => {
							callbacks.onError?.(error)
							resolve(undefined)
						},
					})
				})
		)

	const source = reactive({
		resource,
		search,
		rows: computed(() => resource.data || []),
		loading: computed(() => Boolean(resource.list?.loading)),
		hasNextPage: computed(() => Boolean(resource.hasNextPage)),
		loadMore,
		reload: fetchFirstPage,
		applyFilters,
		remove,
	}) as SettingsListSource<TRow>

	const registered = liveLists.get(options.doctype) ?? new Set()
	registered.add(source)
	liveLists.set(options.doctype, registered)
	// A panel that has gone leaves nothing to refetch. Guarded because this is
	// also called outside a component, where there is no scope to dispose.
	if (getCurrentScope()) onScopeDispose(() => registered.delete(source))

	return source
}

export interface SettingsMethodResourceOptions {
	/** A whitelisted method returning one page of rows. */
	method: string
	/**
	 * The doctype the rows belong to, as an invalidation key only:
	 * `reloadSettingsLists(doctype)` reaches this list too. get_members returns
	 * Users, and a delete from a row menu has to be able to refetch the list it
	 * deleted from without holding the resource behind it.
	 */
	doctype?: string
	/** Extra request params, read at call time — a header filter's value. */
	params?: () => Record<string, unknown>
	/**
	 * The server's own page size. Load More is offered while a page comes back
	 * full, so this has to be what the method pages at (get_members:
	 * MEMBERS_PAGE_LENGTH, which is this same 13).
	 */
	pageLength?: number
	auto?: boolean
}

/**
 * A settings list backed by a whitelisted method rather than a doctype.
 *
 * `createListResource` cannot serve one: it builds a `frappe.client.get_list`
 * call from a doctype and fields, and get_members is a method that applies its
 * own filters, its own page length and its own per-row role lookup. So the
 * paging is done here, against `start` and the length of what came back.
 *
 * No frappe-ui `cache` key on purpose: makeParams closes over the refs below,
 * and createResource hands back the FIRST instance for a key without rebinding
 * those closures, so a remounted panel would inherit a resource still writing
 * into the unmounted one's state.
 */
export function useSettingsMethodResource<TRow = Record<string, any>>(
	options: SettingsMethodResourceOptions
): SettingsListView<TRow> {
	const search = ref('')
	const rows = ref([]) as Ref<TRow[]>
	const start = ref(0)
	const hasNextPage = ref(false)
	const loading = ref(false)
	const pageLength = options.pageLength ?? SETTINGS_PAGE_LENGTH

	const resource = createResource({
		url: options.method,
		makeParams: () => ({
			search: search.value,
			start: start.value,
			...options.params?.(),
		}),
		auto: false,
	}) as unknown as { reload: () => Promise<TRow[] | null> }

	// createResource carries no request sequence and aborts nothing, so two
	// calls in flight both resolve and both append: a filter changed mid-request
	// would show one filter's page under another's, and would over-advance
	// `start` past rows nobody ever saw. Each call takes a token and a
	// superseded response is dropped — with it, its append and its step of
	// `start`, so the newer request stays the one that owns the offset.
	let requestToken = 0

	const fetchPage = async (): Promise<void> => {
		const token = ++requestToken
		loading.value = true
		let data: TRow[] | null = null
		try {
			data = await resource.reload()
		} catch (error) {
			console.error(error)
		}
		if (token !== requestToken) return
		loading.value = false
		if (!data) return
		rows.value = rows.value.concat(data)
		// Paged by what the server actually returned, not by the constant. An
		// exact-equality check hides Load More outright the moment the two
		// disagree, and stepping `start` by the constant would then skip rows.
		start.value = start.value + data.length
		hasNextPage.value = data.length >= pageLength
	}

	// Back to the first page, dropping what is on screen: the search term and
	// the filter both go to the server, so a match past page one is reachable
	// without pressing Load More first.
	const reload = (): Promise<void> => {
		rows.value = []
		start.value = 0
		hasNextPage.value = false
		return fetchPage()
	}

	watch(search, () => reload())

	if (options.auto ?? true) reload()

	const source = reactive({
		search,
		rows,
		loading,
		hasNextPage,
		loadMore: fetchPage,
		reload,
	}) as SettingsListView<TRow>

	const key = options.doctype ?? options.method
	const registered = liveLists.get(key) ?? new Set()
	registered.add(source)
	liveLists.set(key, registered)
	if (getCurrentScope()) onScopeDispose(() => registered.delete(source))

	return source
}
