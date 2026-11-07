import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.routers.sync import pull_playnite_games
from app.schemas import PlaynitePullRequest


def make_game(
    playnite_id,
    *,
    status="Jogando",
    score=8.0,
    genres=None,
    coop_players="Até 4 Jogadores",
    coop_types=None,
    multiplayer_modes=None,
):
    return SimpleNamespace(
        playnite_id=playnite_id,
        genres=[SimpleNamespace(name=name) for name in (genres or [])],
        gameplay_status=status,
        favorite=True,
        must_test=False,
        interest_rating=5,
        score=score,
        notes="Minha nota",
        coop_players=coop_players,
        coop_type_list=lambda: coop_types if coop_types is not None else ["Sofá", "Online"],
        multiplayer_mode_list=lambda: multiplayer_modes if multiplayer_modes is not None else ["Cooperativo", "Competitivo/Versus"],
        input_recommendation="Ambos",
        updated_at="2026-08-23T12:00:00+00:00",
    )


class FakeSession:
    def __init__(self, games):
        self.games = games

    def exec(self, _statement):
        return self

    def all(self):
        return self.games


class PlaynitePullTests(unittest.TestCase):
    def test_request_normalizes_and_deduplicates_ids(self):
        request = PlaynitePullRequest(playnite_ids=[" id-1 ", "ID-1", "id-2"])
        self.assertEqual(request.playnite_ids, ["id-1", "id-2"])

    def test_request_rejects_empty_ids(self):
        with self.assertRaises(ValidationError):
            PlaynitePullRequest(playnite_ids=[" "])

    def test_pull_preserves_request_order_and_reports_missing(self):
        session = FakeSession(
            [
                make_game("id-2", genres=["Aventura"]),
                make_game("id-1", genres=["RPG", "Ação"]),
            ]
        )

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1", "id-missing", "id-2"]),
            session,
        )

        self.assertEqual(result["requested"], 3)
        self.assertEqual(result["found"], 2)
        self.assertEqual(result["not_found"], 1)
        self.assertEqual(
            [game["playnite_id"] for game in result["games"]], ["id-1", "id-2"]
        )
        self.assertEqual(result["missing_playnite_ids"], ["id-missing"])

    def test_pull_returns_final_score_and_only_active_fields(self):
        session = FakeSession(
            [make_game("id-1", status="Finalizado", score=9.5)]
        )

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1"]),
            session,
        )

        game = result["games"][0]
        self.assertEqual(game["score"], 9.5)
        self.assertEqual(game["notes"], "Minha nota")
        self.assertEqual(game["coop_type"], ["Sofá", "Online"])
        self.assertEqual(
            set(game),
            {
                "playnite_id",
                "genres",
                "gameplay_status",
                "favorite",
                "must_test",
                "interest_rating",
                "score",
                "notes",
                "coop_players",
                "coop_type",
                "multiplayer_mode",
                "input_recommendation",
                "updated_at",
            },
        )

    def test_pull_hides_inconsistent_multiplayer_data_for_single_player(self):
        session = FakeSession([
            make_game(
                "id-1",
                coop_players="1 Jogador",
                coop_types=["Sofá"],
                multiplayer_modes=["Competitivo/Versus"],
            )
        ])

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1"]),
            session,
        )

        game = result["games"][0]
        self.assertEqual(game["coop_type"], [])
        self.assertEqual(game["multiplayer_mode"], [])



if __name__ == "__main__":
    unittest.main()
