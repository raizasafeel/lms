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
	/**	Country : Link - Country	*/
	country: string
	/**	Price Type : Select	*/
	price_type: 'Fixed' | 'Percent Off'
	/**	Amount : Currency - currency	*/
	amount?: number
	/**	Currency : Link - Currency	*/
	currency?: string | null
	/**	Percent Off : Percent - Off the course's or batch's own price, in its own currency.	*/
	percent_off?: number
}
