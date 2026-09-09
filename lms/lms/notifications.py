import frappe

# The per-site (and, for one of them, per-batch) Email Template overrides
# upstream/develop honoured. Develop reached them through
# `frappe.email.doctype.email_template.email_template.get_email_template`, which
# returns a subject as well as a message, so a custom template replaced BOTH --
# hence a pair of helpers, one per half, sharing one resolver.
#
# Resolved in Python rather than as inline Jinja because a rule's Subject is a
# Data field, capped at 140 characters: the `{% if override %}` shape the message
# bodies use does not fit in one. Both are registered under `jinja.methods` in
# `lms/hooks.py`, which `get_jinja_hooks()` merges into `jenv.globals`
# unconditionally -- after the `restrict_globals` branch -- so they are reachable
# by their bare names inside a rule's sandboxed render, the same way
# `get_lms_route` and `format_timezone` already are.
_SITE_TEMPLATE_FIELDS = {
	"LMS Batch Enrollment": "batch_confirmation_template",
	"LMS Certificate": "certification_template",
	"LMS Payment": "payment_reminder_template",
}


def _override_template(doc) -> str | None:
	"""The Email Template overriding this document's mail, if an admin picked one.

	Develop's precedence, exactly: LMS Batch Enrollment reads the batch's own
	`confirmation_email_template` first and falls back to the site-wide
	`LMS Settings.batch_confirmation_template` (`lms_batch_enrollment.py`'s
	`send_mail`). The other two have only a site-wide setting.
	"""
	if doc.doctype == "LMS Batch Enrollment":
		per_batch = frappe.db.get_value("LMS Batch", doc.batch, "confirmation_email_template")
		if per_batch:
			return per_batch

	field = _SITE_TEMPLATE_FIELDS.get(doc.doctype)
	return frappe.db.get_single_value("LMS Settings", field) if field else None


