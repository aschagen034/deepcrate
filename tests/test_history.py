from datetime import datetime, timedelta, timezone

import pytest

from history import (
    filter_recent_tracks,
    load_track_history,
    record_playlist_tracks,
    save_track_history,
    was_related_artist_used_recently,
    was_track_used_recently,
    prioritize_related_artists_by_history,
    record_related_artists,
    load_artist_history,
    save_artist_history,
)


def make_track(track_id: str) -> dict:
    return {
        "spotify_id": track_id,
    }


def test_load_track_history_returns_empty_for_missing_file(
    tmp_path,
):
    history_path = tmp_path / "history.json"

    assert load_track_history(history_path) == {}


def test_load_track_history_returns_empty_for_malformed_file(
    tmp_path,
):
    history_path = tmp_path / "history.json"
    history_path.write_text(
        "not valid json",
        encoding="utf-8",
    )

    assert load_track_history(history_path) == {}


def test_filter_recent_tracks_moves_recent_tracks_to_fallback():
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)

    tracks = [
        make_track("recent-track"),
        make_track("new-track"),
        make_track("old-track"),
    ]
    history = {
        "recent-track": now - timedelta(days=1),
        "old-track": now - timedelta(days=40),
    }

    result = filter_recent_tracks(
        tracks,
        history,
        cooldown_days=28,
        target_size=3,
        now=now,
    )

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "new-track",
        "old-track",
        "recent-track",
    ]


def test_filter_recent_tracks_excludes_recent_when_pool_is_large_enough():
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)

    tracks = [
        make_track("recent-track"),
        make_track("new-track-1"),
        make_track("new-track-2"),
    ]
    history = {
        "recent-track": now - timedelta(days=1),
    }

    result = filter_recent_tracks(
        tracks,
        history,
        target_size=2,
        now=now,
    )

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "new-track-1",
        "new-track-2",
    ]


def test_record_playlist_tracks_does_not_modify_original_history():
    used_at = datetime(
        2026,
        9,
        5,
        12,
        30,
        tzinfo=timezone.utc,
    )
    original_history = {}

    result = record_playlist_tracks(
        original_history,
        [make_track("track-1")],
        used_at=used_at,
    )

    assert original_history == {}
    assert result == {
        "track-1": used_at,
    }


def test_record_playlist_tracks_rejects_naive_timestamp():
    naive_timestamp = datetime(2026, 9, 5)

    with pytest.raises(ValueError):
        record_playlist_tracks(
            {},
            [make_track("track-1")],
            used_at=naive_timestamp,
        )


def test_track_history_round_trip(tmp_path):
    history_path = tmp_path / "history.json"
    used_at = datetime(
        2026,
        9,
        5,
        12,
        30,
        tzinfo=timezone.utc,
    )
    history = {
        "track-1": used_at,
    }

    save_track_history(history, history_path)
    loaded_history = load_track_history(history_path)

    assert loaded_history == history


def test_was_track_used_recently_identifies_recent_track():
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)
    history = {
        "track-1": now - timedelta(days=7),
    }

    assert was_track_used_recently(
        "track-1",
        history,
        cooldown_days=28,
        now=now,
    )


def test_was_track_used_recently_rejects_expired_track():
    now = datetime(2026, 9, 5, tzinfo=timezone.utc)
    history = {
        "track-1": now - timedelta(days=40),
    }

    assert not was_track_used_recently(
        "track-1",
        history,
        cooldown_days=28,
        now=now,
    )


def test_was_related_artist_used_recently_is_case_insensitive():
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    history = {
        "black loops": now - timedelta(days=7),
    }

    assert was_related_artist_used_recently(
        "Black Loops",
        history,
        cooldown_days=42,
        now=now,
    )


def test_was_related_artist_used_recently_rejects_expired_artist():
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    history = {
        "black loops": now - timedelta(days=50),
    }

    assert not was_related_artist_used_recently(
        "BLACK LOOPS",
        history,
        cooldown_days=42,
        now=now,
    )


def test_prioritize_related_artists_puts_fresh_artists_first():
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    artists = [
        {"name": "Recently Used"},
        {"name": "Fresh Artist"},
        {"name": "Older Fallback"},
    ]
    history = {
        "recently used": now - timedelta(days=7),
        "older fallback": now - timedelta(days=30),
    }

    result = prioritize_related_artists_by_history(
        artists,
        history,
        cooldown_days=42,
        now=now,
    )

    assert [
        artist["name"]
        for artist in result
    ] == [
        "Fresh Artist",
        "Older Fallback",
        "Recently Used",
    ]


def test_record_related_artists_normalizes_names():
    used_at = datetime(
        2026,
        9,
        24,
        12,
        30,
        tzinfo=timezone.utc,
    )
    original_history = {}

    result = record_related_artists(
        original_history,
        [
            {"name": "Black Loops"},
            {"name": "NightFunk"},
        ],
        used_at=used_at,
    )

    assert original_history == {}
    assert result == {
        "black loops": used_at,
        "nightfunk": used_at,
    }


def test_record_related_artists_rejects_naive_timestamp():
    with pytest.raises(ValueError):
        record_related_artists(
            {},
            [{"name": "Black Loops"}],
            used_at=datetime(2026, 9, 24),
        )


def test_load_artist_history_returns_empty_for_missing_file(
    tmp_path,
):
    history_path = tmp_path / "artist-history.json"

    assert load_artist_history(history_path) == {}


def test_load_artist_history_returns_empty_for_malformed_file(
    tmp_path,
):
    history_path = tmp_path / "artist-history.json"
    history_path.write_text(
        "not valid json",
        encoding="utf-8",
    )

    assert load_artist_history(history_path) == {}


def test_artist_history_round_trip(tmp_path):
    history_path = tmp_path / "artist-history.json"
    used_at = datetime(
        2026,
        9,
        24,
        12,
        30,
        tzinfo=timezone.utc,
    )
    history = {
        "black loops": used_at,
        "nightfunk": used_at,
    }

    save_artist_history(history, history_path)

    assert load_artist_history(history_path) == history