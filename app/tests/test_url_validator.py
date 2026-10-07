import unittest
from processing.url_validator import validate_and_classify_url


class TestUrlValidator(unittest.TestCase):
    def test_direct_ats_classification(self):
        workday = "https://jll.wd1.myworkdayjobs.com/jllcareers/job/Bengaluru-KA/Software-Engineer-2_REQ534756?utm_source=indeed"
        apply_type, provider, clean_url = validate_and_classify_url(workday)
        self.assertEqual(apply_type, "DIRECT_ATS")
        self.assertEqual(provider, "Workday ATS")
        self.assertNotIn("utm_source", clean_url)

        greenhouse = "https://grnh.se/9vmc2qu12us"
        apply_type, provider, _ = validate_and_classify_url(greenhouse)
        self.assertEqual(apply_type, "DIRECT_ATS")
        self.assertEqual(provider, "Greenhouse ATS")

        ashby = "https://jobs.ashbyhq.com/airbound/953d420d"
        apply_type, provider, _ = validate_and_classify_url(ashby)
        self.assertEqual(apply_type, "DIRECT_ATS")
        self.assertEqual(provider, "Ashby ATS")

    def test_aggregator_redirect_classification(self):
        indeed_redirect = "http://in.indeed.com/job/sde-ii-backend-distributed-systems-4786fe4e27af9430"
        apply_type, provider, _ = validate_and_classify_url(indeed_redirect)
        self.assertEqual(apply_type, "AGGREGATOR_REDIRECT")
        self.assertEqual(provider, "Indeed Redirect")

    def test_company_careers_classification(self):
        cisco = "https://careers.cisco.com/global/en/job/2024098"
        apply_type, provider, _ = validate_and_classify_url(cisco)
        self.assertEqual(apply_type, "COMPANY_CAREERS")
        self.assertIn("Company Careers", provider)

    def test_generic_homepage_rejection(self):
        homepage = "https://www.google.com/"
        apply_type, provider, _ = validate_and_classify_url(homepage)
        self.assertEqual(apply_type, "MISSING")
        self.assertIsNone(provider)

    def test_empty_or_none(self):
        self.assertEqual(validate_and_classify_url(None)[0], "MISSING")
        self.assertEqual(validate_and_classify_url("")[0], "MISSING")

    def test_check_url_liveness_closed_banner(self):
        from unittest.mock import MagicMock, patch
        from processing.url_validator import check_url_liveness

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"<html><body>We are currently not accepting applications for this job.</body></html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            is_active, reason = check_url_liveness("https://intugine.freshteam.com/jobs/123")
            self.assertFalse(is_active)
            self.assertIn("CLOSED_BANNER", reason)

    def test_check_url_liveness_active(self):
        from unittest.mock import MagicMock, patch
        from processing.url_validator import check_url_liveness

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"<html><body>Apply now for this backend role with Python!</body></html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            is_active, reason = check_url_liveness("https://target.wd5.myworkdayjobs.com/job/123")
            self.assertTrue(is_active)
            self.assertEqual(reason, "ACTIVE")

    def test_check_url_liveness_404(self):
        import urllib.error
        from unittest.mock import patch
        from processing.url_validator import check_url_liveness

        err = urllib.error.HTTPError("https://example.com/404", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            is_active, reason = check_url_liveness("https://example.com/404")
            self.assertFalse(is_active)
            self.assertEqual(reason, "HTTP_404")


if __name__ == "__main__":
    unittest.main()

