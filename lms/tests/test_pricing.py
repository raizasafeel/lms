from unittest.mock import patch

import frappe

from lms.lms.course_import_export import add_data_to_course
from lms.lms.pricing import (
	get_price,
	get_price_preview,
	get_primary_currency,
	round_for_currency,
	validate_prices,
)
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_course_details, get_order_summary
from lms.patches.v2_0 import move_currency_prices_to_countries, move_usd_amounts_to_prices


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
		course.enable_country_prices = 1
		course.set("prices", list(rows))
		course.save()
		return course

	def india(self, **row):
		return {"country": "India", "price_type": "Fixed", "amount": 4999, "currency": "INR", **row}

	def test_buyer_with_a_row_for_their_country_pays_it(self):
		self.set_prices(self.india())

		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "India"), (4999, "INR"))

	def test_a_blank_fixed_row_currency_is_the_course_currency(self):
		# Frappe fills a new row's currency with the site default, so only an import leaves it blank.
		row = frappe._dict(idx=1, country="India", price_type="Fixed", amount=30, currency=None)

		validate_prices(frappe._dict(prices=[row]), "USD")

		self.assertEqual(row.currency, "USD")

	def test_with_subsidized_pricing_off_everyone_pays_the_regular_price(self):
		course = self.set_prices(self.india())
		course.enable_country_prices = 0
		course.save()

		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "India"), (100, "USD"))
		self.assertEqual(len(frappe.get_doc("LMS Course", self.course.name).prices), 1)

	def test_a_free_course_subsidizes_its_certificate(self):
		self.set_prices(self.india())
		self.course.db_set({"paid_course": 0, "paid_certificate": 1}, update_modified=False)
		self.addCleanup(self.course.db_set, {"paid_course": 1, "paid_certificate": 0}, update_modified=False)

		summary = get_order_summary("LMS Course", self.course.name, country="India")

		self.assertEqual((summary.amount, summary.currency), (4999, "INR"))

	def test_buyer_without_a_row_for_their_country_pays_the_regular_price(self):
		self.set_prices(self.india())

		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "Pakistan"), (100, "USD"))

	def test_percent_off_comes_off_the_regular_price_in_its_currency(self):
		self.set_prices({"country": "India", "price_type": "Percent Off", "percent_off": 33.3})

		# 33.3% off 100 USD is 66.70, rounded to whole dollars.
		self.assertEqual(get_price("LMS Course", self.course.name, 100, "USD", "India"), (67, "USD"))

	def test_rounding_follows_a_coarse_smallest_fraction(self):
		with patch("lms.lms.pricing.frappe.get_cached_value", return_value=5):
			self.assertEqual(round_for_currency(5007.4, "INR"), 5005)
		self.assertEqual(round_for_currency(19.6, "USD"), 20)

	def test_the_buyer_country_defaults_to_the_billing_country(self):
		self.set_prices(self.india())
		frappe.db.set_value("User", self.instructor.email, "country", "India")
		frappe.set_user(self.instructor.email)

		details = get_course_details(self.course.name)

		self.assertEqual(details.price, frappe.utils.fmt_money(4999, 0, "INR"))
		self.assertEqual(details.regular_price, frappe.utils.fmt_money(100, 0, "USD"))

	def test_two_rows_for_one_country_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prices(self.india(), self.india(price_type="Percent Off", percent_off=20))

	def test_a_percent_of_100_or_more_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prices(self.india(price_type="Percent Off", percent_off=100))

	def test_a_row_keeps_only_the_values_its_type_uses(self):
		course = self.set_prices(self.india(price_type="Percent Off", percent_off=30, amount=50))

		self.assertEqual((course.prices[0].amount, course.prices[0].currency), (0, None))

	def test_preview_formats_the_row_price(self):
		preview = get_price_preview(
			frappe._dict(country="India", price_type="Percent Off", percent_off=40), 100, "USD"
		)

		self.assertEqual((preview["country"], preview["amount"], preview["currency"]), ("India", 60, "USD"))
		self.assertEqual(preview["formatted"], frappe.utils.fmt_money(60, 0, "USD"))

	def test_an_imported_course_keeps_its_prices(self):
		course = frappe.new_doc("LMS Course")

		add_data_to_course(course, {"prices": [{"name": "old-row", "parent": "old-course", **self.india()}]})

		self.assertEqual((course.prices[0].country, course.prices[0].amount), ("India", 4999))
		self.assertNotEqual(course.prices[0].name, "old-row")


class TestMoveCurrencyPricesPatch(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self.course = self._create_course(f"Yen Course {frappe.generate_hash(length=6)}", "Administrator")

	def add_currency_row(self, currency, **row):
		frappe.get_doc(
			{
				"doctype": "LMS Price",
				"parenttype": "LMS Course",
				"parent": self.course.name,
				"parentfield": "prices",
				"currency": currency,
				**row,
			}
		).db_insert()

	def rows(self):
		return frappe.get_all(
			"LMS Price",
			filters={"parent": self.course.name},
			fields=["country", "price_type", "amount", "currency", "percent_off"],
			order_by="country",
		)

	def test_a_fixed_row_becomes_one_per_country_paying_in_its_currency(self):
		self.add_currency_row("USD", price_type="Fixed", amount=25)

		move_currency_prices_to_countries.execute()

		fixed = {"price_type": "Fixed", "amount": 25, "currency": "USD", "percent_off": 0}
		self.assertEqual(
			self.rows(), [{"country": "El Salvador", **fixed}, {"country": "United States", **fixed}]
		)

	def test_a_percent_off_row_keeps_its_percent_in_the_regular_currency(self):
		self.add_currency_row("JPY", price_type="Percent Off", percent_off=40)

		move_currency_prices_to_countries.execute()

		self.assertEqual(
			self.rows(),
			[
				{
					"country": "Japan",
					"price_type": "Percent Off",
					"amount": 0,
					"currency": None,
					"percent_off": 40,
				}
			],
		)

	def test_a_country_the_course_already_prices_is_left_alone(self):
		self.add_currency_row("JPY", country="Japan", price_type="Fixed", amount=500)
		self.add_currency_row("JPY", price_type="Fixed", amount=900)

		move_currency_prices_to_countries.execute()

		self.assertEqual([(row.country, row.amount) for row in self.rows()], [("Japan", 500)])

	def test_a_converted_course_has_subsidized_pricing_on(self):
		self.add_currency_row("JPY", price_type="Fixed", amount=900)

		move_currency_prices_to_countries.execute()

		self.assertEqual(frappe.db.get_value("LMS Course", self.course.name, "enable_country_prices"), 1)

	def test_running_twice_changes_nothing_more(self):
		self.add_currency_row("USD", price_type="Fixed", amount=25)

		move_currency_prices_to_countries.execute()
		first = self.rows()
		move_currency_prices_to_countries.execute()

		self.assertEqual(self.rows(), first)


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
