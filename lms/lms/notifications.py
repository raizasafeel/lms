import frappe

# Per-site Email Template overrides, one helper per half because a custom
# template replaces the subject as well as the body. Both are registered under
# `jinja.methods` in `lms/hooks.py`, so a sandboxed rule render can call them.
_SITE_TEMPLATE_FIELDS = {
	"LMS Batch Enrollment": "batch_confirmation_template",
	"LMS Certificate": "certification_template",
	"LMS Payment": "payment_reminder_template",
}


def _override_template(doc) -> str | None:
	"""The Email Template overriding this document's mail, if an admin picked one.
	LMS Batch Enrollment reads the batch's own template first, then the site-wide
	one. The other two doctypes have only a site-wide setting.
	"""
	if doc.doctype == "LMS Batch Enrollment":
		per_batch = frappe.db.get_value("LMS Batch", doc.batch, "confirmation_email_template")
		if per_batch:
			return per_batch

	field = _SITE_TEMPLATE_FIELDS.get(doc.doctype)
	return frappe.db.get_single_value("LMS Settings", field) if field else None


def _legacy_override_args(doc) -> dict:
	"""The flat context develop rendered an override template with.
	Overrides written before this branch name `student_name` or `billing_name`,
	never `doc`, and jenv's DebugUndefined prints an unknown name verbatim.
	"""
	from frappe.utils import get_url

	from lms.lms.utils import get_lms_route

	if doc.doctype == "LMS Batch Enrollment":
		batch = (
			frappe.db.get_value(
				"LMS Batch",
				doc.batch,
				["name", "title", "start_date", "start_time", "medium"],
				as_dict=True,
			)
			or frappe._dict()
		)
		return {
			"title": batch.title,
			"student_name": doc.member_name,
			"start_time": batch.start_time,
			"start_date": batch.start_date,
			"medium": batch.medium,
			"name": batch.name,
		}

	if doc.doctype == "LMS Certificate":
		return {
			"member_name": doc.member_name,
			"course_name": doc.course,
			"course_title": frappe.db.get_value("LMS Course", doc.course, "title"),
			"name": doc.name,
			"template": doc.template,
		}

	if doc.doctype == "LMS Payment":
		document_type = doc.payment_for_document_type
		kind = document_type.split(" ")[-1].lower()
		return {
			"billing_name": doc.billing_name,
			"type": kind,
			"title": frappe.db.get_value(document_type, doc.payment_for_document, "title"),
			"link": get_url() + get_lms_route(f"billing/{kind}/{doc.payment_for_document}"),
		}

	return {}


def _render_override(doc, fieldname: str) -> str:
	template = _override_template(doc)
	if not template:
		return ""

	row = frappe.db.get_value(
		"Email Template",
		template,
		["subject", "response", "response_html", "use_html"],
		as_dict=True,
	)
	if not row:
		return ""

	# A Use HTML template keeps its body in `response_html` and leaves `response`
	# empty, so reading `response` alone returns "" and the override falls back to
	# the built-in copy with no error anywhere.
	if fieldname == "subject":
		content = row.subject
	else:
		content = row.response_html if row.use_html else row.response

	# Only System Manager can write an Email Template, and `restrict_globals=True`
	# is the same sandbox a rule's own subject and message render under. No wider
	# trust boundary than the inline render this replaces.
	return frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		content or "",
		{**_legacy_override_args(doc), "doc": doc},
		restrict_globals=True,
	)


def email_override_subject(doc) -> str:
	"""The override template's subject, or "" when no admin has picked one."""
	return _render_override(doc, "subject")


def email_override_body(doc) -> str:
	"""The override template's body, or "" when no admin has picked one."""
	return _render_override(doc, "response")


