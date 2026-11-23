"""What every certificate design prints. Fonts and the QR code travel inside the HTML because
wkhtmltopdf, Chromium and the sandboxed preview iframe cannot all fetch them while rendering."""

import base64
import functools
import io
from contextlib import contextmanager
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import add_years, get_url, getdate, nowdate

from lms.lms.utils import get_instructors, resolve_text_direction

DESIGNS = ("classic", "modern", "minimal", "ledger", "banner", "corners", "record")
MAX_PEOPLE = 4
SAMPLE_ID = "SAMPLE0000"

# Longest name/title (in characters) each pixel size still fits, per design. The last
# step has no limit: long names wrap instead of being cut.
TEXT_SIZES = {
	"classic": (((26, 56), (36, 46), (None, 38)), ((40, 30), (70, 25), (None, 21))),
	"modern": (((22, 76), (32, 60), (44, 48), (None, 42)), ((40, 34), (70, 28), (None, 23))),
	"minimal": (((26, 52), (38, 42), (None, 36)), ((40, 26), (70, 22), (None, 19))),
	"ledger": (((22, 60), (32, 48), (44, 40), (None, 34)), ((40, 28), (70, 24), (None, 20))),
	"banner": (((24, 54), (34, 44), (None, 36)), ((40, 26), (70, 22), (None, 19))),
	"corners": (((24, 58), (36, 46), (None, 38)), ((40, 28), (70, 23), (None, 20))),
	"record": (((22, 68), (32, 54), (44, 44), (None, 38)), ((40, 24), (70, 20), (None, 18))),
}

FONT_DIR = ("public", "fonts", "certificates")
FONT_FACES = {
	"sans": (
		("LMS Sans", "NotoSans-Regular.woff", 400, "normal"),
		("LMS Sans", "NotoSans-Bold.woff", 700, "normal"),
		("LMS Sans Arabic", "NotoSansArabic-Regular.woff", 400, "normal"),
		("LMS Sans Arabic", "NotoSansArabic-Bold.woff", 700, "normal"),
	),
	"serif": (
		("LMS Serif", "NotoSerif-Regular.woff", 400, "normal"),
		("LMS Serif", "NotoSerif-Bold.woff", 700, "normal"),
		("LMS Serif", "NotoSerif-Italic.woff", 400, "italic"),
		("LMS Naskh Arabic", "NotoNaskhArabic-Regular.woff", 400, "normal"),
		("LMS Naskh Arabic", "NotoNaskhArabic-Bold.woff", 700, "normal"),
	),
	"mono": (("LMS Mono", "NotoSansMono-Regular.woff", 400, "normal"),),
}
ARABIC_LIST_LANGUAGES = ("ar", "fa", "ur", "ps")


def get_certificate_context(doc, design: str = "classic") -> frappe._dict:
	"""Everything a certificate design prints for `doc`, an LMS Certificate that may be unsaved."""
	preview = doc.flags.certificate_preview or {}
	lang = preview.get("language") or get_certificate_language()
	labels = get_labels(lang)
	kind = preview.get("kind") or ("course" if doc.course else "batch")
	title = get_certificate_title(doc, kind)
	name = doc.member_name or frappe.db.get_value("User", doc.member, "full_name") or ""
	certificate_id = doc.name or SAMPLE_ID
	verify_url = get_verification_url(certificate_id)
	name_size, title_size = get_text_sizes(design, name, title)
	return frappe._dict(
		{
			"lang": lang,
			"direction": resolve_text_direction(lang),
			"labels": labels,
			"kind": kind,
			"completed": labels.completed_batch if kind == "batch" else labels.completed_course,
			"kind_label": labels.batch if kind == "batch" else labels.course,
			"name": name,
			"title": title,
			"name_size": name_size,
			"title_size": title_size,
			"issued": format_certificate_date(doc.issue_date, lang),
			"expires": format_certificate_date(doc.expiry_date, lang),
			"certificate_id": certificate_id,
			"verify_url": verify_url,
			"verify_short": verify_url.split("://", 1)[-1],
			"qr_code": get_qr_code(verify_url),
			"font_css": get_certificate_font_css("serif" if design == "classic" else "sans"),
			**get_issuer(hide_logo=preview.get("hide_logo")),
			**get_people(doc, lang, labels, preview.get("people")),
		}
	)


def get_certificate_language() -> str:
	return frappe.db.get_single_value("System Settings", "language") or "en"


