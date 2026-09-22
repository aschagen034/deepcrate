import pytest
import spotify_client
import requests

from spotipy.exceptions import SpotifyException
from spotify_client import (
    add_tracks_to_playlist,
    authenticate,
    create_playlist,
    find_owned_playlist_by_name,
    get_current_user,
    get_top_artists,
    replace_playlist_tracks,
    search_artist_tracks,
    search_track,
)


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


class FakePlaylistUpdateSpotify:
    def __init__(self):
        self.replace_calls = []

    def playlist_replace_items(
        self,
        playlist_id,
        track_uris,
    ):
        self.replace_calls.append(
            {
                "playlist_id": playlist_id,
                "track_uris": track_uris,
            }
        )

        return {
            "snapshot_id": "new-snapshot",
        }


class FakeTopArtistsSpotify:
    def __init__(self):
        self.calls = []

    def current_user_top_artists(self, **arguments):
        self.calls.append(arguments)

        return {
            "items": [
                {
                    "id": "artist-1",
                    "name": "Test Artist",
                },
            ],
        }


class FakePlaylistCreateSpotify:
    def __init__(self):
        self.create_calls = []

    def current_user_playlist_create(
        self,
        **arguments,
    ):
        self.create_calls.append(arguments)

        return {
            "id": "playlist-1",
            "name": arguments["name"],
            "external_urls": {
                "spotify": "https://open.spotify.com/playlist/1",
            },
        }


class FakePlaylistAddSpotify:
    def __init__(self):
        self.add_calls = []

    def playlist_add_items(
        self,
        playlist_id,
        track_uris,
    ):
        self.add_calls.append(
            {
                "playlist_id": playlist_id,
                "track_uris": track_uris,
            }
        )

        return {
            "snapshot_id": "new-snapshot",
        }


class FakeCurrentUserSpotify:
    def __init__(self):
        self.call_count = 0

    def current_user(self):
        self.call_count += 1

        return {
            "id": "current-user",
            "display_name": "Test User",
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


def test_replace_playlist_tracks_replaces_all_items():
    spotify = FakePlaylistUpdateSpotify()
    track_uris = [
        "spotify:track:track-1",
        "spotify:track:track-2",
    ]

    result = replace_playlist_tracks(
        spotify,
        playlist_id="playlist-1",
        track_uris=track_uris,
    )

    assert result == "new-snapshot"
    assert spotify.replace_calls == [
        {
            "playlist_id": "playlist-1",
            "track_uris": track_uris,
        }
    ]


def test_replace_playlist_tracks_rejects_more_than_100_items():
    spotify = FakePlaylistUpdateSpotify()
    track_uris = [
        f"spotify:track:{index}"
        for index in range(101)
    ]

    with pytest.raises(
        ValueError,
        match="at most 100",
    ):
        replace_playlist_tracks(
            spotify,
            playlist_id="playlist-1",
            track_uris=track_uris,
        )

    assert spotify.replace_calls == []


def test_spotify_operation_uses_retry_after():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")

        if len(attempts) == 1:
            raise SpotifyException(
                429,
                -1,
                "Rate limited",
                headers={
                    "Retry-After": "12",
                },
            )

        return "success"

    result = spotify_client._run_spotify_operation(
        operation,
        operation_name="Spotify test operation",
        sleep_func=delays.append,
    )

    assert result == "success"
    assert len(attempts) == 2
    assert delays == [12.0]


def test_spotify_operation_retries_server_error():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")

        if len(attempts) == 1:
            raise SpotifyException(
                503,
                -1,
                "Service unavailable",
            )

        return "success"

    result = spotify_client._run_spotify_operation(
        operation,
        operation_name="Spotify test operation",
        sleep_func=delays.append,
    )

    assert result == "success"
    assert len(attempts) == 2
    assert delays == [1]


def test_spotify_operation_does_not_retry_quota_exhaustion():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise SpotifyException(
            429,
            -1,
            "Quota exceeded",
            reason="QUOTA_EXCEEDED",
        )

    with pytest.raises(SpotifyException):
        spotify_client._run_spotify_operation(
            operation,
            operation_name="Spotify test operation",
            sleep_func=delays.append,
        )

    assert len(attempts) == 1
    assert delays == []


def test_spotify_operation_does_not_retry_bad_request():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise SpotifyException(
            400,
            -1,
            "Bad request",
        )

    with pytest.raises(SpotifyException):
        spotify_client._run_spotify_operation(
            operation,
            operation_name="Spotify test operation",
            sleep_func=delays.append,
        )

    assert len(attempts) == 1
    assert delays == []


def test_get_top_artists_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakeTopArtistsSpotify()
    captured_operation_names = []

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = get_top_artists(
        spotify,
        limit=10,
    )

    assert result == [
        {
            "id": "artist-1",
            "name": "Test Artist",
        },
    ]
    assert spotify.calls == [
        {
            "limit": 10,
            "time_range": "short_term",
        },
    ]
    assert captured_operation_names == [
        "Spotify get top artists for short_term",
    ]


@pytest.mark.parametrize(
    "time_range",
    [
        "short_term",
        "medium_term",
        "long_term",
    ],
)
def test_get_top_artists_accepts_spotify_time_ranges(
    monkeypatch,
    time_range,
):
    spotify = FakeTopArtistsSpotify()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        lambda operation, operation_name: operation(),
    )

    get_top_artists(
        spotify,
        limit=10,
        time_range=time_range,
    )

    assert spotify.calls == [
        {
            "limit": 10,
            "time_range": time_range,
        },
    ]


