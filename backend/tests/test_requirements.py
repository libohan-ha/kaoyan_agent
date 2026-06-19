from pathlib import Path
import unittest


class RequirementsTest(unittest.TestCase):
    def test_httpx_is_pinned_for_openai_client_compatibility(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("httpx==0.27.2", requirements)


if __name__ == "__main__":
    unittest.main()
