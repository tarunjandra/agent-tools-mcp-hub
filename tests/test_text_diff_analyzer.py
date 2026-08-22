"""Unit tests for text diff analyzer."""
import unittest
from agent_tools.text_diff_analyzer import compute_text_diff

class TestTextDiffAnalyzer(unittest.TestCase):
    def test_no_changes(self):
        text = "line 1\nline 2\n"
        res = compute_text_diff(text, text)
        self.assertFalse(res["has_changes"])
        self.assertEqual(res["additions"], 0)
        self.assertEqual(res["deletions"], 0)

    def test_additions_and_deletions(self):
        a = "hello\nworld\n"
        b = "hello\nagent\nworld\n"
        res = compute_text_diff(a, b)
        self.assertTrue(res["has_changes"])
        self.assertEqual(res["additions"], 1)
        self.assertEqual(res["deletions"], 0)
        self.assertIn("+agent", res["unified_diff"])

if __name__ == "__main__":
    unittest.main()
