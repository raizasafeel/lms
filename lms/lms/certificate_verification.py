from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import getdate
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from lms.lms.certificate_designs import (
	get_certificate_pdf,
	get_certificate_title,
	get_issuer,
	render_certificate,
)
from lms.lms.doctype.lms_certificate.lms_certificate import get_certificate_template
from lms.lms.utils import get_lms_route

RAW_PRINT_PATHS = (
	"/printview",
	"/api/method/frappe.utils.print_format.download_pdf",
	"/api/v2/method/frappe.utils.print_format.download_pdf",
)
AWARDED_FOR = {
	"course": ("LMS Course", "course", "short_introduction", "image"),
	"batch": ("LMS Batch", "batch_name", "description", "meta_image"),
}


def get_verification_page_url(certificate: str) -> str:
	return get_lms_route(f"certificates/{quote(certificate, safe='')}")


def get_viewable_certificate(certificate: str):
	"""The certificate, when the viewer may see it. An unpublished one is visible only
	to its member and staff, as `has_permission` decides."""
	if not isinstance(certificate, str) or not frappe.db.exists("LMS Certificate", certificate):
		frappe.throw(_("Certificate not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("LMS Certificate", certificate)
	if not (doc.published or frappe.has_permission("LMS Certificate", "read", doc)):
		frappe.throw(_("This certificate is not published."), frappe.PermissionError)
	return doc


def get_certificate_status(doc) -> str:
	if not doc.published:
		return "unpublished"
	if doc.expiry_date and getdate(doc.expiry_date) < getdate():
		return "expired"
	return "valid"


def get_print_format(doc) -> str | None:
	return doc.template or get_certificate_template(doc.course)


def get_certificate_details(doc) -> dict:
	"""What the verification page shows. The member's email stays out: guests may read this."""
	kind = "course" if doc.course else "batch"
	return {
		"name": doc.name,
		"kind": kind,
		"title": get_certificate_title(doc, kind),
		"status": get_certificate_status(doc),
		"issue_date": doc.issue_date,
		"expiry_date": doc.expiry_date,
		"evaluator_name": doc.evaluator_name if doc.evaluator else None,
		"issued_by": get_issuer(hide_logo=True)["site_name"],
		"is_member": doc.member == frappe.session.user,
		"member": get_member_details(doc),
		"awarded_for": get_awarded_for(doc, kind),
		"html": render_certificate(doc.name, get_print_format(doc)),
	}


def get_member_details(doc) -> dict:
	user = frappe.db.get_value(
		"User", doc.member, ["full_name", "username", "user_image", "headline"], as_dict=True
	)
	user = user or frappe._dict()
	return {
		"full_name": doc.member_name or user.full_name,
		"username": user.username,
		"user_image": user.user_image,
		"headline": user.headline,
	}


def get_awarded_for(doc, kind: str) -> dict | None:
	"""The published course or batch the certificate was awarded for, for its card."""
	doctype, link_field, description_field, image_field = AWARDED_FOR[kind]
	if not doc.get(link_field):
		return None
	row = frappe.db.get_value(
		doctype,
		{"name": doc.get(link_field), "published": 1},
		["name", "title", "category", description_field, image_field],
		as_dict=True,
	)
	if not row:
		return None
	return {
		"name": row.name,
		"title": row.title,
		"category": row.category,
		"description": row[description_field],
		"image": row[image_field],
	}


def send_certificate_pdf(doc) -> None:
	frappe.local.response.filename = f"{doc.name}.pdf"
	frappe.local.response.filecontent = get_certificate_pdf(doc.name, get_print_format(doc))
	frappe.local.response.type = "pdf"


def redirect_raw_certificate_prints() -> None:
	"""A before_request hook: frappe's print view and PDF URLs for a certificate open its
	verification page, which checks who may see it and offers the PDF."""
	if frappe.request.path.rstrip("/") not in RAW_PRINT_PATHS:
		return
	form = frappe.form_dict
	if form.doctype != "LMS Certificate" or not isinstance(form.name, str) or not form.name:
		return
	# frappe.Redirect raised this early becomes an error page, so werkzeug's redirect it is.
	abort(redirect(get_verification_page_url(form.name)))
