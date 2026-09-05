import random

import pytest

from playlist_generator import (
    add_ranking_variety,
    build_playlist,
    interleave_tracks_by_artist,
)


def make_track(
    track_id: str,
    artist_id: str,
) -> dict:
    return {
        "spotify_id": track_id,
        "artist_id": artist_id,
    }


def test_build_playlist_removes_duplicate_spotify_tracks():
    ranked_tracks = [
        make_track("track-1", "artist-1"),
        make_track("track-1", "artist-1"),
        make_track("track-2", "artist-2"),
    ]

    result = build_playlist(ranked_tracks)

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "track-1",
        "track-2",
    ]


def test_build_playlist_limits_tracks_per_artist():
    ranked_tracks = [
        make_track("track-1", "artist-1"),
        make_track("track-2", "artist-1"),
        make_track("track-3", "artist-1"),
        make_track("track-4", "artist-2"),
    ]

    result = build_playlist(
        ranked_tracks,
        max_tracks_per_artist=2,
    )

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "track-1",
        "track-4",
        "track-2",
    ]


def test_build_playlist_stops_at_target_size():
    ranked_tracks = [
        make_track(
            track_id=f"track-{index}",
            artist_id=f"artist-{index // 5}",
        )
        for index in range(60)
    ]

    result = build_playlist(
        ranked_tracks,
        target_size=50,
        max_tracks_per_artist=5,
    )

    assert len(result) == 50


def test_interleave_tracks_spreads_artists_apart():
    tracks = [
        make_track("artist-1-track-1", "artist-1"),
        make_track("artist-1-track-2", "artist-1"),
        make_track("artist-2-track-1", "artist-2"),
        make_track("artist-2-track-2", "artist-2"),
        make_track("artist-3-track-1", "artist-3"),
    ]

    result = interleave_tracks_by_artist(tracks)

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "artist-1-track-1",
        "artist-2-track-1",
        "artist-3-track-1",
        "artist-1-track-2",
        "artist-2-track-2",
    ]


def test_add_ranking_variety_is_repeatable_with_seed():
    ranked_tracks = [
        {
            **make_track(f"track-{index}", f"artist-{index}"),
            "recommendation_score": 1.0,
        }
        for index in range(10)
    ]

    first_result = add_ranking_variety(
        ranked_tracks,
        rng=random.Random(42),
    )
    second_result = add_ranking_variety(
        ranked_tracks,
        rng=random.Random(42),
    )

    assert [
        track["spotify_id"]
        for track in first_result
    ] == [
        track["spotify_id"]
        for track in second_result
    ]


def test_add_ranking_variety_changes_equal_score_order():
    ranked_tracks = [
        {
            **make_track(f"track-{index}", f"artist-{index}"),
            "recommendation_score": 1.0,
        }
        for index in range(10)
    ]

    first_result = add_ranking_variety(
        ranked_tracks,
        rng=random.Random(1),
    )
    second_result = add_ranking_variety(
        ranked_tracks,
        rng=random.Random(2),
    )

    assert [
        track["spotify_id"]
        for track in first_result
    ] != [
        track["spotify_id"]
        for track in second_result
    ]


def test_add_ranking_variety_preserves_large_score_difference():
    ranked_tracks = [
        {
            **make_track("high-score", "artist-1"),
            "recommendation_score": 10.0,
        },
        {
            **make_track("low-score", "artist-2"),
            "recommendation_score": 1.0,
        },
    ]

    result = add_ranking_variety(
        ranked_tracks,
        variation=0.20,
        rng=random.Random(42),
    )

    assert result[0]["spotify_id"] == "high-score"


def test_add_ranking_variety_rejects_invalid_variation():
    with pytest.raises(ValueError):
        add_ranking_variety([], variation=1.1)