# The body an admin sees first, copied from develop's
# `templates/emails/batch_confirmation.html` and wrapped in develop's two
# overrides: the per-batch template first, the per-site setting behind it.
BATCH_CONFIRMATION_MESSAGE = """
{% set override = email_override_body(doc) %}
{% if override %}
{{ override }}
{% else %}
{% set batch = frappe.get_doc("LMS Batch", doc.batch) %}
<p>{{ _("Dear ") }} {{ doc.member_name }},</p>
<br>
<p>{{ _("We are pleased to inform you that you have been enrolled in our upcoming batch. Congratulations!") }}</p>
<br>
<p><b>{{ _("Batch Start Date:") }}</b> {{ frappe.utils.format_date(batch.start_date, "medium") }}</p>
{% if batch.medium %}
<p><b>{{ _("Medium:") }}</b> {{ batch.medium }}</p>
{% endif %}
<p><b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(batch.start_time, "hh:mm a") }}</p>
<br>
<p><a href="{{ frappe.utils.get_url() }}{{ get_lms_route("batches/" ~ batch.name) }}">{{ _("Visit your batch") }}</a></p>
<p>{{ _("If you have any questions or require assistance, feel free to contact us.") }}</p>
<br>
<p>{{ _("Best Regards") }}</p>
{% endif %}
"""

# A rule's Subject renders through the same restricted Jinja as its body, so the
# override is an inline expression on one line. A `{% set %}` tag of its own
# would render a newline into the subject header.
BATCH_CONFIRMATION_SUBJECT = '{{ email_override_subject(doc) or "Enrollment Confirmation for " ~ frappe.db.get_value("LMS Batch", doc.batch, "title") }}'

# Copied from develop's `templates/emails/certification.html`, with its `args`
# names resolved against the certificate, and wrapped in the per-site
# `LMS Settings.certification_template` override.
CERTIFICATION_MESSAGE = """
{% set override = email_override_body(doc) %}
{% if override %}
{{ override }}
{% else %}
{% set course_title = frappe.db.get_value("LMS Course", doc.course, "title") %}
<p>
    {{ _("Dear ") }} {{ doc.member_name }},
</p>
<br>
<p>
    {{ _("I am delighted to inform you that you have successfully earned your certification for the {0} course. Congratulations!").format(frappe.bold(course_title)) }}
</p>
<br>
<p>
    {{ _("With this certification, you can now showcase your updated skills and share your achievement with your colleagues and on LinkedIn. To access your certificate, please click on the link provided below. Make sure you are logged in to the portal.") }}
</p>
<br>
<a href="/api/method/frappe.utils.print_format.download_pdf?doctype=LMS+Certificate&name={{ doc.name }}&format={{ doc.template | urlencode }}">{{ _("Certificate Link") }}</a>
<br>
<p>
    {{ _("Once again, congratulations on this significant accomplishment.")}}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>
{% endif %}
"""

# Same subject override as BATCH_CONFIRMATION_SUBJECT, for this mail's single
# per-site template.
CERTIFICATION_SUBJECT = '{{ email_override_subject(doc) or "Congratulations on getting certified!" }}'

# Copied from develop's `certificate_request_notification.html`. `date` and
# `start_time` shadow `doc.date` and `doc.start_time` on purpose: the mail shows
# the instant in the zone the learner booked it in, and the date can shift too.
EVALUATION_BOOKING_MESSAGE = """
{% set course_title = frappe.db.get_value("LMS Course", doc.course, "title") %}
{% set evaluator_name = frappe.db.get_value("User", doc.evaluator, "full_name") %}
{% set timezone = get_evaluation_display_timezone(doc.course, doc.batch_name) %}
{% set date, start_time = convert_from_system_timezone(doc.date, doc.start_time, timezone) %}
{% set timezone_label = format_timezone(timezone, frappe.utils.get_datetime(date ~ " " ~ start_time)) %}
<p> {{ _("Hey {0}").format(doc.member_name) }} </p>
<br>
<p> {{ _('Your evaluation for the course {0} has been scheduled on {1} at {2} {3}.').format(course_title, frappe.utils.format_date(date, "medium"), frappe.utils.format_time(start_time, "short"), timezone_label) }}</p>
<br>
<p> {{ _("Your evaluator is {0}").format(evaluator_name) }} </p>
<br>
<p> {{ _("Please prepare well and be on time for the evaluations.") }} </p>
"""

