import time
from collections.abc import Callable, Collection
from typing import TypeVar

import requests
import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from retry import run_with_retries

Result = TypeVar("Result")

SPOTIFY_RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


class SpotifyTemporaryError(RuntimeError):
    """Represent a temporary Spotify failure that may succeed later."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after


def _run_spotify_operation(
    operation: Callable[[], Result],
    operation_name: str,
    sleep_func: Callable[[float], None] = time.sleep,
    retryable_status_codes: Collection[int] | None = None,
    retry_network_errors: bool = True,
) -> Result:
    """Run a Spotify operation with logged retry handling."""

    if retryable_status_codes is None:
        retryable_status_codes = (
            SPOTIFY_RETRYABLE_STATUS_CODES
        )

    def send_request() -> Result:
        try:
            return operation()
        except SpotifyException as error:
            if error.http_status not in retryable_status_codes:
                raise

            # Quota exhaustion is not a short rolling-window rate limit.
            # Let Task Scheduler retry the complete run later.
            if error.reason == "QUOTA_EXCEEDED":
                raise

            retry_after = None

            if error.http_status == 429:
                retry_after_value = error.headers.get(
                    "Retry-After"
                )

                if isinstance(
                    retry_after_value,
                    (str, int, float),
                ):
                    try:
                        retry_after = float(
                            retry_after_value
                        )
                    except ValueError:
                        retry_after = None

            raise SpotifyTemporaryError(
                str(error),
                retry_after=retry_after,
            ) from error

    def retry_delay(
        error: Exception,
        attempt: int,
    ) -> float:
        if (
            isinstance(error, SpotifyTemporaryError)
            and error.retry_after is not None
        ):
            return error.retry_after

        return min(
            2 ** (attempt - 1),
            30.0,
        )

    retryable_exceptions: tuple[type[Exception], ...] = (
        SpotifyTemporaryError,
    )

    if retry_network_errors:
        retryable_exceptions += (
            requests.Timeout,
            requests.ConnectionError,
        )

    return run_with_retries(
        send_request,
        retryable_exceptions=retryable_exceptions,
        operation_name=operation_name,
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        sleep_func=sleep_func,
        delay_for_exception=retry_delay,
    )


def authenticate() -> spotipy.Spotify:
    """Authenticate the user and return a Spotify API client."""
    load_dotenv()
    auth_manager = SpotifyOAuth(
        scope=(
            "user-read-private "
            "user-top-read "
            "playlist-read-private "
            "playlist-modify-private "
            "playlist-modify-public"
        )
    )
    return spotipy.Spotify(
        auth_manager=auth_manager,
        requests_session=False,
        requests_timeout=10,
    )


def get_current_user(
    spotify,
) -> dict | None:
    """Return the authenticated Spotify user's profile."""

    return _run_spotify_operation(
        spotify.current_user,
        operation_name="Spotify get current user",
    )


def get_top_artists(spotify, limit: int = 10) -> list[dict]:
    """Return the user's top artists over Spotify's short-term time range."""
    response = _run_spotify_operation(
        lambda: spotify.current_user_top_artists(
            limit=limit,
            time_range="short_term",
        ),
        operation_name="Spotify get top artists",
    )
    return response["items"]


def search_track(
    spotify,
    track_name: str,
    artist_name: str,
) -> dict | None:
    """Return the first of five search results with an exact, case-insensitive artist match.

    Return normalized track details, or None if no artist matches.
    """
    query = f"track:{track_name} artist:{artist_name}"

    response = _run_spotify_operation(
        lambda: spotify.search(
            q=query,
            type="track",
            limit=5,
        ),
        operation_name=(
            f"Spotify search for {track_name} by {artist_name}"
        ),
    )

    tracks = response.get(
        "tracks",
        {},
    ).get("items", [])

    for track in tracks:
        matching_artist = next(
            (
                artist
                for artist in track["artists"]
                if artist["name"].casefold()
                == artist_name.casefold()
            ),
            None,
        )

        if matching_artist:
            return {
                "spotify_id": track["id"],
                "spotify_uri": track["uri"],
                "name": track["name"],
                "artist_name": matching_artist["name"],
                "artist_id": matching_artist["id"],
                "album_name": track["album"]["name"],
            }

    return None


