import unittest

from app.utils.playnite_assets import playnite_asset_url


class PlayniteAssetUrlTests(unittest.TestCase):
    def test_windows_path(self):
        self.assertEqual(
            playnite_asset_url("game-1", r"C:\Users\Console\cover.png"),
            "/api/covers/playnite/game-1/cover.png",
        )

    def test_windows_path_with_forward_slashes(self):
        self.assertEqual(
            playnite_asset_url("game-1", "C:/Users/Console/library/files/background.jpg"),
            "/api/covers/playnite/game-1/background.jpg",
        )

    def test_legacy_absolute_url(self):
        self.assertEqual(
            playnite_asset_url(
                "game-1", "http://legacy-host:8000/api/covers/playnite/game-1/cover.png"
            ),
            "/api/covers/playnite/game-1/cover.png",
        )

    def test_relative_url(self):
        self.assertEqual(
            playnite_asset_url("game-1", "/api/covers/playnite/game-1/cover.png"),
            "/api/covers/playnite/game-1/cover.png",
        )

    def test_missing_background(self):
        self.assertIsNone(playnite_asset_url("game-1", None))


if __name__ == "__main__":
    unittest.main()
