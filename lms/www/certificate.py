import frappe
from frappe import _

from lms.lms.certificate_verification import get_verification_page_url


def get_context(context):
	context.no_cache = 1
	certificate_id = frappe.form_dict.certificate_id
	# A filter list here would match some other certificate.
	if not isinstance(certificate_id, str) or not frappe.db.exists("LMS Certificate", certificate_id):
		raise frappe.PageDoesNotExistError(_("Certificate not found."))
	frappe.local.flags.redirect_location = get_verification_page_url(certificate_id)
	raise frappe.Redirect
