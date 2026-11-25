<template>
	<div class="relative pt-[13%]">
		<div class="relative aspect-[1122/793]">
			<div
				v-for="(certificate, index) in certificates"
				:key="certificate.name"
				data-sheet
				:data-position="positionOf(index)"
				class="absolute inset-0 origin-top transition-[transform,opacity] duration-500 ease-flow motion-reduce:transition-none"
				:style="sheetStyle(index)"
			>
				<CertificateThumbnail
					v-if="index === 0 || hasPlayed"
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
import { onBeforeUnmount, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import CertificateThumbnail from '@/components/Certificates/CertificateThumbnail.vue'

/** Milliseconds each certificate stays on top while the stack plays. */
const STEP = 1300
const VISIBLE_LAYERS = 3

const props = defineProps<{
	/** Latest first; the first one sits on top. */
	certificates: { name: string; title: string }[]
	playing?: boolean
}>()

const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
const front = ref(0)
const hasPlayed = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

/** 0 is the top sheet; higher numbers sit further back. */
function positionOf(index: number): number {
	const count = props.certificates.length
	return (index - front.value + count) % count
}

function sheetStyle(index: number): Record<string, string | number> {
	const position = positionOf(index)
	const depth = Math.min(position, VISIBLE_LAYERS - 1)
	return {
		zIndex: props.certificates.length - position,
		opacity: position < VISIBLE_LAYERS ? 1 - position * 0.15 : 0,
		transform: `translateY(${-depth * 9}%) scale(${1 - depth * 0.08})`,
	}
}

function stop() {
	clearInterval(timer)
	timer = undefined
	front.value = 0
}

watch(
	() => props.playing,
	(playing) => {
		stop()
		if (!playing || reduceMotion.value || props.certificates.length < 2) return
		hasPlayed.value = true
		timer = setInterval(() => {
			front.value = (front.value + 1) % props.certificates.length
		}, STEP)
	}
)

onBeforeUnmount(stop)
</script>

<style scoped>
.certificate-paper {
	background: #fff; /* token-exempt: certificate paper is white in both themes */
}
</style>