def search_artist_tracks(
    spotify,
    artist_name: str,
    limit: int = 5,
) -> list[dict]:
    """Return up to limit unique tracks with an exact, case-insensitive artist match.

    Filter the first ten search results; fewer than limit tracks may qualify.
    """
    if limit < 1 or limit > 10:
        raise ValueError("Track limit must be between 1 and 10")

    response = _run_spotify_operation(
        lambda: spotify.search(
            q=f"artist:{artist_name}",
            type="track",
            limit=10,
        ),
        operation_name=(
            f"Spotify search tracks for {artist_name}"
        ),
    )

    tracks = response.get(
        "tracks",
        {},
    ).get("items", [])

    matched_tracks = []
    seen_track_ids = set()

    for track in tracks:
        matching_artist = next(
            (
                artist
                for artist in track["artists"]
                if artist["name"].casefold()
                == artist_name.casefold()
            ),
            None,
        )

        if matching_artist is None:
            continue

        if track["id"] in seen_track_ids:
            continue

        matched_tracks.append(
            {
                "spotify_id": track["id"],
                "spotify_uri": track["uri"],
                "name": track["name"],
                "artist_name": matching_artist["name"],
                "artist_id": matching_artist["id"],
                "album_name": track["album"]["name"],
            }
        )
        seen_track_ids.add(track["id"])

        if len(matched_tracks) == limit:
            break

    return matched_tracks


def create_playlist(
    spotify,
    name: str,
    description: str = "",
) -> dict:
    """Create a private playlist and return its ID, name, and Spotify URL."""
    playlist = _run_spotify_operation(
        lambda: spotify.current_user_playlist_create(
            name=name,
            public=False,
            description=description,
        ),
        operation_name="Spotify create playlist",
        retryable_status_codes={429},
        retry_network_errors=False,
    )

    return {
        "spotify_id": playlist["id"],
        "name": playlist["name"],
        "spotify_url": playlist["external_urls"]["spotify"],
    }


def add_tracks_to_playlist(
    spotify,
    playlist_id: str,
    track_uris: list[str],
) -> str | None:
    """Append up to 100 track URIs and return the playlist snapshot ID.

    Return None without making a request when no tracks are supplied.
    """
    if not track_uris:
        return None

    if len(track_uris) > 100:
        raise ValueError(
            "Spotify accepts at most 100 playlist items per request"
        )

    response = _run_spotify_operation(
        lambda: spotify.playlist_add_items(
            playlist_id,
            track_uris,
        ),
        operation_name="Spotify add playlist tracks",
        retryable_status_codes={429},
        retry_network_errors=False,
    )

    return response["snapshot_id"]


def find_owned_playlist_by_name(
    spotify,
    user_id: str,
    playlist_name: str,
) -> dict | None:
    """Find the first playlist owned by user_id with a case-insensitive name match.

    Search all available pages and return None if no match is found.
    """
    offset = 0

    while True:
        response = _run_spotify_operation(
            lambda: spotify.current_user_playlists(
                limit=50,
                offset=offset,
            ),
            operation_name=(
                f"Spotify list playlists at offset {offset}"
            ),
        )

        for playlist in response.get("items", []):
            same_name = (
                playlist["name"].casefold()
                == playlist_name.casefold()
            )
            owned_by_user = (
                playlist["owner"]["id"] == user_id
            )

            if same_name and owned_by_user:
                return {
                    "spotify_id": playlist["id"],
                    "name": playlist["name"],
                    "spotify_url": (
                        playlist["external_urls"]["spotify"]
                    ),
                    "public": playlist.get("public"),
                }

        if response.get("next") is None:
            return None

        offset += response.get("limit", 50)


def replace_playlist_tracks(
    spotify,
    playlist_id: str,
    track_uris: list[str],
) -> str:
    """Replace the playlist's contents with up to 100 track URIs.

    An empty list clears the playlist. Return the playlist snapshot ID.
    """
    if len(track_uris) > 100:
        raise ValueError(
            "Spotify accepts at most 100 playlist items per request"
        )

    response = _run_spotify_operation(
        lambda: spotify.playlist_replace_items(
            playlist_id,
            track_uris,
        ),
        operation_name="Spotify replace playlist tracks",
    )

    return response["snapshot_id"]