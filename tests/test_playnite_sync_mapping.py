import unittest

from app.routers.sync import _detect_platform, _map_completion, _playnite_to_gamecreate
from app.schemas import PlayniteGame


class PlayniteSyncMappingTests(unittest.TestCase):
    def test_managed_tags_round_trip_override_legacy_metadata(self):
        item = PlayniteGame(Id="id", Name="Teste", Platforms=["PC"],
            Categories=["coop online"], Features=["Controller Support"],
            Tags=["[Servidor] Coop: Sofá", "[Servidor] Coop: LAN",
                  "[Servidor] Jogadores: Até 4 Jogadores", "[Servidor] Tela: Versus",
                  "[Servidor] Input: Ambos", "Outra tag"], Notes="Observação")
        result = _playnite_to_gamecreate(None, item)
        self.assertEqual(result.coop_type, ["Sofá", "LAN"])
        self.assertEqual(result.coop_players, "Até 4 Jogadores")
        self.assertEqual(result.coop_screen_type, "Versus")
        self.assertEqual(result.input_recommendation, "Ambos")
        self.assertEqual(result.notes, "Observação")

    def test_empty_coop_round_trip(self):
        item = PlayniteGame(Id="id", Name="Teste", Tags=["[Servidor] Coop: Nenhum"])
        self.assertEqual(_playnite_to_gamecreate(None, item).coop_type, [])

    def test_platform_aliases(self):
        for source, expected in (
            ("macOS", "PC (Steam)"),
            ("Nintendo Game Boy Advance", "GBA"),
            ("Nintendo SNES", "SNES"),
            ("Sony PlayStation 2", "PS2"),
            ("Sony PlayStation Portable", "PSP"),
        ):
            self.assertEqual(_detect_platform(None, [source], None), expected)

    def test_portuguese_completion_statuses(self):
        self.assertEqual(_map_completion("jogando"), "Jogando")
        self.assertEqual(_map_completion("finalizado"), "Finalizado")
        self.assertEqual(_map_completion("abandonado"), "Abandonado")

    def test_empty_genres_remain_empty_and_cover_is_relative(self):
        item = PlayniteGame(
            Id="playnite-test",
            Name="Teste",
            Platforms=["PC"],
            CoverImage=r"C:\\Users\\Console\\cover.png",
        )
        result = _playnite_to_gamecreate(None, item)
        self.assertIsNotNone(result)
        self.assertEqual(result.genres, [])
        self.assertEqual(
            result.cover_url,
            "/api/covers/playnite/playnite-test/cover.png",
        )
        self.assertIsNone(result.background_url)


if __name__ == "__main__":
    unittest.main()
