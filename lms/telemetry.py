"""Product telemetry for Frappe Learning.

Frappe ships a Pulse client (`frappe.utils.telemetry.capture`) that posts an
event name and a free-form `properties` dict to a Pulse site, where it lands as
a `Pulse Event` row tagged with the site it came from. This module is the single
place LMS calls it from, so that:

* Every server event carries the same standing context: the persona the site
  picked during onboarding, how old the site is, and what role the actor holds.
  The questions worth asking of this data are all segmentations ("do Customer
  Academy sites configure a payment gateway inside their first fortnight?"), and
  an event name on its own cannot be segmented after the fact.

* The milestones that mark activation are emitted from a document hook rather
  than from whichever endpoint happened to create the row. A second code path
  that creates a course cannot silently stop counting, which is what happens
  when each form instruments itself.

* Telemetry can never break a request. Pulse's own `capture` swallows its
  errors, but the context gathered here reads the database, so every entry point
  in this module is guarded too.

Browser-side events go through `frontend/src/telemetry.js`. They carry the
actor's role but not the persona, because the endpoint that serves settings to
the browser is guest-readable; join them to a site's persona on `site`, which
every Pulse event carries.
"""

import frappe

try:
	from frappe.utils.telemetry import capture as pulse_capture
except ImportError:  # pragma: no cover - very old frappe, or telemetry removed
	pulse_capture = None

try:
	from frappe.utils.telemetry import site_age
except ImportError:  # pragma: no cover
	site_age = None

try:
	from frappe.utils.telemetry import is_pulse_enabled
except ImportError:  # pragma: no cover
	is_pulse_enabled = None

APP = "lms"

# Written by `lms.lms.api.capture_user_persona` from the answers the onboarding
# form collects (frontend/src/pages/Forms/PersonaForm.vue).
PERSONA_FIELDS = (
	"persona_usage_context",
	"persona_first_milestone",
	"persona_current_tool",
	"persona_discovery_source",
)

# The roles reported on an event, most specific first: a moderator who also
# holds Course Creator is reported as a moderator.
REPORTED_ROLES = ("Moderator", "Course Creator", "Batch Evaluator")


def is_enabled() -> bool:
	"""Whether anything downstream would keep an event.

	Checked before the context is gathered rather than inside the client, so a
	site that has telemetry switched off -- most self-hosted ones -- pays nothing
	for the document hooks in this module. Treated as on when the framework does
	not offer the check, which leaves the client's own guard to decide.
	"""
	if not pulse_capture:
		return False

	if not is_pulse_enabled:
		return True

	try:
		return bool(is_pulse_enabled())
	except Exception:
		return False


def capture(event: str, properties: dict | None = None, **kwargs):
	"""Send one product event to Pulse with the site's standing context merged in.

	`properties` wins over the common context, so a caller can deliberately
	override a key (an event captured on behalf of another user, say).
	"""
	if not is_enabled():
		return

	try:
		merged = get_common_properties()
		merged.update(properties or {})
		pulse_capture(event, APP, properties=merged, **kwargs)
	except Exception:
		# A missing metric is not worth a failed request.
		frappe.logger("lms.telemetry").debug(f"could not capture {event}", exc_info=True)


def get_common_properties() -> dict:
	"""Context every server event carries, built once per request.

	Memoised on `frappe.local`, which is torn down with the request, so a long
	worker process never serves one site's persona to another's events.
	"""
	cached = getattr(frappe.local, "lms_telemetry_context", None)
	if cached is None:
		cached = build_common_properties()
		frappe.local.lms_telemetry_context = cached
	return dict(cached)


def build_common_properties() -> dict:
	context = {"role": get_actor_role()}

	for field in PERSONA_FIELDS:
		value = get_setting(field)
		if value:
			# `persona_usage_context` reads as `usage_context` on the event: the
			# prefix only exists to namespace the fields on LMS Settings.
			context[field.replace("persona_", "", 1)] = value

	if get_setting("demo_data_present"):
		context["demo_data_present"] = True

	age = get_site_age()
	if age is not None:
		context["site_age_days"] = age

	return context


def get_setting(fieldname: str):
	"""Read one LMS Settings field, tolerating a field a site has not migrated to yet."""
	try:
		return frappe.get_cached_value("LMS Settings", None, fieldname)
	except Exception:
		return None


def get_site_age():
	if not site_age:
		return None
	try:
		return site_age()
	except Exception:
		return None


def get_actor_role() -> str:
	"""The coarse role the event is attributed to.

	Deliberately coarse: it separates the person building the site from the
	people learning on it, which is the split every funnel here is drawn on.
	"""
	user = frappe.session.user

	if user in ("Guest", "Administrator"):
		return user.lower()

	try:
		roles = set(frappe.get_roles(user))
	except Exception:
		return "unknown"

	for role in REPORTED_ROLES:
		if role in roles:
			return role.lower().replace(" ", "_")

	return "student"


# Document events
# ---------------
# Registered against `*` in hooks.py rather than doctype by doctype: the guard
# below is a dict lookup, and one registration means a doctype is added to the
# taxonomy here, in one place, next to the properties it reports.

TRACKED_DOCTYPES = {
	"LMS Course": "course",
	"Course Chapter": "chapter",
	"Course Lesson": "lesson",
	"LMS Quiz": "quiz",
	"LMS Assignment": "assignment",
	"LMS Programming Exercise": "programming_exercise",
	"LMS Batch": "batch",
	"LMS Program": "program",
	"LMS Live Class": "live_class",
	"LMS Enrollment": "course_enrollment",
	"LMS Batch Enrollment": "batch_enrollment",
	"LMS Quiz Submission": "quiz_submission",
	"LMS Assignment Submission": "assignment_submission",
	"LMS Certificate": "certificate",
	"LMS Certificate Request": "evaluation_request",
	"LMS Payment": "payment",
	"LMS Coupon": "coupon",
	"LMS Category": "category",
	"LMS Badge": "badge",
	"LMS Course Review": "course_review",
	"Job Opportunity": "job_opportunity",
}

