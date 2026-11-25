export interface LMSPrice {
	creation?: string
	name?: string
	modified?: string
	owner?: string
	modified_by?: string
	docstatus?: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Currency : Link - Currency	*/
	currency: string
	/**	Price Type : Select	*/
	price_type: 'Fixed' | 'Percent Off'
	/**	Amount : Currency - currency	*/
	amount?: number
	/**	Percent Off : Percent - Off the primary price, converted at the current exchange rate.	*/
	percent_off?: number
}
