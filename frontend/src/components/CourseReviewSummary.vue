<template>
	<div
		class="flex flex-col gap-6 rounded-6 border border-outline-gray-2 p-6 @2xl:flex-row @2xl:items-center"
	>
		<div
			class="flex shrink-0 flex-col gap-2 @2xl:w-44 @2xl:border-e @2xl:border-outline-gray-2"
		>
			<span class="text-4xl-semibold text-ink-gray-9">
				{{ average ? formatRating(average) : '0' }}
			</span>
			<ReviewStars :rating="average" />
			<span class="text-p-base text-ink-gray-6">
				{{
					ratings.length === 1
						? __('1 rating')
						: __('{0} ratings').format(ratings.length)
				}}
			</span>
		</div>
		<div
			class="flex flex-1 flex-col gap-1"
			role="group"
			:aria-label="__('Filter reviews by stars')"
		>
			<button
				v-for="row in rows"
				:key="row.stars"
				type="button"
				class="flex items-center gap-3 rounded-4 px-2 py-1.5 text-p-base transition-colors hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:pointer-events-none"
				:class="stars === row.stars ? 'bg-surface-gray-2' : ''"
				:aria-pressed="stars === row.stars"
				:aria-label="__('{0} stars: {1} reviews').format(row.stars, row.count)"
				:disabled="!row.count"
				data-testid="rating-row"
				@click="stars = stars === row.stars ? null : row.stars"
			>
				<span
					class="w-3 tabular-nums"
					:class="row.count ? 'text-ink-gray-8' : 'text-ink-gray-4'"
				>
					{{ row.stars }}
				</span>
				<span
					class="lucide-star size-4"
					:class="row.count ? 'text-ink-gray-6' : 'text-ink-gray-4'"
					aria-hidden="true"
				/>
				<span
					class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-gray-2"
				>
					<span
						class="block h-full rounded-full bg-surface-amber-4"
						:style="{ width: `${share(row.count)}%` }"
					/>
				</span>
				<span
					class="w-8 text-end tabular-nums"
					:class="row.count ? 'text-ink-gray-7' : 'text-ink-gray-4'"
				>
					{{ row.count }}
				</span>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ReviewStars from '@/components/ReviewStars.vue'
import { formatRating } from '@/utils'
import { starBucket } from '@/utils/reviews'

/** The average, the count per star, and a row per star that filters the list. */
const props = defineProps<{ ratings: number[] }>()

const stars = defineModel<number | null>('stars', { default: null })

const average = computed(() =>
	props.ratings.length
		? props.ratings.reduce((sum, rating) => sum + rating, 0) /
		  props.ratings.length
		: 0
)

const rows = computed(() =>
	[5, 4, 3, 2, 1].map((value) => ({
		stars: value,
		count: props.ratings.filter((rating) => starBucket(rating) === value)
			.length,
	}))
)

const share = (count: number): number =>
	props.ratings.length ? (count / props.ratings.length) * 100 : 0
</script>
