import unittest

from scripts.verify_setup import valid_atd_frame_ids


class AtdFrameIdTests(unittest.TestCase):
    def test_accepts_sequential_ids(self):
        self.assertTrue(valid_atd_frame_ids(["1:a\n", "2:b\n", "3:c\n"], 3))

    def test_rejects_duplicate_internal_id(self):
        self.assertFalse(valid_atd_frame_ids(["1:a\n", "2:b\n", "2:c\n"], 3))

    def test_rejects_duplicate_with_matching_count_and_endpoint(self):
        # Same record count and final ID as 1..3, which the old endpoint check accepted.
        self.assertFalse(valid_atd_frame_ids(["1:a\n", "1:b\n", "3:c\n"], 3))

    def test_rejects_missing_internal_id(self):
        self.assertFalse(valid_atd_frame_ids(["1:a\n", "3:b\n", "4:c\n"], 3))

    def test_rejects_malformed_or_short_input(self):
        self.assertFalse(valid_atd_frame_ids(["1:a\n", "bad\n"], 2))
        self.assertFalse(valid_atd_frame_ids(["1:a\n"], 2))


if __name__ == "__main__":
    unittest.main()
