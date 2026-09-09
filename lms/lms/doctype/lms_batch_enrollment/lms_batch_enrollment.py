# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSBatchEnrollment(Document):
	def after_insert(self):
		self.add_member_to_live_class()

	def validate(self):
		self.validate_owner()
		self.validate_duplicate_members()
		self.validate_payment()
		self.validate_self_enrollment()
		self.validate_seat_availability()
		self.validate_course_enrollment()

	def validate_owner(self):
		if self.owner == self.member:
			return

		roles = frappe.get_roles()
		if "Moderator" not in roles and "Batch Evaluator" not in roles:
			frappe.throw(_("You must be a Moderator or Batch Evaluator to enroll users in a batch."))

	def validate_payment(self):
		paid_batch = frappe.db.get_value("LMS Batch", self.batch, "paid_batch")
		if paid_batch and not self.is_admin():
			payment = frappe.db.exists(
				"LMS Payment",
				{
					"payment_for_document_type": "LMS Batch",
					"payment_for_document": self.batch,
					"member": self.member,
					"payment_received": True,
				},
			)
			if not payment:
				frappe.throw(_("Payment is required to enroll in this batch."))
			else:
				self.payment = payment

	def validate_self_enrollment(self):
		batch_details = frappe.db.get_value(
			"LMS Batch", self.batch, ["allow_self_enrollment", "paid_batch"], as_dict=True
		)
		if batch_details.paid_batch:
			return
		if not batch_details.allow_self_enrollment and not self.is_admin():
			frappe.throw(_("Enrollment in this batch is restricted. Please contact the Administrator."))

	def is_admin(self):
		roles = frappe.get_roles(frappe.session.user)
		return "Course Creator" in roles or "Moderator" in roles or "Batch Evaluator" in roles

	def validate_duplicate_members(self):
		# Lock the batch row for the rest of this transaction before reading. The
		# check below is a read of a row a concurrent request has not inserted
		# yet, so without the lock both requests see "absent" and both insert —
		# and a duplicate row also consumes a seat in validate_seat_availability,
		# which turns a double-click into "no seats available" for someone else.
		# Same shape as the payment and coupon locks in lms/lms/utils.py.
		frappe.db.get_value("LMS Batch", self.batch, "name", for_update=True)

		if frappe.db.exists(
			"LMS Batch Enrollment",
			{"batch": self.batch, "member": self.member, "name": ["!=", self.name]},
		):
			frappe.throw(_("Member already enrolled in this batch"))

	def validate_seat_availability(self):
		seat_count = frappe.db.get_value("LMS Batch", self.batch, "seat_count")
		enrolled_count = frappe.db.count("LMS Batch Enrollment", {"batch": self.batch})
		if seat_count and enrolled_count >= seat_count:
			frappe.throw(_("There are no seats available in this batch."))

	def validate_course_enrollment(self):
		courses = frappe.get_all("Batch Course", filters={"parent": self.batch}, fields=["course"])

		for course in courses:
			# Same reasoning as validate_duplicate_members, one level down: without
			# the lock, two batches sharing a course can both read "absent" for the
			# same member and the loser's inner insert throws, failing an enrolment
			# that should have skipped. Batch row first, then course row, in that
			# order everywhere — the reverse order exists nowhere, so no cycle.
			frappe.db.get_value("LMS Course", course.course, "name", for_update=True)

			if not frappe.db.exists(
				"LMS Enrollment",
				{"course": course.course, "member": self.member},
			):
				enrollment = frappe.new_doc("LMS Enrollment")
				enrollment.course = course.course
				enrollment.member = self.member
				enrollment.enrollment_from_batch = self.batch
				enrollment.save()

	def add_member_to_live_class(self):
		live_classes = frappe.get_all("LMS Live Class", {"batch_name": self.batch}, ["name", "event"])

		for live_class in live_classes:
			if live_class.event:
				# Scoped bypass: adds only self.member to events of this batch's own live
				# classes. A self-enrolling student has no create permission on Event
				# Participants; the authorization boundary is enrollment creation itself.
				frappe.get_doc(
					{
						"doctype": "Event Participants",
						"reference_doctype": "User",
						"reference_docname": self.member,
						"email": self.member,
						"parent": live_class.event,
						"parenttype": "Event",
						"parentfield": "event_participants",
					}
				).save(ignore_permissions=True)
