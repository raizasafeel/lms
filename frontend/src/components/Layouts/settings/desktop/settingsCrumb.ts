import type { InjectionKey } from 'vue'

/** The page a settings panel sits under, drawn as "← Parent / Title" in its header. */
export interface SettingsCrumb {
	label: string
	open: () => void
}

export const settingsCrumbKey: InjectionKey<SettingsCrumb | null> =
	Symbol('settingsCrumb')
