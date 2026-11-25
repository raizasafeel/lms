from unittest.mock import patch

import frappe

from lms.lms.course_import_export import add_data_to_course
from lms.lms.pricing import get_price, get_price_preview, get_primary_currency, round_for_currency
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_course_details
from lms.patches.v2_0 import move_usd_amounts_to_prices

USD_TO_INR = 83.4567


def exchange_rate(rate=USD_TO_INR):
	return patch("lms.lms.pricing.get_current_exchange_rate", return_value=rate)


class TestPricing(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(
			f"price-instructor-{hash}@example.com", "Price", "Instructor", ["Course Creator"]
		)
		cls.course = cls._create_course(f"Priced Course {hash}", cls.instructor.email)
		cls.course.db_set({"paid_course": 1, "course_price": 100, "currency": "USD"}, update_modified=False)

	def set_prices(self, *rows):
		course = frappe.get_doc("LMS Course", self.course.name)
		course.set("prices", list(rows))
		course.save()
		return course

	def test_buyer_with_a_fixed_row_pays_it_in_their_currency(self):
		self.set_prices({"currency": "INR", "price_type": "Fixed", "amount": 4999})

		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "India"), (4999, "INR"))

	def test_buyer_without_a_row_pays_the_primary_price(self):
		self.set_prices({"currency": "INR", "price_type": "Fixed", "amount": 4999})

		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "Germany"), (100, "USD"))

	def test_percent_off_converts_then_rounds_in_the_row_currency(self):
		with exchange_rate():
			self.set_prices({"currency": "INR", "price_type": "Percent Off", "percent_off": 40})
			price = get_price("LMS Course", self.course.name, 100, "USD", "India")

		# 100 USD is 8345.67 INR; 40% off is 5007.40, rounded to whole rupees.
		self.assertEqual(price, (5007, "INR"))

	def test_rounding_follows_a_coarse_smallest_fraction(self):
		with patch("lms.lms.pricing.frappe.get_cached_value", return_value=5):
			self.assertEqual(round_for_currency(5007.4, "INR"), 5005)
		self.assertEqual(round_for_currency(19.6, "USD"), 20)

	def test_the_buyer_country_defaults_to_the_billing_country(self):
		self.set_prices({"currency": "INR", "price_type": "Fixed", "amount": 4999})
		frappe.db.set_value("User", self.instructor.email, "country", "India")
		frappe.set_user(self.instructor.email)

		details = get_course_details(self.course.name)

		self.assertEqual(details.price, frappe.utils.fmt_money(4999, 0, "INR"))

	def test_a_row_in_the_primary_currency_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prices({"currency": "USD", "price_type": "Fixed", "amount": 90})

	def test_two_rows_for_one_currency_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prices(
				{"currency": "INR", "price_type": "Fixed", "amount": 4999},
				{"currency": "INR", "price_type": "Fixed", "amount": 3999},
			)

	def test_a_percent_of_100_or_more_is_refused(self):
		with exchange_rate(), self.assertRaises(frappe.ValidationError):
			self.set_prices({"currency": "INR", "price_type": "Percent Off", "percent_off": 100})

	def test_a_row_keeps_only_the_value_its_type_uses(self):
		course = self.set_prices(
			{"currency": "INR", "price_type": "Fixed", "amount": 4999, "percent_off": 30}
		)

		self.assertEqual(course.prices[0].percent_off, 0)

	def test_preview_formats_the_row_price(self):
		with exchange_rate():
			preview = get_price_preview(
				frappe._dict(currency="INR", price_type="Percent Off", percent_off=40), 100, "USD"
			)

		self.assertEqual(preview["amount"], 5007)
		self.assertEqual(preview["formatted"], frappe.utils.fmt_money(5007, 0, "INR"))

	def test_preview_reports_a_missing_exchange_rate(self):
		with patch("lms.lms.pricing.fetch_exchange_rate", side_effect=frappe.ValidationError("No rate")):
			frappe.cache.delete_value("lms:exchange_rate:USD:XTS")
			preview = get_price_preview(frappe._dict(currency="XTS", price_type="Percent Off"), 100, "USD")

		self.assertEqual(preview["error"], "No rate")

	def test_an_imported_course_keeps_its_prices(self):
		course = frappe.new_doc("LMS Course")
		row = {
			"name": "old-row",
			"parent": "old-course",
			"currency": "INR",
			"price_type": "Fixed",
			"amount": 4999,
		}

		add_data_to_course(course, {"prices": [row]})

		self.assertEqual((course.prices[0].currency, course.prices[0].amount), ("INR", 4999))
		self.assertNotEqual(course.prices[0].name, "old-row")


class TestPrimaryCurrency(BaseTestUtils):
	def set_primary_currency(self, currency):
		frappe.db.set_single_value("LMS Settings", "default_currency", currency)

	def test_new_courses_and_batches_take_the_primary_currency(self):
		self.set_primary_currency("EUR")
		course = self._create_course(f"Euro Course {frappe.generate_hash(length=6)}", "Administrator")
		batch = self._create_batch(
			course.name, "Administrator", title=f"Euro Batch {frappe.generate_hash(length=6)}"
		)

		self.assertEqual((course.currency, batch.currency), ("EUR", "EUR"))

	def test_a_paid_course_keeps_its_currency(self):
		self.set_primary_currency("EUR")
		course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Rupee Course {frappe.generate_hash(length=6)}",
				"short_introduction": "Priced in rupees",
				"description": "Priced in rupees",
				"paid_course": 1,
				"course_price": 4999,
				"currency": "INR",
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert()

		self.assertEqual(course.currency, "INR")

	def test_usd_when_none_is_set(self):
		self.set_primary_currency(None)

		self.assertEqual(get_primary_currency(), "USD")


class TestMoveUsdAmountsPatch(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._require(
			frappe.db.has_column("LMS Course", "amount_usd"),
			"The amount_usd column is gone, so there is nothing left to migrate.",
		)

	def make_course(self, currency, amount_usd):
		course = self._create_course(f"Usd Course {frappe.generate_hash(length=6)}", "Administrator")
		frappe.db.set_value(
			"LMS Course", course.name, {"currency": currency, "amount_usd": amount_usd}, update_modified=False
		)
		return course.name

	def usd_rows(self, course):
		return frappe.get_all(
			"LMS Price",
			filters={"parent": course, "currency": "USD"},
			fields=["price_type", "amount"],
		)

	def test_a_usd_amount_becomes_a_fixed_usd_row(self):
		course = self.make_course("INR", 60)

		move_usd_amounts_to_prices.execute()

		self.assertEqual(self.usd_rows(course), [{"price_type": "Fixed", "amount": 60}])

	def test_a_usd_course_gets_no_row(self):
		course = self.make_course("USD", 60)

		move_usd_amounts_to_prices.execute()

		self.assertEqual(self.usd_rows(course), [])

	def test_running_twice_adds_one_row(self):
		course = self.make_course("INR", 60)

		move_usd_amounts_to_prices.execute()
		move_usd_amounts_to_prices.execute()

		self.assertEqual(len(self.usd_rows(course)), 1)