def get_labels(lang: str) -> frappe._dict:
	return frappe._dict(
		{
			"heading": _("Certificate of completion", lang=lang),
			"certifies": _("This certifies that", lang=lang),
			"awarded_to": _("Awarded to", lang=lang),
			"completed_course": _("has completed the course", lang=lang),
			"completed_batch": _("has completed the batch", lang=lang),
			"issued": _("Date of issue", lang=lang),
			"valid_until": _("Valid until", lang=lang),
			"certificate_id": _("Certificate ID", lang=lang),
			"verify_at": _("Verify at", lang=lang),
			"instructor": _("Instructor", lang=lang),
			"instructors": _("Instructors", lang=lang),
			"evaluator": _("Evaluator", lang=lang),
			"taught_by": _("Taught by", lang=lang),
			"evaluated_by": _("Evaluated by", lang=lang),
			"course": _("Course", lang=lang),
			"batch": _("Batch", lang=lang),
		}
	)


def get_certificate_title(doc, kind: str) -> str:
	if kind == "course":
		return doc.course_title or frappe.db.get_value("LMS Course", doc.course, "title") or ""
	if doc.batch_title or not doc.batch_name:
		return doc.batch_title or ""
	return frappe.db.get_value("LMS Batch", doc.batch_name, "title") or ""


def get_text_sizes(design: str, name: str, title: str) -> tuple[int, int]:
	name_steps, title_steps = TEXT_SIZES.get(design, TEXT_SIZES["classic"])
	return pick_size(len(name), name_steps), pick_size(len(title), title_steps)


def pick_size(length: int, steps) -> int:
	for limit, size in steps:
		if limit is None or length <= limit:
			return size
	return steps[-1][1]


def format_certificate_date(value, lang: str) -> str:
	if not value:
		return ""
	from babel.core import UnknownLocaleError
	from babel.dates import format_date

	try:
		return format_date(getdate(value), "d MMMM y", locale=lang.replace("-", "_"))
	except (UnknownLocaleError, ValueError):
		return format_date(getdate(value), "d MMMM y", locale="en")


def get_verification_url(certificate_id: str) -> str:
	return get_url(f"/certificates/{certificate_id}")


def get_qr_code(url: str) -> str:
	"""An SVG data URI, as frappe's two-factor setup renders its QR code."""
	from pyqrcode import create

	stream = io.BytesIO()
	create(url, error="M").svg(
		stream, scale=1, omithw=True, quiet_zone=0, module_color="#171717", background="#ffffff"
	)
	return "data:image/svg+xml;base64," + base64.b64encode(stream.getvalue()).decode()


def get_issuer(hide_logo: bool = False) -> dict:
	logo = None if hide_logo else frappe.db.get_single_value("Website Settings", "banner_image")
	return {
		"site_name": frappe.db.get_single_value("Website Settings", "app_name") or "Frappe Learning",
		"logo": get_url(logo) if logo else "",
	}


def get_people(doc, lang: str, labels: frappe._dict, sample: list | None = None) -> dict:
	"""The evaluator when one signed off, else up to four instructors of the course or batch."""
	if sample:
		names = sample[:MAX_PEOPLE]
		label = labels.instructors if len(names) > 1 else labels.instructor
		prefix = labels.taught_by
	elif doc.evaluator:
		evaluator = doc.evaluator_name or frappe.db.get_value("User", doc.evaluator, "full_name") or ""
		names, label, prefix = [evaluator], labels.evaluator, labels.evaluated_by
	else:
		doctype, parent = ("LMS Course", doc.course) if doc.course else ("LMS Batch", doc.batch_name)
		names = [row.full_name for row in get_instructors(doctype, parent)][:MAX_PEOPLE] if parent else []
		label = labels.instructors if len(names) > 1 else labels.instructor
		prefix = labels.taught_by
	people = join_names(names, lang)
	return {
		"people": names,
		"people_label": label,
		"people_names": people,
		"people_line": f"{prefix} {people}" if people else "",
	}


def join_names(names: list[str], lang: str) -> str:
	""" "A", "A and B", "A, B and C" in the certificate's language."""
	if len(names) <= 1:
		return names[0] if names else ""
	separator = "، " if lang.split("-")[0] in ARABIC_LIST_LANGUAGES else ", "
	return _("{0} and {1}", lang=lang).format(separator.join(names[:-1]), names[-1])


@functools.lru_cache(maxsize=4)
def get_certificate_font_css(family: str) -> str:
	"""@font-face rules for the bundled Noto fonts as data URIs. The files are static, so
	one read per process is enough."""
	faces = FONT_FACES[family] + FONT_FACES["mono"]
	return "".join(font_face_rule(*face) for face in faces)


