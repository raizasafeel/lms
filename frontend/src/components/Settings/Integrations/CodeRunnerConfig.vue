<template>
	<LmsSettingsConfig v-slot="{ doc }" integration-key="code_runner">
		<FormControl
			:model-value="doc.livecode_url"
			type="text"
			:label="__('Server URL')"
			:placeholder="HOSTED_SERVER"
			:description="__(HINT)"
			@update:model-value="(value: string) => (doc.livecode_url = value)"
		/>
	</LmsSettingsConfig>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import LmsSettingsConfig from './LmsSettingsConfig.vue'

const HOSTED_SERVER = 'https://falcon.frappe.io'

const HINT =
	"Leave it blank to use Frappe's hosted server, or see docs.frappe.io/learning/falcon-self-hosting-guide to host your own."
</script>
