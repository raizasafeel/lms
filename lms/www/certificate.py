import frappe

from lms.lms.certificate_verification import get_verification_page_url


def get_context(context):
	context.no_cache = 1
	frappe.local.flags.redirect_location = get_verification_page_url(frappe.form_dict.certificate_id)
	raise frappe.Redirect
