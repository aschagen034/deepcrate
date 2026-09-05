import pytest

from spotify_client import search_artist_tracks, find_owned_playlist_by_name


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


class FakePlaylistSpotify:
    def __init__(self, pages: list[dict]):
        self.pages = pages
        self.playlist_calls = []

    def current_user_playlists(self, **arguments):
        self.playlist_calls.append(arguments)
        return self.pages.pop(0)


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


def test_find_owned_playlist_by_name_checks_ownership_and_pages():
    spotify = FakePlaylistSpotify(
        [
            {
                "items": [
                    {
                        "id": "followed-playlist",
                        "name": "DeepCrate Weekly",
                        "owner": {
                            "id": "another-user",
                        },
                        "external_urls": {
                            "spotify": "followed-url",
                        },
                        "public": True,
                    },
                ],
                "next": "next-page",
                "limit": 50,
            },
            {
                "items": [
                    {
                        "id": "owned-playlist",
                        "name": "deepcrate weekly",
                        "owner": {
                            "id": "current-user",
                        },
                        "external_urls": {
                            "spotify": "owned-url",
                        },
                        "public": False,
                    },
                ],
                "next": None,
                "limit": 50,
            },
        ]
    )

    result = find_owned_playlist_by_name(
        spotify,
        user_id="current-user",
        playlist_name="DeepCrate Weekly",
    )

    assert result == {
        "spotify_id": "owned-playlist",
        "name": "deepcrate weekly",
        "spotify_url": "owned-url",
        "public": False,
    }

    assert spotify.playlist_calls == [
        {
            "limit": 50,
            "offset": 0,
        },
        {
            "limit": 50,
            "offset": 50,
        },
    ]


def test_find_owned_playlist_by_name_returns_none_when_missing():
    spotify = FakePlaylistSpotify(
        [
            {
                "items": [],
                "next": None,
                "limit": 50,
            },
        ]
    )

    result = find_owned_playlist_by_name(
        spotify,
        user_id="current-user",
        playlist_name="DeepCrate Weekly",
    )

    assert result is None