def test_get_top_artists_rejects_invalid_time_range():
    spotify = FakeTopArtistsSpotify()

    with pytest.raises(
        ValueError,
        match="Time range must be",
    ):
        get_top_artists(
            spotify,
            time_range="weekly",
        )

    assert spotify.calls == []


def test_search_artist_tracks_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakeSpotify(
        [
            make_spotify_track(
                "track-1",
                "Test Track",
                "PAWSA",
            ),
        ]
    )
    captured_operation_names = []

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = search_artist_tracks(
        spotify,
        artist_name="PAWSA",
        limit=1,
    )

    assert len(result) == 1
    assert captured_operation_names == [
        "Spotify search tracks for PAWSA",
    ]


def test_find_owned_playlist_uses_retry_wrapper_for_each_page(
    monkeypatch,
):
    spotify = FakePlaylistSpotify(
        [
            {
                "items": [],
                "next": "next-page",
                "limit": 50,
            },
            {
                "items": [],
                "next": None,
                "limit": 50,
            },
        ]
    )
    captured_operation_names = []

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = find_owned_playlist_by_name(
        spotify,
        user_id="current-user",
        playlist_name="DeepCrate Weekly",
    )

    assert result is None
    assert captured_operation_names == [
        "Spotify list playlists at offset 0",
        "Spotify list playlists at offset 50",
    ]


def test_create_playlist_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakePlaylistCreateSpotify()
    captured_operation_names = []

    def fake_run(
        operation,
        operation_name,
        **retry_options,
    ):
        captured_operation_names.append(operation_name)

        assert retry_options == {
            "retryable_status_codes": {429},
            "retry_network_errors": False,
        }

        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = create_playlist(
        spotify,
        name="DeepCrate Weekly",
        description="Test description",
    )

    assert result == {
        "spotify_id": "playlist-1",
        "name": "DeepCrate Weekly",
        "spotify_url": "https://open.spotify.com/playlist/1",
    }
    assert spotify.create_calls == [
        {
            "name": "DeepCrate Weekly",
            "public": False,
            "description": "Test description",
        },
    ]
    assert captured_operation_names == [
        "Spotify create playlist",
    ]