# Copied from develop's `published_course_notification.html`. One body serves
# every recipient, so the per-instructor avatar is dropped, and the link goes
# through `get_lms_route` because the SPA mount path is site-configurable.
PUBLISHED_COURSE_MESSAGE = """
<div style="width: 70%; margin: 0 auto;">
    <img src="{{ frappe.db.get_single_value("Website Settings", "banner_image") }}" style="width: 30px; height: 30px;" />
    <p style="font-size: 16px; font-weight: 600;">
        {{ _("Hello Learner") }},
    </p>
    <p>
        {{ _("A new course has been published on ") }} {{ frappe.db.get_single_value("Website Settings", "app_name") }} {{ _("that might interest you!") }} {{ _("Here are the details:") }}
    </p>
    <div style="background-color: #F8F8F8; border-radius: 12px; padding: 12px; margin-bottom: 6px;">
        <div style="font-weight: 600; margin-bottom: 6px;">
            {{ doc.title }}
        </div>
        <div>
            {{ doc.short_introduction }}
        </div>
        <div style="margin-top: 20px;">
            {% for row in doc.instructors %}
            <div style="margin-bottom: 5px;">
                {{ frappe.db.get_value("User", row.instructor, "full_name") }}
            </div>
            {% endfor %}
        </div>
    </div>
    <a href="{{ frappe.utils.get_url() }}{{ get_lms_route("courses/" ~ doc.name) }}" style="display: inline-block; padding: 4px 8px; background-color: #171717; color: #fff; text-decoration: none; cursor: pointer; border-radius: 8px; margin-top: 10px;">
        {{ _("Checkout the course") }}
    </a>
</div>
"""

# Copied from develop's `published_batch_notification.html`, same substitutions
# as PUBLISHED_COURSE_MESSAGE. LMS Batch has no `short_introduction`, so the
# blurb comes from `doc.description`.
PUBLISHED_BATCH_MESSAGE = """
<div style="width: 70%; margin: 0 auto;">
    <img src="{{ frappe.db.get_single_value("Website Settings", "banner_image") }}" style="width: 30px; height: 30px;" />
    <p style="font-size: 16px; font-weight: 600;">
        {{ _("Hello Learner") }},
    </p>
    <p>
        {{ _("A new batch has been published on ") }} {{ frappe.db.get_single_value("Website Settings", "app_name") }} {{ _("that might interest you!") }} {{ _("Here are the details:") }}
    </p>
    <div style="background-color: #F8F8F8; border-radius: 12px; padding: 12px; margin-bottom: 6px;">
        <div style="font-weight: 600; margin-bottom: 6px; font-size: 15px;">
            {{ doc.title }}
        </div>
        <div>
            {{ doc.description }}
        </div>
        <div style="margin-top: 20px; font-size: 13px;">
            {% if doc.end_date %}
            <span>
                {{ _("From ") }} {{ frappe.utils.format_date(doc.start_date, "dd MMM YYYY") }} {{ _(" to ") }} {{ frappe.utils.format_date(doc.end_date, "dd MMM YYYY") }}
            </span>
            {% else %}
            <span>
                {{ frappe.utils.format_date(doc.start_date, "dd MMM YYYY") }}
            </span>
            {% endif %}
        </div>
        <div style="color: #525252; margin-top: 4px; font-size: 13px;">
            <span>
                {{ _("Time: ") }} {{ frappe.utils.format_time(doc.start_time, "HH:mm a") }} {{ format_timezone(doc.timezone, doc.start_date) }}
            </span>
        </div>
        <div style="margin-top: 20px;">
            {% for row in doc.instructors %}
            <div style="margin-bottom: 5px;">
                {{ frappe.db.get_value("User", row.instructor, "full_name") }}
            </div>
            {% endfor %}
        </div>
    </div>
    <a href="{{ frappe.utils.get_url() }}{{ get_lms_route("batches/" ~ doc.name) }}" style="display: inline-block; padding: 4px 8px; background-color: #171717; color: #fff; text-decoration: none; cursor: pointer; border-radius: 8px; margin-top: 10px;">
        {{ _("Checkout the batch") }}
    </a>
</div>
"""

