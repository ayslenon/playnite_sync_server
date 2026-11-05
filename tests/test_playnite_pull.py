import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.routers.sync import pull_playnite_games
from app.schemas import PlaynitePullRequest


def make_game(
    playnite_id,
    *,
    status="Jogando",
    replay_score=4,
    genres=None,
):
    return SimpleNamespace(
        playnite_id=playnite_id,
        genres=[SimpleNamespace(name=name) for name in (genres or [])],
        gameplay_status=status,
        favorite=True,
        must_test=False,
        interest_rating=5,
        replay_score=replay_score,
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

    def test_pull_hides_replay_score_for_non_finalized_games(self):
        session = FakeSession([make_game("id-1", status="Jogando", replay_score=4)])

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1"]),
            session,
        )

        self.assertIsNone(result["games"][0]["replay_score"])
        self.assertEqual(result["games"][0]["genres"], [])

    def test_pull_returns_final_score_and_only_active_fields(self):
        session = FakeSession(
            [make_game("id-1", status="Finalizado", replay_score=4)]
        )

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1"]),
            session,
        )

        game = result["games"][0]
        self.assertEqual(game["replay_score"], 4)
        self.assertEqual(
            set(game),
            {
                "playnite_id",
                "genres",
                "gameplay_status",
                "favorite",
                "must_test",
                "interest_rating",
                "replay_score",
                "updated_at",
            },
        )


if __name__ == "__main__":
    unittest.main()
