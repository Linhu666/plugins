import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PluginManifestTests(unittest.TestCase):
    def test_manifest_identity_and_interface(self):
        data = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "codex-offline-voice")
        self.assertEqual(data["version"], "0.1.0")
        self.assertEqual(data["skills"], "./skills/")
        self.assertEqual(data["interface"]["displayName"], "Codex Offline Voice")

    def test_management_scripts_exist(self):
        for name in ("install.ps1", "uninstall.ps1", "status.ps1", "build.ps1", "download-models.ps1"):
            self.assertTrue((ROOT / "scripts" / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