# Copied from develop's `lms_course_interest.html`. One body is rendered for
# every bcc'd recipient, so the `first_name` greeting is dropped.
COURSE_AVAILABILITY_MESSAGE = """
{% set course_url = frappe.utils.get_url() ~ get_lms_route("courses/" ~ doc.name) %}
{% set brand_name = frappe.db.get_single_value("Website Settings", "app_name") %}
<div>
	<p>{{ _("Hi,") }}</p>
	<br>
	<p>{{ _("The course {0} is now available on {1}.").format(frappe.bold(doc.title), brand_name) }}</p>
	<br>
	<p>{{ _("Click on the link below to start learning.") }}</p>
	<p style="margin: 15px 0px;">
		<a href="{{ course_url }}" rel="nofollow" class="btn btn-primary">{{ _("Start Learning") }}</a>
	</p>
	<br>
	<p>
		{{ _("You can also copy-paste following link in your browser") }}<br>
		<a href="{{ course_url }}">{{ course_url }}</a>
	</p>
	<br>
	<p>{{ _("Thanks and Regards") }},</p>
	<p>{{ brand_name }}</p>
</div>
"""

# An audience that is a query rather than a field or a role, rendered as Jinja
# before it is split into addresses. Every such query uses `frappe.db.get_all`,
# because `get_list` is checked against whoever saved and returns nobody.
ENABLED_USERS_BCC = """{% for user in frappe.db.get_all("User", filters={"enabled": 1}, fields=["name"], limit_page_length=0) %}{{ user.name }}
{% endfor %}"""

INTERESTED_USERS_BCC = """{% for interest in frappe.db.get_all("LMS Course Interest", filters={"course": doc.name}, fields=["user"], limit_page_length=0) %}{{ interest.user }}
{% endfor %}"""

# The three reminders below are Days Before rules, so `date_changed` names the
# date their audience is computed from. Each opened with `Dear {{ student_name }}`
# on develop; one body serves every bcc'd recipient, so they say "Hi," instead.
BATCH_START_REMINDER_MESSAGE = """
<p>{{ _("Hi,") }}</p>
<br>
<p>
	{{ _("The batch you have enrolled for is starting tomorrow. Please be prepared and be on time for the session.") }}
</p>
<br>
<p>
	<b>{{ _("Batch:") }}</b> {{ doc.title }}
</p>
<p>
	<b>{{ _("Start Date:") }}</b> {{ frappe.utils.format_date(doc.start_date, "long") }}
</p>
<p>
	<b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(doc.start_time, "hh:mm a") }}
</p>
<p>
	<b>{{ _("Medium:") }}</b> {{ doc.medium }}
</p>
<br>
<p>
	<a href="{{ frappe.utils.get_url() }}{{ get_lms_route("batches/" ~ doc.name) }}">👉 {{ _("Visit your batch") }}</a>
</p>
<br>
<p>
	{{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
	{{ _("Best Regards") }}
</p>
"""

BATCH_START_REMINDER_RECORDED_MESSAGE = """
<p>{{ _("Hi,") }}</p>
<br>
<p>
	{{ _("You're enrolled and all set! The course content is ready, so you can start learning right away and go at your own pace.") }}
</p>
{% if doc.evaluation %}
<br>
<p>
	{{ _("When you feel ready, you can schedule an evaluation to get certified.") }}
	{% if doc.evaluation_end_date %}
	{{ _("The last day to schedule your evaluation is {0}.").format(frappe.utils.format_date(doc.evaluation_end_date, "long")) }}
	{% endif %}
</p>
{% endif %}
<br>
<p>
	<b>{{ _("Batch:") }}</b> {{ doc.title }}
</p>
<p>
	<b>{{ _("Medium:") }}</b> {{ doc.medium }}
</p>
<br>
<p>
	<a href="{{ frappe.utils.get_url() }}{{ get_lms_route("batches/" ~ doc.name) }}">👉 {{ _("Visit your batch") }}</a>
</p>
<br>
<p>
	{{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
	{{ _("Best Regards") }}
</p>
"""

LIVE_CLASS_REMINDER_MESSAGE = """
<p>{{ _("Hi,") }}</p>
<br>
<p>
	{{ _("You have a live class scheduled today. Please be prepared and be on time for the session.") }}
</p>
<br>
<p>
	<b>{{ _("Class:") }}</b> {{ doc.title }}
</p>
<p>
	<b>{{ _("Date:") }}</b> {{ frappe.utils.format_date(doc.date, "long") }}
</p>
<p>
	<b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(doc.time, "hh:mm a") }}
</p>
<br>
<p>
	<a href="{{ frappe.utils.get_url() }}{{ get_lms_route("batches/" ~ doc.batch_name) }}">👉 {{ _("Visit your batch") }}</a>
</p>
<br>
<p>
	{{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
	{{ _("Best Regards") }}
</p>
"""

