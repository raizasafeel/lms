<template>
	<div ref="root" class="relative pt-[10%]">
		<div class="relative aspect-[1122/793]">
			<div
				v-for="(certificate, index) in certificates"
				:key="certificate.name"
				data-sheet
				:data-position="positionOf(index)"
				:data-leaving="index === leaving || undefined"
				class="absolute inset-0 origin-top transition-[transform,opacity] duration-500 ease-flow motion-reduce:transition-none"
				:style="sheetStyle(index)"
			>
				<CertificateThumbnail
					v-if="index <= VISIBLE_LAYERS || hasPlayed"
					:certificate="certificate.name"
					:title="certificate.title"
				/>
				<div
					v-else
					class="certificate-paper size-full ring-1 ring-outline-gray-1"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useIntersectionObserver, useMediaQuery } from '@vueuse/core'
import CertificateThumbnail from '@/components/Certificates/CertificateThumbnail.vue'

/** Milliseconds each certificate stays on top while the stack plays. */
const STEP = 1300
const VISIBLE_LAYERS = 3
// The visible sheets and the first hidden one, which the first step reveals, load up
// front so no sheet shows its loading state mid-animation; the rest wait for a hover.

const props = defineProps<{
	/** Latest first; the first one sits on top. */
	certificates: { name: string; title: string }[]
	playing?: boolean
}>()

const root = ref<HTMLElement | null>(null)
const isInView = ref(true)
const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
const front = ref(0)
/** The sheet that last left the top; it is off to the right until the next step. */
const leaving = ref<number | null>(null)
const hasPlayed = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

useIntersectionObserver(root, ([entry]) => {
	isInView.value = entry?.isIntersecting ?? true
})

const isPlaying = computed(
	() =>
		Boolean(props.playing) &&
		isInView.value &&
		!reduceMotion.value &&
		props.certificates.length > 1
)

/** 0 is the top sheet; higher numbers sit further back. */
function positionOf(index: number): number {
	const count = props.certificates.length
	return (index - front.value + count) % count
}

function sheetStyle(index: number): Record<string, string | number> {
	const count = props.certificates.length
	if (index === leaving.value) {
		return {
			zIndex: count + 1,
			opacity: 1,
			transform: 'translateX(115%) rotate(6deg)',
		}
	}
	const position = positionOf(index)
	const depth = Math.min(position, VISIBLE_LAYERS - 1)
	return {
		zIndex: count - position,
		opacity: position < VISIBLE_LAYERS ? 1 - position * 0.15 : 0,
		transform: `translateY(${-depth * 7}%) scale(${1 - depth * 0.07})`,
	}
}

function advance() {
	leaving.value = front.value
	front.value = (front.value + 1) % props.certificates.length
}

/** Clearing both refs lets the transition carry every sheet back to its place. */
function stop() {
	clearInterval(timer)
	timer = undefined
	front.value = 0
	leaving.value = null
}

watch(isPlaying, (playing) => {
	stop()
	if (!playing) return
	hasPlayed.value = true
	timer = setInterval(advance, STEP)
})

onBeforeUnmount(stop)
</script>

<style scoped>
.certificate-paper {
	background: #fff; /* token-exempt: certificate paper is white in both themes */
}
</style>
