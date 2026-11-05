import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.routers.sync import _normalize_score_for_playnite, pull_playnite_games
from app.schemas import PlaynitePullRequest


def make_game(
    playnite_id,
    *,
    status="Jogando",
    replay_score=4,
    score="8/10",
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
        score=score,
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
            [make_game("id-1", status="Finalizado", replay_score=4, score="9.5")]
        )

        result = pull_playnite_games(
            PlaynitePullRequest(playnite_ids=["id-1"]),
            session,
        )

        game = result["games"][0]
        self.assertEqual(game["replay_score"], 4)
        self.assertEqual(game["score"], "9.5/10")
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
                "score",
                "updated_at",
            },
        )

    def test_score_normalization_accepts_supported_formats(self):
        cases = {
            "8": "8/10",
            "8/10": "8/10",
            "9.5": "9.5/10",
            "9,5": "9.5/10",
            " 7,50 / 10 ": "7.5/10",
            "0": "0/10",
            "10.0": "10/10",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(_normalize_score_for_playnite(raw), expected)

    def test_score_normalization_rejects_missing_invalid_or_out_of_range(self):
        invalid_values = (
            None,
            "",
            " ",
            "abc",
            "8/5",
            "8/10/10",
            "-1",
            "10.1",
        )
        for raw in invalid_values:
            with self.subTest(raw=raw):
                self.assertIsNone(_normalize_score_for_playnite(raw))


if __name__ == "__main__":
    unittest.main()
