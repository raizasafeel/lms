<template>
	<LmsSettingsConfig v-slot="{ doc }" integration-key="unsplash">
		<Password
			v-model="doc.unsplash_access_key"
			:label="__('Access key')"
			required
			:placeholder="__('Paste your Unsplash access key')"
			:description="__('Create one at unsplash.com/developers.')"
		/>
	</LmsSettingsConfig>
</template>

<script setup lang="ts">
import { Password } from 'frappe-ui'
import LmsSettingsConfig from './LmsSettingsConfig.vue'
</script>