def _legacy_override_args(doc) -> dict:
	"""The flat context develop rendered an override template with.

	Develop reached the override through `get_email_template(name, args)`, which
	renders the template against the sender's own `args` dict. Every override
	written before this branch therefore names `student_name` or `billing_name`,
	never `doc`. frappe's jenv uses DebugUndefined, which emits an unknown name
	verbatim rather than blank, so a context of `doc` alone mails the literal
	text `{{ student_name }}`. Each dict below is the `args` its sender built on
	upstream/develop, key for key.
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

	# Core reads the body through `EmailTemplate.response_`, which returns
	# `response_html` when Use HTML is ticked and leaves `response` empty in that
	# case. Reading the raw `response` column returns "" for such a template, the
	# `{% if override %}` guard falls through, and the site's own wording is
	# replaced by the built-in copy with no error anywhere.
	if fieldname == "subject":
		content = row.subject
	else:
		content = row.response_html if row.use_html else row.response

	# The rendered string is an Email Template's own subject/response. Email
	# Template grants write to System Manager only, and `restrict_globals=True`
	# puts it in the same sandbox the rule's own subject and message render under
	# (`notification.py:504`/`:512`) -- this is not a wider trust boundary than the
	# inline `{{ frappe.render_template(...) }}` it replaces, which reached the
	# same field through `safe_exec.safe_render_template`.
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


# The body an admin sees first. Copied from the Jinja template this rule replaces
# (`lms/templates/emails/batch_confirmation.html` on upstream/develop) with its
# `args` names resolved against the enrollment document, and wrapped in the two
# overrides develop honoured, in develop's own precedence order: the per-batch
# template the LMS Batch form offers first, the per-site
# `LMS Settings.batch_confirmation_template` behind it. That is literally
# `batch.confirmation_email_template or frappe.db.get_single_value("LMS Settings",
# "batch_confirmation_template")` from `lms_batch_enrollment.py`'s `send_mail` on
# upstream/develop.
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

# A rule's Subject is rendered through the same restricted Jinja as its body
# (`frappe/email/doctype/notification/notification.py:504`), so the override is an
# inline expression here rather than a block -- and one line, because a `{% set %}`
# tag of its own would render a newline into the subject header.
BATCH_CONFIRMATION_SUBJECT = '{{ email_override_subject(doc) or "Enrollment Confirmation for " ~ frappe.db.get_value("LMS Batch", doc.batch, "title") }}'

# Copied from `lms/templates/emails/certification.html` on upstream/develop, with
# its `args` names resolved against the certificate document: `member_name` ->
# `doc.member_name`, `course_title` -> the course-title lookup, `name` -> `doc.name`,
# `template` -> `doc.template` (the Print Format the certificate was issued with),
# and wrapped in the per-site `LMS Settings.certification_template` override
# `lms_certificate.py`'s `send_mail` reads on upstream/develop.
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

# Same subject override `BATCH_CONFIRMATION_SUBJECT` documents, for the
# certification mail's single per-site template.
CERTIFICATION_SUBJECT = '{{ email_override_subject(doc) or "Congratulations on getting certified!" }}'

# Copied from `lms/templates/emails/certificate_request_notification.html` on
# upstream/develop, with its `args` names resolved against the certificate
# request document: `member_name` -> `doc.member_name`, `course` ->
# `course_title` (the course-title lookup), `evaluator` -> `evaluator_name`
# (looked up from the User, not the fetch_from-populated `doc.evaluator_name`,
# to match the certification message's lookup-over-cached-field style).
#
# `date` / `start_time` / `timezone` restore the original's *display*-zone
# conversion instead of rendering the system-time wall clock the document
# stores: `lms.lms_certificate_request.send_notification` used to compute a
# display timezone (`get_evaluation_display_timezone`), roll the stored
# system-time date/time into it (`convert_from_system_timezone` -- the date
# can change too, this is the part a naive substitution would get wrong), and
# label that zone (`format_timezone`). Those three live in `lms.lms.utils`,
# outside the restricted sandbox's default globals -- but LMS declares its own
# `jinja.methods` hook (`lms/hooks.py`), and `get_jinja_hooks()` merges into
# `jenv.globals` unconditionally, after the `restrict_globals` branch
# (`frappe/utils/jinja.py`), so a method listed there is reachable by its bare
# name even inside a restricted render. All three are added to that hook list
# for this. `date`/`start_time` here are the *converted* pair, shadowing
# `doc.date`/`doc.start_time` deliberately -- the email must show the instant
# in the zone the learner picked it in, not the zone it is stored in.
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

# Copied from `lms/templates/emails/published_course_notification.html` on
# upstream/develop, with its `args` names resolved against the course document:
# `brand_name` / `brand_logo` -> the Website Settings lookups, `title` ->
# `doc.title`, `short_introduction` -> `doc.short_introduction`, and the
# `instructors` loop (a list of dicts from `get_instructors`, including
# `user_image`) -> a loop over the child table itself, printing only the name
# -- one rendered body cannot show a different avatar-or-initial per recipient
# the way the old per-recipient dict did, so that half of the row is dropped.
# `course_url` was hardcoded as `/lms/courses/<name>` in the plan this replaced;
# the SPA's mount path is site-configurable (`frappe.conf.lms_path`, see
# `lms/lms/utils.py:49-58`), so the link goes through `get_lms_route`, already
# reachable bare inside a rule's sandboxed render (`lms/hooks.py`'s `jinja`
# hook).
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

# Copied from `lms/templates/emails/published_batch_notification.html` on
# upstream/develop, same substitutions as PUBLISHED_COURSE_MESSAGE, plus:
# `short_introduction` -> `doc.description` (the old sender's own `args` mapped
# it that way, not to a `short_introduction` field -- LMS Batch has none),
# `start_date` / `end_date` / `start_time` -> the matching `doc.*` fields, and
# `timezone` -> `format_timezone(doc.timezone, doc.start_date)`, also reachable
# through the `jinja` hook. `batch_url` gets the same `get_lms_route`
# correction as the course link.
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

# Copied from `lms/templates/emails/lms_course_interest.html` on upstream/develop,
# with `title` -> `doc.title`, `app_name` -> the Website Settings lookup (matching
# the other two publish mails, not the `System Settings` value the old sender
# actually read), and `course_link` / `site_url` collapsed into one absolute
# `course_url`, built the same `get_lms_route`-based way as the other two
# messages. `first_name` is dropped: this body is rendered once and bcc'd to
# every interested user, so it cannot greet each one by name the way the old
# per-recipient send did.
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

# An audience that is a query rather than a field or a role. A recipient row's
# cc/bcc is rendered as Jinja with safe globals before it is split into addresses
# (`frappe/email/doctype/notification/notification.py:905-910`), which is the only
# way core Notification can express "everyone". `get_emails_from_template` splits
# on both "," and "\n", so one name per line renders cleanly either way.
#
# Every audience query in this file uses `frappe.db.get_all`, never
# `frappe.db.get_list`. Inside a restricted render `get_all` is
# `frappe.utils.safe_exec.safe_get_all`, which forces `ignore_permissions=True`;
# `get_list` is `safe_get_list`, checked against whoever triggered the save. The
# render runs in that user's session, and every audience here is data they have
# no business reading, so `get_list` broke each one differently (all three
# reproduced on lms-audit.localhost as a Course Creator):
#
#   - `LMS Course Interest` grants read to System Manager only, so it raised
#     PermissionError. `send_notification_by_channel` catches every exception into
#     an Error Log, so a Course Creator publishing a course sent no availability
#     mail and saw no error.
#   - `LMS Batch Enrollment` grants read to LMS Student only with if_owner, so it
#     failed the other way: an empty list -- no bcc at all -- rather than raising.
#     Observed as [] both for a Course Creator and for the enrolled student.
#   - `User` silently lost Administrator and Guest to `get_permission_query_conditions`.
#
# Every audience develop computed used `frappe.get_all`, i.e. unpermissioned.
ENABLED_USERS_BCC = """{% for user in frappe.db.get_all("User", filters={"enabled": 1}, fields=["name"], limit_page_length=0) %}{{ user.name }}
{% endfor %}"""

INTERESTED_USERS_BCC = """{% for interest in frappe.db.get_all("LMS Course Interest", filters={"course": doc.name}, fields=["user"], limit_page_length=0) %}{{ interest.user }}
{% endfor %}"""

# All three reminders below are "Days Before" rules: `date_changed` names the date
# field their audience is computed from, and `Notification.get_documents_for_today`
# (frappe/email/doctype/notification/notification.py:255-275) selects rows whose
# that field falls in [nowdate() + days_in_advance, same day 23:59:59]. Both batch
# rules use days_in_advance=1 (fires the day before start_date); the live class
# rule uses days_in_advance=0 (fires the day of `date`, matching the daily job it
# replaces, which filtered on `date: nowdate()`).
#
# Their audience is a query, not a field or a role -- same reasoning as
# ENABLED_USERS_BCC / INTERESTED_USERS_BCC above -- so they bcc every current
# enrollment instead of addressing recipients individually.
#
# Copied from `batch_start_reminder.html` / `batch_start_reminder_recorded.html` /
# `live_class_reminder.html` on upstream/develop, with their `args` names resolved
# against the document each rule fires on: `title` -> `doc.title`, `start_date` ->
# `doc.start_date`, `start_time` -> `doc.start_time`, `medium` -> `doc.medium`,
# `date` -> `doc.date`, `time` -> `doc.time`, `name` -> `doc.name`, `batch_name` ->
# `doc.batch_name`, `evaluation` -> `doc.evaluation`, `evaluation_end_date` ->
# `doc.evaluation_end_date` (both real fields on LMS Batch, not passed by the old
# sender's `args` dict under a different name -- see lms_batch.py's deleted
# `send_mail`). `get_url()` + `get_lms_route(...)` replaces the templates' bare
# `get_lms_route(...)`, matching every other link in this file: the SPA's mount
# path is site-configurable and the old sender never needed an absolute link
# because `frappe.sendmail` doesn't require one, but the other five rules already
# establish the absolute-link convention.
#
# Each template opened with `Dear {{ student_name }}`. One rule renders one body
# for every bcc'd recipient, so nothing can name each of them -- the same
# constraint COURSE_AVAILABILITY_MESSAGE hit above. Reworded to the same plain
# "Hi," opener that message already uses, instead of leaving a dangling "Dear ,".
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

# The daily job (`send_payment_reminder`, `lms/lms/doctype/lms_payment/lms_payment.py`)
# keeps its own selection -- it skips a payment already paid under a different
# payment id (`has_paid_later`) and a payment for a now-sold-out batch
# (`is_batch_sold_out`), neither expressible as a rule condition -- and triggers
# this rule per surviving LMS Payment via `doc.run_method("lms_notify")`, a
# method no controller defines. `Document.run_method` still calls
# `run_notifications(method="lms_notify")` for any method name
# (`frappe/model/document.py:1690-1703`), which is what a `Method`-event rule
# matches against.
#
# `LMS Settings.payment_reminder_template` is a live per-site override, the same
# shape `BATCH_CONFIRMATION_MESSAGE` and `CERTIFICATION_MESSAGE` above keep for
# `batch_confirmation_template` and `certification_template`: if an admin has
# picked one, its Email Template subject and response replace the pair below.
# All three are read on upstream/develop -- `lms_payment.py`'s `send_mail`,
# `lms_batch_enrollment.py`'s `send_mail` and `lms_certificate.py`'s `send_mail`
# -- so all three survive the move.
#
# Body copied from `payment_reminder.html` on upstream/develop, with its
# `args` names resolved against the LMS Payment document: `billing_name` ->
# `doc.billing_name`, `type` -> the doctype-name lookup already used
# elsewhere in this file (`doc.payment_for_document_type.split(" ")[-1]`,
# lowercased), `title` -> a `frappe.db.get_value` lookup on the paid-for
# document, `link` -> the same `billing/<type>/<name>` route `send_mail`
# built, through `get_lms_route` instead of a hardcoded `/lms/` prefix.
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

# Same subject override `BATCH_CONFIRMATION_SUBJECT` documents, for the payment
# reminder's single per-site template.
PAYMENT_REMINDER_SUBJECT = (
	"""{{ email_override_subject(doc) or "Complete Your Enrollment - Don't miss out!" }}"""
)

# Same per-document instructor lookup `LMS New Course Published` /
# `LMS New Batch Published` use for a comma-separated `receiver_by_document_field`,
# but LMS Payment carries no `instructor`/`instructors` field pair to walk that
# way -- the paid-for document does. Rendered as a cc, the same shape
# `ENABLED_USERS_BCC` / `INTERESTED_USERS_BCC` use for a query-shaped audience.
#
# "Course Instructor" is a pure child table (only ever reached through LMS
# Course/LMS Batch's own Table MultiSelect), and a permission-checked query on a
# child doctype with no parent context silently drops the requested field from
# the returned rows -- `row.instructor` then renders as the literal string "None"
# for every row. `frappe.db.get_all` skips permissions outright and that field
# filtering with it, so no `parent_doctype` is needed alongside it (verified on
# lms-audit.localhost: get_all with no parent context returns `instructor`
# populated, both as Administrator and as a user who is not a System Manager).
PAYMENT_INSTRUCTORS_CC = """{% for row in frappe.db.get_all("Course Instructor", filters={"parenttype": doc.payment_for_document_type, "parent": doc.payment_for_document}, fields=["instructor"], limit_page_length=0) %}{{ row.instructor }}
{% endfor %}"""

# Copied from `lms/templates/emails/job_application.html` on upstream/develop,
# with its `args` names resolved against the LMS Job Application document:
# `full_name` -> a lookup on `doc.user`, `job_title` -> `doc.job_title` (already
# fetch_from-populated from the job). The attachment itself is not part of the
# body -- `attach_files`/`from_attach_field` on the rule below carry the resume,
# the same way `lms_job_application.py`'s deleted `send_email_to_employer` did
# with its own `attachments` kwarg.
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

# Copied from `lms/templates/emails/job_report.html` on upstream/develop, with
# its `args` names resolved against the Job Opportunity document: `job` ->
# `doc.name`, `user` -> a lookup on `doc.reported_by` (the reporting user,
# recorded by `report()` before this rule fires), `reason` -> `doc.report_reason`.
# The original template also built an unused `job_link` local (`"<a href='" +
# job_url + "'>" + job + "</a>"`) that the body never referenced -- dropped
# here rather than carried forward dead. `job_url` was a desk link
# (`get_link_to_form("Job Opportunity", job)`) in the deleted sender; this
# audience is the site's own System Managers, who use the portal like anyone
# else, so it goes through `get_lms_route` instead, matching every other link
# in this file.
JOB_REPORT_MESSAGE = """
{% set job_url = frappe.utils.get_url() ~ get_lms_route("job-openings/" ~ doc.name) %}
{% set reporter = frappe.db.get_value("User", doc.reported_by, "full_name") %}
<p>{{ _("Hey,") }}</p>
<p>{{ _("{0} has reported a job post for the following reason.").format(reporter) }}</p>
<p>" {{ doc.report_reason }} "</p>
<p>{{ _("Please take appropriate action at {0}").format(job_url) }}</p>
"""

# One entry per mail Frappe Learning sends. Each becomes a `Notification` row the
# site owns from then on: the seeder creates it once and never writes to it again,
# so an admin's wording, channel and on/off switch survive every migrate.
#
# Ordering hazard: "LMS Course Availability" and "LMS New Course Published" watch
# different fields (`upcoming` and `published`), but one save can change both --
# an admin clearing Upcoming and ticking Published together. In that save the
# availability mail survives only because it is evaluated BEFORE the publish rule.
# Reverse the two and it is SILENCED, not duplicated: the publish rule's
# `set_property_after_alert` re-enters `doc.save()` on the same document object,
# `Document.run_notifications` runs again with the availability rule still absent
# from `flags.notifications_executed`, and it is evaluated inside that reentrant
# save -- where `get_doc_before_save()` already carries the new `upcoming`, so
# core's Value Change check
# (`frappe/email/doctype/notification/notification.py:852-864`) sees no change and
# returns without sending. The name is appended to `notifications_executed` all
# the same, so the outer loop then skips it and the mail is never sent at all.
# That evaluation order falls out of `Notification`'s `sort_field: creation DESC`,
# which in turn falls out of this list's order (the availability entry is seeded
# after, so it is newer). Reordering this list, or reseeding the two rules in a
# different order, can flip that.
# One caveat this mechanism carries, deliberately left as it is. Core wraps
# `send_notification_by_channel` in a bare try/except that logs and continues,
# then applies `set_property_after_alert` unconditionally
# (`frappe/email/doctype/notification/notification.py:399-440`). On a site with
# no outgoing Email Account and no `mail_login` in site_config, `frappe.sendmail`
# raises while building the queue, so for the two publish rules below
# `notification_sent` is set to 1 although nothing was sent -- and their own
# condition then suppresses that announcement for good. The in-app copy goes with
# it, because the `send_system_notification` branch sits inside the same try.
#
# Both publish rules seed disabled, so this needs an admin to switch broadcasts
# on for a site with no outgoing mail at all. The two fixes available inside LMS
# are each worse than the defect: gating the conditions on an Email Account row
# would stop mail on sites configured only through site_config (safe_eval exposes
# no `frappe.conf`), and overriding core's Notification class would change
# behaviour for every Notification on the site, LMS or not. The real fix belongs
# in frappe.
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
		"name": "LMS New Course Published",
		# Seeded off. Each publish mail was gated on develop by an LMS Settings
		# Select -- `send_notification_for_published_courses` /
		# `send_notification_for_published_batches`, both with a blank first option
		# and no default -- so a stock site sent neither. Seeding these enabled
		# would mass-mail every enabled User, and file a Notification Log per
		# recipient, the first time anyone published a course or batch after
		# upgrading. An admin turns them on from the notification settings page,
		# which is what that page is for.
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
			# "instructor,instructors": data field first, child-table fieldname
			# second (`_parse_receiver_by_document_field`,
			# `frappe/email/doctype/notification/notification.py:921-928` --
			# proven against core's own fixture, `email_id,email_ids` in
			# `test_notification.py:98`). Dotted "instructors.instructor" has no
			# comma, so `_parse_receiver_by_document_field` treats the whole
			# string as a single top-level fieldname, `doc.get()` returns None,
			# and no instructor is ever addressed.
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
		# Seeded off. Each publish mail was gated on develop by an LMS Settings
		# Select -- `send_notification_for_published_courses` /
		# `send_notification_for_published_batches`, both with a blank first option
		# and no default -- so a stock site sent neither. Seeding these enabled
		# would mass-mail every enabled User, and file a Notification Log per
		# recipient, the first time anyone published a course or batch after
		# upgrading. An admin turns them on from the notification settings page,
		# which is what that page is for.
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
		"name": "LMS Course Availability",
		"document_type": "LMS Course",
		"event": "Value Change",
		"method": None,
		"date_changed": None,
		"days_in_advance": None,
		# Develop fired this from `LMSCourse.on_update`:
		# `if not self.upcoming and self.has_value_changed("upcoming")`. It is the
		# course leaving "upcoming" that makes it available to the people who
		# registered interest, not the course being published. `upcoming` is a
		# Check, and core casts both sides of the Value Change comparison before
		# testing them (`notification.py:852-864`), so 1 -> 0 reads as a change.
		"value_changed": "upcoming",
		# Deliberately no `notification_sent`-style guard: marking a course upcoming
		# again and then clearing it is meant to re-mail everyone who has registered
		# interest in the meantime, not just the first cohort.
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
		# selected `{"start_date": add_days(nowdate(), 1), "published": 1}` -- a
		# draft batch was never reminded.
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
		# The employer belongs on `recipients`, where develop put it
		# (`recipients=company_email` in `send_email_to_employer`). A rule whose
		# only recipient row is a cc leaves `recipients` empty, and
		# `send_an_email` passes `expose_recipients="header"`, which renders
		# `"To": ", ".join(self.recipients)` -- the empty string. `receiver_by_document_field`
		# reads a field on the document itself and cannot follow `job.`, hence the
		# fetched `company_email` mirror on LMS Job Application.
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

	Not a fixture: `sync_fixtures` imports with force, which deletes and re-inserts
	the row on every migrate and would reset an admin's wording. Not `is_standard`
	either, which makes the row read-only outside developer mode.
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
