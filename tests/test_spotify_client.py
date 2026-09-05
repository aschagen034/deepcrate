import pytest

from spotify_client import search_artist_tracks


class FakeSpotify:
    def __init__(self, tracks: list[dict]):
        self.tracks = tracks
        self.search_calls = []

    def search(self, **arguments):
        self.search_calls.append(arguments)

        return {
            "tracks": {
                "items": self.tracks,
            },
        }


def make_spotify_track(
    track_id: str,
    track_name: str,
    artist_name: str,
) -> dict:
    return {
        "id": track_id,
        "uri": f"spotify:track:{track_id}",
        "name": track_name,
        "artists": [
            {
                "id": f"{artist_name}-id",
                "name": artist_name,
            },
        ],
        "album": {
            "name": "Test Album",
        },
    }


def test_search_artist_tracks_uses_one_request_and_filters_results():
    spotify = FakeSpotify(
        [
            make_spotify_track(
                "track-1",
                "PAWSA Track One",
                "PAWSA",
            ),
            make_spotify_track(
                "track-1",
                "PAWSA Track One",
                "PAWSA",
            ),
            make_spotify_track(
                "wrong-track",
                "Another Track",
                "Another Artist",
            ),
            make_spotify_track(
                "track-2",
                "PAWSA Track Two",
                "PAWSA",
            ),
        ]
    )

    result = search_artist_tracks(
        spotify,
        artist_name="PAWSA",
        limit=2,
    )

    assert spotify.search_calls == [
        {
            "q": "artist:PAWSA",
            "type": "track",
            "limit": 10,
        }
    ]

    assert [
        track["spotify_id"]
        for track in result
    ] == [
        "track-1",
        "track-2",
    ]

    assert result[0] == {
        "spotify_id": "track-1",
        "spotify_uri": "spotify:track:track-1",
        "name": "PAWSA Track One",
        "artist_name": "PAWSA",
        "artist_id": "PAWSA-id",
        "album_name": "Test Album",
    }


@pytest.mark.parametrize("limit", [0, 11])
def test_search_artist_tracks_rejects_invalid_limit(limit):
    spotify = FakeSpotify([])

    with pytest.raises(
        ValueError,
        match="Track limit must be between 1 and 10",
    ):
        search_artist_tracks(
            spotify,
            artist_name="PAWSA",
            limit=limit,
        )

    assert spotify.search_calls == []