BATCH_MEMBERS_BCC = """{% for row in frappe.db.get_all("LMS Batch Enrollment", filters={"batch": doc.name}, fields=["member"], limit_page_length=0) %}{{ row.member }}
{% endfor %}"""

LIVE_CLASS_MEMBERS_BCC = """{% for row in frappe.db.get_all("LMS Batch Enrollment", filters={"batch": doc.batch_name}, fields=["member"], limit_page_length=0) %}{{ row.member }}
{% endfor %}"""

# `send_payment_reminder` keeps its own selection, which no rule condition can
# express, and triggers this rule per surviving payment with
# `run_method("lms_notify")`. Core fires Method rules for any method name.
PAYMENT_REMINDER_MESSAGE = """
{% set override = email_override_body(doc) %}
{% if override %}
{{ override }}
{% else %}
{% set type = doc.payment_for_document_type.split(" ")[-1].lower() %}
{% set title = frappe.db.get_value(doc.payment_for_document_type, doc.payment_for_document, "title") %}
{% set link = frappe.utils.get_url() ~ get_lms_route("billing/" ~ type ~ "/" ~ doc.payment_for_document) %}
<div>
    <p>{{ _('Hi') }} {{ doc.billing_name }},</p>
    <br>
    <p>{{ _('We noticed that you started enrolling in the') }} {{ type }} {{ title }} {{ _('but didn’t complete your payment') }}.</p>
    <br>
    <p>
        {{ _("We have a limited number of seats, and they won't be available for long!")}}
    </p>
    <br>
    <p>
        {{ _("Don’t miss this opportunity to enhance your skills. Click below to complete your enrollment") }}:
    </p>
    <br>
    <p>
        <a href="{{ link }}">👉 {{ _("Complete Your Enrollment") }}</a>
    </p>
    <br>
    <p>
        {{ _("If you have any questions or need assistance, feel free to reach out to our support team.") }}
    </p>
    <br>
    <p>
        {{ _("Looking forward to seeing you enrolled!") }}
    </p>
</div>
{% endif %}
"""

# Same subject override, for the payment reminder's per-site template.
PAYMENT_REMINDER_SUBJECT = (
	"""{{ email_override_subject(doc) or "Complete Your Enrollment - Don't miss out!" }}"""
)

# LMS Payment has no instructor field, so the instructors come from the paid-for
# document's child table. A permission-checked query on a child doctype with no
# parent context renders `instructor` as the string "None", hence `get_all`.
PAYMENT_INSTRUCTORS_CC = """{% for row in frappe.db.get_all("Course Instructor", filters={"parenttype": doc.payment_for_document_type, "parent": doc.payment_for_document}, fields=["instructor"], limit_page_length=0) %}{{ row.instructor }}
{% endfor %}"""

# Copied from develop's `job_application.html`. The resume is not in the body.
# `attach_files` and `from_attach_field` on the rule below carry it.
JOB_APPLICATION_MESSAGE = """
{% set full_name = frappe.db.get_value("User", doc.user, "full_name") %}
<p>
    {{ _("{0} has applied for the job position {1}").format(full_name, doc.job_title) }}
</p>
<br>
<p>
    {{ _("You can find their resume attached to this email.") }}
</p>
"""

# Copied from develop's `job_report.html`. Its unused `job_link` local is
# dropped, and the desk link becomes a portal link through `get_lms_route`
# because this audience uses the portal like anyone else.
JOB_REPORT_MESSAGE = """
{% set job_url = frappe.utils.get_url() ~ get_lms_route("job-openings/" ~ doc.name) %}
{% set reporter = frappe.db.get_value("User", doc.reported_by, "full_name") %}
<p>{{ _("Hey,") }}</p>
<p>{{ _("{0} has reported a job post for the following reason.").format(reporter) }}</p>
<p>" {{ doc.report_reason }} "</p>
<p>{{ _("Please take appropriate action at {0}").format(job_url) }}</p>
"""

