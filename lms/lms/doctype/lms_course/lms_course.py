# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import random

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, today

from ...utils import (
	generate_slug,
	get_average_rating,
	get_lesson_count,
	update_payment_record,
	validate_image,
)


class LMSCourse(Document):
	def validate(self):
		self.validate_published()
		self.validate_instructors()
		self.validate_video_link()
		self.validate_status()
		self.validate_payments_app()
		self.validate_certification()
		self.validate_amount_and_currency()
		self.image = validate_image(self.image)
		self.validate_card_gradient()

	def validate_published(self):
		if not self.published:
			return
		if self.is_new() or self.has_value_changed("published") or not self.published_on:
			self.published_on = today()

	def validate_instructors(self):
		if self.is_new() and not self.instructors:
			frappe.get_doc(
				{
					"doctype": "Course Instructor",
					"instructor": self.owner,
					"parent": self.name,
					"parentfield": "instructors",
					"parenttype": "LMS Course",
				}
			).save(ignore_permissions=True)

	def validate_video_link(self):
		# Store video_link exactly as entered: a YouTube/Vimeo link or an uploaded
		# file path. The frontend normalizes links for rendering (it handles full
		# URLs and bare ids alike), so there's no need to strip URLs down to a bare
		# id here. Stripping was lossy: it mangled uploaded /files paths and turned
		# some YouTube urls into ids that don't round-trip cleanly.
		return

	def validate_status(self):
		if self.published:
			self.status = "Approved"

	def validate_payments_app(self):
		if self.paid_course:
			installed_apps = frappe.get_installed_apps()
			if "payments" not in installed_apps:
				documentation_link = "https://docs.frappe.io/learning/setting-up-payment-gateway"
				frappe.throw(
					_(
						"Please install the Payments App to create a paid course. Refer to the documentation for more details. {0}"
					).format(documentation_link)
				)

	def validate_certification(self):
		if self.enable_certification and self.paid_certificate:
			frappe.throw(_("A course cannot have both paid certificate and certificate of completion."))

		if self.paid_certificate and not self.evaluator:
			frappe.throw(_("Evaluator is required for paid certificates."))

		if self.paid_certificate and not self.timezone:
			frappe.throw(_("Timezone is required for paid certificates."))

	def validate_amount_and_currency(self):
		if self.paid_course and (cint(self.course_price) <= 0 or not self.currency):
			frappe.throw(_("Amount and currency are required for paid courses."))

		if self.paid_certificate and (cint(self.course_price) <= 0 or not self.currency):
			frappe.throw(_("Amount and currency are required for paid certificates."))

	def validate_card_gradient(self):
		if not self.image and not self.card_gradient:
			colors = [
				"Red",
				"Blue",
				"Green",
				"Yellow",
				"Orange",
				"Pink",
				"Amber",
				"Violet",
				"Cyan",
				"Teal",
				"Gray",
				"Purple",
			]
			self.card_gradient = random.choice(colors)

	def on_payment_authorized(self, payment_status):
		if payment_status in ["Authorized", "Completed"]:
			update_payment_record("LMS Course", self.name)

	def autoname(self):
		if not self.name:
			self.name = generate_slug(self.title, "LMS Course")

	def __repr__(self):
		return f"<Course#{self.name}>"


def update_course_statistics():
	courses = frappe.get_all("LMS Course", fields=["name"])

	for course in courses:
		lessons = get_lesson_count(course.name)
		enrollments = frappe.db.count("LMS Enrollment", {"course": course.name, "member_type": "Student"})
		avg_rating = get_average_rating(course.name) or 0
		avg_rating = flt(avg_rating, frappe.get_system_settings("float_precision") or 3)

		frappe.db.set_value(
			"LMS Course",
			course.name,
			{"lessons": lessons, "enrollments": enrollments, "rating": avg_rating},
		)
