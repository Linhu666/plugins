import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class EntrypointTests(unittest.TestCase):
    def test_entrypoint_can_run_as_script(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, str(ROOT / "app_entry.py"), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.1.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
