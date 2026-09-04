from playlist_generator import build_playlist


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
        "track-2",
        "track-4",
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