# One entry per mail Frappe Learning sends. The seeder creates each as a
# Notification row once and never writes to it again, so an admin's wording,
# channel and on/off switch survive every migrate.
LMS_NOTIFICATIONS = [
	{
		"name": "LMS Batch Enrollment Confirmation",
		"document_type": "LMS Batch Enrollment",
		"event": "New",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": BATCH_CONFIRMATION_SUBJECT,
		"message": BATCH_CONFIRMATION_MESSAGE,
		"recipients": [{"receiver_by_document_field": "member"}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Certification",
		"document_type": "LMS Certificate",
		"event": "New",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": CERTIFICATION_SUBJECT,
		"message": CERTIFICATION_MESSAGE,
		"recipients": [{"receiver_by_document_field": "member"}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Evaluation Booking",
		"document_type": "LMS Certificate Request",
		"event": "New",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": 'Evaluation slot booked for {{ frappe.db.get_value("LMS Course", doc.course, "title") }}',
		"message": EVALUATION_BOOKING_MESSAGE,
		"recipients": [
			{"receiver_by_document_field": "member"},
			{"receiver_by_document_field": "evaluator"},
		],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		# Known defect, left as it is. On a site with no outgoing mail this rule
		# and the batch one below still get `notification_sent` set to 1 although
		# nothing was sent, and their own condition then suppresses it for good.
		"name": "LMS New Course Published",
		# Seeded off. Develop gated both publish mails behind an LMS Settings Select
		# that defaulted to blank, so a stock site sent neither. An admin turns
		# them on from the notification settings page.
		"enabled": 0,
		"document_type": "LMS Course",
		"event": "Value Change",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": "published",
		"condition": "doc.published and not doc.notification_sent",
		"subject": 'A new course has been published on {{ frappe.db.get_single_value("Website Settings", "app_name") }}',
		"message": PUBLISHED_COURSE_MESSAGE,
		"recipients": [
			# Data field first, child-table fieldname second. Dotted
			# "instructors.instructor" has no comma, so the whole string is read
			# as one top-level fieldname and no instructor is ever addressed.
			{"receiver_by_document_field": "instructor,instructors"},
			{"bcc": ENABLED_USERS_BCC},
		],
		"set_property_after_alert": "notification_sent",
		"property_value": "1",
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS New Batch Published",
		# Seeded off. Develop gated both publish mails behind an LMS Settings Select
		# that defaulted to blank, so a stock site sent neither. An admin turns
		# them on from the notification settings page.
		"enabled": 0,
		"document_type": "LMS Batch",
		"event": "Value Change",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": "published",
		"condition": "doc.published and not doc.notification_sent",
		"subject": 'A new batch has been published on {{ frappe.db.get_single_value("Website Settings", "app_name") }}',
		"message": PUBLISHED_BATCH_MESSAGE,
		"recipients": [
			{"receiver_by_document_field": "instructor,instructors"},
			{"bcc": ENABLED_USERS_BCC},
		],
		"set_property_after_alert": "notification_sent",
		"property_value": "1",
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		# Must stay before "LMS New Course Published". One save can change both
		# fields, and reversing the two silences this mail rather than
		# duplicating it.
		"name": "LMS Course Availability",
		"document_type": "LMS Course",
		"event": "Value Change",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		# Develop fired this when a course left "upcoming", not when it was
		# published. `upcoming` is a Check, and core casts both sides before
		# comparing, so 1 to 0 reads as a change.
		"value_changed": "upcoming",
		# No `notification_sent`-style guard on purpose. Marking a course upcoming
		# again and clearing it should re-mail everyone who registered interest
		# since, not just the first cohort.
		"condition": "not doc.upcoming",
		"subject": "{{ doc.title }} is available!",
		"message": COURSE_AVAILABILITY_MESSAGE,
		"recipients": [{"bcc": INTERESTED_USERS_BCC}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Batch Start Reminder",
		"document_type": "LMS Batch",
		"event": "Days Before",
		"method": None,
		"date_changed": "start_date",
		"days_in_advance": 1,
		"value_changed": None,
		# `doc.published` matches develop's `send_batch_start_reminder`, which
		# never reminded a draft batch.
		"condition": "doc.published and doc.show_live_class",
		"subject": "Your batch {{ doc.title }} is starting tomorrow",
		"message": BATCH_START_REMINDER_MESSAGE,
		"recipients": [{"bcc": BATCH_MEMBERS_BCC}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Batch Start Reminder (Recorded)",
		"document_type": "LMS Batch",
		"event": "Days Before",
		"method": None,
		"date_changed": "start_date",
		"days_in_advance": 1,
		"value_changed": None,
		# Same `published` filter develop's `send_batch_start_reminder` applied.
		"condition": "doc.published and not doc.show_live_class",
		"subject": "You're enrolled in {{ doc.title }} - start whenever you're ready",
		"message": BATCH_START_REMINDER_RECORDED_MESSAGE,
		"recipients": [{"bcc": BATCH_MEMBERS_BCC}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Live Class Reminder",
		"document_type": "LMS Live Class",
		"event": "Days Before",
		"method": None,
		"date_changed": "date",
		"days_in_advance": 0,
		"value_changed": None,
		"condition": "",
		"subject": "Your live class {{ doc.title }} is today",
		"message": LIVE_CLASS_REMINDER_MESSAGE,
		"recipients": [{"bcc": LIVE_CLASS_MEMBERS_BCC}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Payment Reminder",
		"document_type": "LMS Payment",
		"event": "Method",
		"method": "lms_notify",
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": PAYMENT_REMINDER_SUBJECT,
		"message": PAYMENT_REMINDER_MESSAGE,
		"recipients": [
			{"receiver_by_document_field": "member", "cc": PAYMENT_INSTRUCTORS_CC},
		],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
	{
		"name": "LMS Job Application",
		"document_type": "LMS Job Application",
		"event": "New",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": "New Job Applicant",
		"message": JOB_APPLICATION_MESSAGE,
		# The employer belongs on `recipients`, where develop put it. A rule whose
		# only recipient row is a cc renders an empty "To" header, and
		# `receiver_by_document_field` cannot follow a link, hence the mirror.
		"recipients": [{"receiver_by_document_field": "company_email"}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": "From Field",
		"from_attach_field": "resume",
	},
	{
		"name": "LMS Job Post Reported",
		"document_type": "Job Opportunity",
		"event": "Method",
		"method": "lms_notify",
		"date_changed": None,
		"days_in_advance": None,
		"value_changed": None,
		"condition": "",
		"subject": "A job post has been reported: {{ doc.job_title }}",
		"message": JOB_REPORT_MESSAGE,
		"recipients": [{"receiver_by_role": "System Manager"}],
		"set_property_after_alert": None,
		"property_value": None,
		"attach_files": None,
		"from_attach_field": None,
	},
]


def rule_names() -> list[str]:
	return [rule["name"] for rule in LMS_NOTIFICATIONS]


def seed_notifications():
	"""Create any rule the site is missing. Never rewrite one it already has.
	Not a fixture, because `sync_fixtures` imports with force and would reset an
	admin's wording on every migrate.
	"""
	for rule in LMS_NOTIFICATIONS:
		if frappe.db.exists("Notification", rule["name"]):
			continue
		insert_rule(rule)


def insert_rule(rule: dict):
	doc = frappe.new_doc("Notification")
	doc.name = rule["name"]
	doc.flags.name_set = True
	doc.module = "LMS"
	doc.is_standard = 0
	doc.enabled = rule.get("enabled", 1)
	doc.channel = "Email"
	doc.send_system_notification = 1
	doc.document_type = rule["document_type"]
	doc.event = rule["event"]
	doc.method = rule["method"]
	doc.date_changed = rule["date_changed"]
	doc.days_in_advance = rule["days_in_advance"]
	doc.value_changed = rule["value_changed"]
	doc.condition = rule["condition"]
	doc.condition_type = "Python"
	doc.subject = rule["subject"]
	doc.message = rule["message"]
	doc.message_type = "HTML"
	doc.set_property_after_alert = rule["set_property_after_alert"]
	doc.property_value = rule["property_value"]
	doc.attach_files = rule["attach_files"]
	doc.from_attach_field = rule["from_attach_field"]
	for recipient in rule["recipients"]:
		doc.append("recipients", recipient)
	# nosemgrep: lms-unjustified-ignore-permissions - seeding a rule the site owns, with no user to authorise it
	doc.insert(ignore_permissions=True)
