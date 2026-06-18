import unittest


class TimeUtilsTest(unittest.TestCase):
    def test_utc_database_timestamp_is_displayed_as_shanghai_time(self):
        from services.time_utils import to_local_display

        self.assertEqual(
            to_local_display("2026-06-18 15:54:55"),
            "2026-06-18 23:54:55",
        )

    def test_local_date_filter_uses_utc_bounds(self):
        from services.time_utils import local_date_bounds_utc

        self.assertEqual(
            local_date_bounds_utc("2026-06-19"),
            ("2026-06-18 16:00:00", "2026-06-19 16:00:00"),
        )


if __name__ == "__main__":
    unittest.main()