def test_add_tracks_to_playlist_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakePlaylistAddSpotify()
    captured_operation_names = []
    track_uris = [
        "spotify:track:track-1",
        "spotify:track:track-2",
    ]

    def fake_run(
        operation,
        operation_name,
        **retry_options,
    ):
        captured_operation_names.append(operation_name)

        assert retry_options == {
            "retryable_status_codes": {429},
            "retry_network_errors": False,
        }

        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = add_tracks_to_playlist(
        spotify,
        playlist_id="playlist-1",
        track_uris=track_uris,
    )

    assert result == "new-snapshot"
    assert spotify.add_calls == [
        {
            "playlist_id": "playlist-1",
            "track_uris": track_uris,
        },
    ]
    assert captured_operation_names == [
        "Spotify add playlist tracks",
    ]


def test_replace_playlist_tracks_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakePlaylistUpdateSpotify()
    captured_operation_names = []
    track_uris = [
        "spotify:track:track-1",
        "spotify:track:track-2",
    ]

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = replace_playlist_tracks(
        spotify,
        playlist_id="playlist-1",
        track_uris=track_uris,
    )

    assert result == "new-snapshot"
    assert captured_operation_names == [
        "Spotify replace playlist tracks",
    ]


def test_get_current_user_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakeCurrentUserSpotify()
    captured_operation_names = []

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = get_current_user(spotify)

    assert result == {
        "id": "current-user",
        "display_name": "Test User",
    }
    assert spotify.call_count == 1
    assert captured_operation_names == [
        "Spotify get current user",
    ]


def test_search_track_uses_retry_wrapper(
    monkeypatch,
):
    spotify = FakeSpotify(
        [
            make_spotify_track(
                "track-1",
                "Example Track",
                "PAWSA",
            ),
        ]
    )
    captured_operation_names = []

    def fake_run(operation, operation_name):
        captured_operation_names.append(operation_name)
        return operation()

    monkeypatch.setattr(
        spotify_client,
        "_run_spotify_operation",
        fake_run,
    )

    result = search_track(
        spotify,
        track_name="Example Track",
        artist_name="PAWSA",
    )

    assert result is not None
    assert result["spotify_id"] == "track-1"
    assert captured_operation_names == [
        "Spotify search for Example Track by PAWSA",
    ]


def test_authenticate_disables_spotipy_internal_retries(
    monkeypatch,
):
    captured_arguments = {}
    fake_auth_manager = object()
    fake_spotify_client = object()

    monkeypatch.setattr(
        spotify_client,
        "load_dotenv",
        lambda: None,
    )
    monkeypatch.setattr(
        spotify_client,
        "SpotifyOAuth",
        lambda **arguments: fake_auth_manager,
    )

    def fake_spotify(**arguments):
        captured_arguments.update(arguments)
        return fake_spotify_client

    monkeypatch.setattr(
        spotify_client.spotipy,
        "Spotify",
        fake_spotify,
    )

    result = authenticate()

    assert result is fake_spotify_client
    assert captured_arguments == {
        "auth_manager": fake_auth_manager,
        "requests_session": False,
        "requests_timeout": 10,
    }


def test_spotify_operation_can_disable_network_retries():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise requests.Timeout("Request timed out")

    with pytest.raises(requests.Timeout):
        spotify_client._run_spotify_operation(
            operation,
            operation_name="Spotify write operation",
            sleep_func=delays.append,
            retry_network_errors=False,
        )

    assert len(attempts) == 1
    assert delays == []


def test_spotify_operation_can_restrict_retryable_statuses():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise SpotifyException(
            503,
            -1,
            "Service unavailable",
        )

    with pytest.raises(SpotifyException):
        spotify_client._run_spotify_operation(
            operation,
            operation_name="Spotify write operation",
            sleep_func=delays.append,
            retryable_status_codes={429},
        )

    assert len(attempts) == 1
    assert delays == []