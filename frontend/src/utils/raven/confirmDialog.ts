// frappe-ui takes dialog buttons as plain option objects rather than components,
// so the Cancel-then-destructive pair both Raven confirmations draw is declared
// once here instead of in each of them.

export interface DialogAction {
	label: string
	variant?: 'solid'
	theme?: 'red'
	loading?: boolean
	onClick: (context: { close: () => void }) => void
}

export function confirmActions(
	confirmLabel: string,
	onConfirm: () => void,
	loading?: boolean
): DialogAction[] {
	return [
		{
			label: __('Cancel'),
			onClick: ({ close }: { close: () => void }) => close(),
		},
		{
			label: confirmLabel,
			variant: 'solid',
			theme: 'red',
			loading,
			onClick: onConfirm,
		},
	]
}
