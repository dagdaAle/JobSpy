import unittest

from jobspy.inpa import InPA

area = InPA._in_area


class InPAAreaTest(unittest.TestCase):
    def test_empty_or_national_location_keeps_all(self):
        self.assertTrue(area({"sedi": ["Roma"]}, ""))
        self.assertTrue(area({"sedi": ["Roma"]}, None))
        self.assertTrue(area({"sedi": ["Roma"]}, "Italia"))

    def test_no_sedi_is_excluded(self):
        self.assertFalse(area({"sedi": []}, "Verona"))
        self.assertFalse(area({}, "Verona"))

    def test_province_match(self):
        self.assertTrue(area({"sedi": ["Verona"]}, "Verona"))

    def test_province_match_even_with_national_sede(self):
        self.assertTrue(area({"sedi": ["Italia", "Verona"]}, "Verona"))

    def test_national_only_is_excluded(self):
        self.assertFalse(area({"sedi": ["Italia"]}, "Verona"))
        self.assertFalse(area({"sedi": ["Tutto il territorio nazionale"]}, "Verona"))
        self.assertFalse(area({"sedi": ["Nazionale"]}, "Verona"))

    def test_region_wide_only(self):
        self.assertTrue(area({"sedi": ["Veneto"]}, "Verona"))
        self.assertFalse(area({"sedi": ["Veneto", "Padova"]}, "Verona"))
        self.assertFalse(area({"sedi": ["Italia", "Veneto"]}, "Verona"))

    def test_case_and_spaces(self):
        self.assertTrue(area({"sedi": [" VERONA "]}, "  Verona , Veneto"))


if __name__ == "__main__":
    unittest.main()