# `published` on these marks the moment a site's content becomes reachable by a
# learner, which no creation event marks: all three are created unpublished.
PUBLISHABLE_DOCTYPES = ("LMS Course", "LMS Batch", "LMS Program")


def course_properties(doc) -> dict:
	return {
		"paid": bool(doc.get("paid_course")),
		"published": bool(doc.get("published")),
		"certification": bool(doc.get("enable_certification")),
		"paid_certificate": bool(doc.get("paid_certificate")),
		"chapter_count": len(doc.get("chapters") or []),
	}


def batch_properties(doc) -> dict:
	return {
		"paid": bool(doc.get("paid_batch")),
		"published": bool(doc.get("published")),
		"course_count": len(doc.get("courses") or []),
		"self_enrollment": bool(doc.get("allow_self_enrollment")),
		"conferencing_provider": doc.get("conferencing_provider") or "",
	}


def quiz_properties(doc) -> dict:
	return {
		"question_count": len(doc.get("questions") or []),
		"proctored": bool(doc.get("enable_proctoring")),
		"scheduled": bool(doc.get("enable_scheduling")),
		"negative_marking": bool(doc.get("enable_negative_marking")),
	}


def quiz_submission_properties(doc) -> dict:
	return {
		"percentage": doc.get("percentage"),
		"passed": _has_passed(doc),
		"violations": doc.get("violation_count") or 0,
	}


def _has_passed(doc) -> bool | None:
	percentage = doc.get("percentage")
	passing = doc.get("passing_percentage")
	if percentage is None or passing is None:
		return None
	return percentage >= passing


def payment_properties(doc) -> dict:
	return {
		"currency": doc.get("currency") or "",
		"amount": doc.get("amount"),
		"for_doctype": doc.get("payment_for_document_type") or "",
		"for_certificate": bool(doc.get("payment_for_certificate")),
		"used_coupon": bool(doc.get("coupon")),
		"discount_amount": doc.get("discount_amount") or 0,
	}


def enrollment_properties(doc) -> dict:
	return {
		"paid": bool(doc.get("payment")),
		"from_batch": bool(doc.get("enrollment_from_batch")),
	}


def live_class_properties(doc) -> dict:
	return {
		"conferencing_provider": doc.get("conferencing_provider") or "",
		"duration": doc.get("duration"),
	}


def program_properties(doc) -> dict:
	return {
		"published": bool(doc.get("published")),
		"course_count": len(doc.get("program_courses") or []),
		"enforce_course_order": bool(doc.get("enforce_course_order")),
	}


def lesson_properties(doc) -> dict:
	return {
		"is_scorm": bool(doc.get("is_scorm_package")),
		"in_preview": bool(doc.get("include_in_preview")),
	}


def coupon_properties(doc) -> dict:
	return {
		"discount_type": doc.get("discount_type") or "",
		"has_usage_limit": bool(doc.get("usage_limit")),
	}


DOC_PROPERTIES = {
	"LMS Course": course_properties,
	"LMS Batch": batch_properties,
	"LMS Program": program_properties,
	"Course Lesson": lesson_properties,
	"LMS Quiz": quiz_properties,
	"LMS Quiz Submission": quiz_submission_properties,
	"LMS Payment": payment_properties,
	"LMS Enrollment": enrollment_properties,
	"LMS Live Class": live_class_properties,
	"LMS Coupon": coupon_properties,
}


def capture_doc_event(doc, method=None):
	"""Emit `<thing>_created` for the doctypes in the taxonomy above."""
	event = TRACKED_DOCTYPES.get(doc.doctype)
	if not event or not is_enabled():
		return

	capture(f"{event}_created", describe_doc(doc, include_first=True))


def capture_publish_event(doc, method=None):
	"""Emit `<thing>_published` when a course, batch or program goes live."""
	if doc.doctype not in PUBLISHABLE_DOCTYPES or not is_enabled():
		return

	try:
		if not doc.has_value_changed("published"):
			return
	except Exception:
		return

	event = TRACKED_DOCTYPES.get(doc.doctype)
	if not event:
		return

	if doc.get("published"):
		capture(f"{event}_published", describe_doc(doc))
	else:
		capture(f"{event}_unpublished", {})


def describe_doc(doc, include_first: bool = False) -> dict:
	"""Properties for a document event. Never raises: a property that cannot be
	read is worth less than the event it would have annotated."""
	properties = {}

	if include_first:
		try:
			properties["is_first"] = is_first_of_doctype(doc.doctype)
		except Exception:
			pass

	extract = DOC_PROPERTIES.get(doc.doctype)
	if extract:
		try:
			properties.update(extract(doc))
		except Exception:
			pass

	return properties


def is_first_of_doctype(doctype: str) -> bool:
	"""Whether the document just inserted is the only one on the site.

	This is the activation signal the retention work needs -- a site's first
	course and its first enrolled learner, not its thousandth. Reads two rows
	rather than counting, so it costs the same on a site with a million.
	"""
	cache_key = f"lms_telemetry_seen:{doctype}"
	cache = frappe.cache()

	if cache.get_value(cache_key):
		return False

	rows = frappe.get_all(doctype, limit=2, pluck="name")

	if len(rows) > 1:
		# Latch it: past the first, this doctype never needs counting again.
		cache.set_value(cache_key, 1)
		return False

	return True
