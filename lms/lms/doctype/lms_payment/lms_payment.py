# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, nowdate
from pypika import functions as fn


class LMSPayment(Document):
	pass


UNIQUE_PAYMENT_ID = "unique_payment_id"


def on_doctype_update():
	add_unique_payment_id_constraint()


def add_unique_payment_id_constraint():
	"""One gateway payment belongs to one LMS Payment. Two callbacks for the same
	payment id can be resolved to different rows, which do not lock each other,
	so the constraint is what stops both being credited.

	A site that already carries duplicates (the very bug this prevents) keeps
	its rows and is told, rather than having a migration decide which payment was
	really charged. It gets a plain index for the duplicate lookup, and
	update_payment_record falls back to serializing callbacks until the
	constraint can be added. Runs on every migrate, so cleaning the duplicates up
	is all an operator has to do."""
	if has_unique_payment_id():
		return

	duplicates = get_duplicate_payment_ids()

	if duplicates:
		frappe.log_error(
			title="Duplicate payment ids block a unique constraint on LMS Payment",
			message="More than one LMS Payment row shares a payment id: "
			+ ", ".join(duplicates)
			+ ".\nUntil the duplicates are removed, every payment callback for a course or batch "
			"is serialized to keep one gateway payment from crediting two of them. Keep the "
			"payment that was really charged and the next migrate will add the constraint.",
			defer_insert=True,
		)
		frappe.db.add_index("LMS Payment", ["payment_id"])
		return

	frappe.db.add_unique("LMS Payment", ["payment_id"])


def has_unique_payment_id() -> bool:
	return bool(frappe.db.has_index("tabLMS Payment", UNIQUE_PAYMENT_ID))


def get_duplicate_payment_ids() -> list[str]:
	payment = frappe.qb.DocType("LMS Payment")
	return (
		frappe.qb.from_(payment)
		.select(payment.payment_id)
		.where(payment.payment_id.notnull() & (payment.payment_id != ""))
		.groupby(payment.payment_id)
		.having(fn.Count(payment.name) > 1)
	).run(pluck=True)


def send_payment_reminder():
	incomplete_payments = frappe.get_all(
		"LMS Payment",
		{
			"payment_received": 0,
			"creation": [">", add_days(nowdate(), -1)],
			"payment_for_document_type": ["in", allowed_payment_types()],
		},
		[
			"name",
			"member",
			"payment_for_document",
			"payment_for_document_type",
			"billing_name",
		],
	)

	for payment in incomplete_payments:
		if has_paid_later(payment):
			continue

		if is_batch_sold_out(payment):
			continue

		frappe.get_doc("LMS Payment", payment.name).run_method("lms_notify")


def allowed_payment_types():
	send_batch_reminders = frappe.db.get_single_value("LMS Settings", "send_payment_reminders_for_batch")
	send_course_reminders = frappe.db.get_single_value("LMS Settings", "send_payment_reminders_for_course")

	allowed_types = []
	if send_batch_reminders:
		allowed_types.append("LMS Batch")

	if send_course_reminders:
		allowed_types.append("LMS Course")

	return allowed_types


def has_paid_later(payment):
	return frappe.db.exists(
		"LMS Payment",
		{
			"member": payment.member,
			"payment_received": 1,
			"payment_for_document": payment.payment_for_document,
			"payment_for_document_type": payment.payment_for_document_type,
		},
	)


def is_batch_sold_out(payment):
	if payment.payment_for_document_type == "LMS Batch":
		seat_count = frappe.get_cached_value("LMS Batch", payment.payment_for_document, "seat_count")
		number_of_students = frappe.db.count("LMS Batch Enrollment", {"batch": payment.payment_for_document})

		if seat_count <= number_of_students:
			return True

	return False