def font_face_rule(family: str, filename: str, weight: int, style: str) -> str:
	data = base64.b64encode(Path(frappe.get_app_path("lms", *FONT_DIR), filename).read_bytes()).decode()
	return (
		f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:{style};"
		f"src:url(data:font/woff;base64,{data}) format('woff')}}"
	)


SCREEN_RESET = (
	"<style>@media screen{.print-hide,.action-banner{display:none!important}"
	".print-format-gutter{padding:0!important;background:#fff!important}"
	".print-format{max-width:none!important;min-height:0!important;padding:0!important;"
	"margin:0!important;border-radius:0!important}}</style>"
)


def as_screen_document(html: str) -> str:
	"""A printview page shown in a browser frame, without the print toolbar and grey gutter
	that frappe adds on screen, so it looks like the PDF."""
	return html.replace("</head>", SCREEN_RESET + "</head>", 1)


@contextmanager
def print_permissions_checked():
	"""For callers that have already decided the viewer may see the certificate."""
	previous = frappe.flags.ignore_print_permissions
	frappe.flags.ignore_print_permissions = True
	try:
		yield
	finally:
		frappe.flags.ignore_print_permissions = previous


def render_certificate(certificate: str, print_format: str) -> str | None:
	"""A saved certificate as HTML. The caller has already decided the viewer may see it."""
	try:
		with print_permissions_checked():
			html = frappe.get_print("LMS Certificate", certificate, print_format, no_letterhead=1)
	except Exception:
		frappe.log_error(title=f"Certificate render failed: {certificate}")
		return None
	return as_screen_document(html)


def get_certificate_pdf(certificate: str, print_format: str) -> bytes:
	"""A saved certificate as PDF. The caller has already decided the viewer may see it."""
	with print_permissions_checked():
		return frappe.get_print("LMS Certificate", certificate, print_format, as_pdf=True, no_letterhead=1)


PREVIEW_OPTIONS = ("long", "batch", "expiry", "no_logo", "rtl")
SAMPLE = {
	"en": {
		"name": "Maya Fernandes",
		"long_name": "Maximiliana Alexandra Wójcik-Fitzgerald Okonkwo",
		"long_title": "Advanced data analysis and interactive dashboard design for decision makers",
		"batch_title": "Spring 2026 cohort",
		"people": ["Ana Ruiz", "Wei Chen", "Rahul Mehta", "Sara Okafor"],
	},
	"ar": {
		"name": "ليلى عبد الرحمن",
		"long_name": "عبد الرحمن بن محمد بن إبراهيم الفلاحي القحطاني",
		"long_title": "تحليل البيانات المتقدم وتصميم لوحات المعلومات التفاعلية لصناع القرار",
		"batch_title": "دفعة ربيع 2026",
		"people": ["سارة الخطيب"],
	},
}


def render_certificate_preview(print_format: str, course: str, options: dict) -> str | None:
	"""`print_format` rendered for an unsaved certificate of `course` with sample data. A custom
	design that cannot render sample data returns None instead of a traceback."""
	doc = build_preview_certificate(course, options)
	try:
		with print_permissions_checked():
			html = frappe.get_print("LMS Certificate", None, print_format, doc=doc, no_letterhead=1)
	except Exception:
		frappe.log_error(title=f"Certificate design preview failed: {print_format}")
		return None
	return as_screen_document(html)


def build_preview_certificate(course: str, options: dict):
	sample = SAMPLE["ar" if options.get("rtl") else "en"]
	title = sample["long_title"] if options.get("long") or options.get("rtl") else None
	doc = frappe.new_doc("LMS Certificate")
	doc.update(
		{
			"course": course,
			"member": frappe.session.user,
			"member_name": sample["long_name"] if options.get("long") else sample["name"],
			"course_title": title or frappe.db.get_value("LMS Course", course, "title"),
			"batch_title": sample["batch_title"] if options.get("batch") else None,
			"issue_date": nowdate(),
			"expiry_date": add_years(nowdate(), 2) if options.get("expiry") else None,
		}
	)
	if options.get("batch"):
		doc.course_title = None
	people = sample["people"] if options.get("long") or options.get("rtl") else None
	doc.flags.certificate_preview = {
		"kind": "batch" if options.get("batch") else "course",
		"hide_logo": bool(options.get("no_logo")),
		"language": "ar" if options.get("rtl") else None,
		"people": people,
	}
	return doc
