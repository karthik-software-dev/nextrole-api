import unittest
from processing.experience_parser import extract_experience
from processing.salary_parser import parse_salary


class TestProcessingParsers(unittest.TestCase):
    """Unit tests for Central Processing parsers (experience and salary)."""

    def test_extract_experience_ranges(self):
        min_e, max_e, raw_e = extract_experience("Candidate must have 1-3 years of software experience.")
        self.assertEqual(min_e, 1)
        self.assertEqual(max_e, 3)
        self.assertEqual(raw_e, "1-3 Yrs")

        min_e, max_e, raw_e = extract_experience("Requires 2 to 5 Yrs hands-on Python development.")
        self.assertEqual(min_e, 2)
        self.assertEqual(max_e, 5)
        self.assertEqual(raw_e, "2-5 Yrs")

    def test_extract_experience_minimum_and_plus(self):
        min_e, max_e, raw_e = extract_experience("At least 3 years of experience in backend development.")
        self.assertEqual(min_e, 3)
        self.assertIsNone(max_e)
        self.assertEqual(raw_e, "3+ Yrs")

        min_e, max_e, raw_e = extract_experience("Looking for 2+ yrs experience.")
        self.assertEqual(min_e, 2)
        self.assertIsNone(max_e)
        self.assertEqual(raw_e, "2+ Yrs")

    def test_extract_experience_months(self):
        min_e, max_e, raw_e = extract_experience("Requires 18 months of experience in Python.")
        self.assertEqual(min_e, 1)
        self.assertEqual(max_e, 1)
        self.assertEqual(raw_e, "1 Yrs")

    def test_parse_salary_lpa(self):
        s_min, s_max, curr = parse_salary("₹18-35 LPA")
        self.assertEqual(s_min, 1800000.0)
        self.assertEqual(s_max, 3500000.0)
        self.assertEqual(curr, "INR")

        s_min, s_max, curr = parse_salary("5-12 Lacs P.A.")
        self.assertEqual(s_min, 500000.0)
        self.assertEqual(s_max, 1200000.0)
        self.assertEqual(curr, "INR")

        s_min, s_max, curr = parse_salary("Rs. 10 - 16 Lakhs")
        self.assertEqual(s_min, 1000000.0)
        self.assertEqual(s_max, 1600000.0)
        self.assertEqual(curr, "INR")

        s_min, s_max, curr = parse_salary("Up to 25 LPA")
        self.assertIsNone(s_min)
        self.assertEqual(s_max, 2500000.0)
        self.assertEqual(curr, "INR")

    def test_parse_salary_lpa_helper(self):
        from processing.salary_parser import parse_salary_lpa
        self.assertEqual(parse_salary_lpa("₹18-35 LPA"), 26.5)
        self.assertEqual(parse_salary_lpa("Rs. 12 LPA"), 12.0)
        self.assertEqual(parse_salary_lpa("Up to 20 LPA"), 20.0)

        class MockJob:
            salary_min = 1200000.0
            salary_max = 1800000.0
            currency = "INR"

        self.assertEqual(parse_salary_lpa(MockJob()), 15.0)

    def test_parse_salary_annual_and_monthly(self):
        s_min, s_max, curr = parse_salary("₹8,00,000 - ₹10,00,000 a year")
        self.assertEqual(s_min, 800000.0)
        self.assertEqual(s_max, 1000000.0)
        self.assertEqual(curr, "INR")

        s_min, s_max, curr = parse_salary("From ₹80,000 a month")
        self.assertEqual(s_min, 960000.0)
        self.assertIsNone(s_max)
        self.assertEqual(curr, "INR")

        s_min, s_max, curr = parse_salary("No equity")
        self.assertIsNone(s_min)
        self.assertIsNone(s_max)

    def test_parse_foreign_currencies(self):
        s_min, s_max, curr = parse_salary("$80k - $120k")
        self.assertEqual(s_min, 80000.0)
        self.assertEqual(s_max, 120000.0)
        self.assertEqual(curr, "USD")

        s_min, s_max, curr = parse_salary("180k - 240k AED")
        self.assertEqual(s_min, 180000.0)
        self.assertEqual(s_max, 240000.0)
        self.assertEqual(curr, "AED")

        s_min, s_max, curr = parse_salary("60k - 90k SGD")
        self.assertEqual(s_min, 60000.0)
        self.assertEqual(s_max, 90000.0)
        self.assertEqual(curr, "SGD")

        s_min, s_max, curr = parse_salary("€70,000 - €90,000 / yr")
        self.assertEqual(s_min, 70000.0)
        self.assertEqual(s_max, 90000.0)
        self.assertEqual(curr, "EUR")

        s_min, s_max, curr = parse_salary("$100k / year")
        self.assertEqual(s_min, 100000.0)
        self.assertIsNone(s_max)
        self.assertEqual(curr, "USD")

    def test_parse_salary_lpa_foreign_conversion(self):
        from processing.salary_parser import parse_salary_lpa

        class MockForeignJob:
            def __init__(self, s_min, s_max, curr):
                self.salary_min = s_min
                self.salary_max = s_max
                self.currency = curr

        # $80k - $120k USD -> midpoint $100k * 86.5 = 86.5 LPA
        usd_lpa = parse_salary_lpa(MockForeignJob(80000.0, 120000.0, "USD"))
        self.assertAlmostEqual(usd_lpa, 86.5, places=1)

        # 180k - 240k AED -> midpoint 210k * 23.5 = 49.35 LPA
        aed_lpa = parse_salary_lpa(MockForeignJob(180000.0, 240000.0, "AED"))
        self.assertAlmostEqual(aed_lpa, 49.35, places=2)

        # Raw string conversion fallback
        raw_lpa = parse_salary_lpa("$80k - $120k")
        self.assertAlmostEqual(raw_lpa, 86.5, places=1)

    def test_format_salary_display_dual_currency(self):
        from processing.salary_parser import format_salary_display

        usd_disp = format_salary_display(80000.0, 120000.0, "USD")
        self.assertEqual(usd_disp, "$80k - $120k / yr (~₹69.2 - 103.8 LPA)")

        aed_disp = format_salary_display(180000.0, 240000.0, "AED")
        self.assertEqual(aed_disp, "AED 180k - AED 240k / yr (~₹42.3 - 56.4 LPA)")

        sgd_disp = format_salary_display(60000.0, 90000.0, "SGD")
        self.assertEqual(sgd_disp, "SGD 60k - SGD 90k / yr (~₹39.0 - 58.5 LPA)")

        inr_disp = format_salary_display(800000.0, 1400000.0, "INR")
        self.assertEqual(inr_disp, "₹8 - 14 LPA")


if __name__ == "__main__":
    unittest.main()
