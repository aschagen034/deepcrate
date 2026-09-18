import os

import requests
from dotenv import load_dotenv
from retry import run_with_retries

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
LASTFM_RETRYABLE_ERROR_CODES = {11, 16, 29}


class LastfmTemporaryError(RuntimeError):
    """Represent a temporary Last.fm failure that may succeed later."""


def _request_lastfm(
    params: dict,
) -> dict:
    """Send a Last.fm request with retries for temporary failures."""

    def send_request() -> dict:
        response = requests.get(
            LASTFM_API_URL,
            params=params,
            timeout=10,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            status_code = response.status_code

            if status_code == 429 or status_code >= 500:
                raise LastfmTemporaryError(
                    f"Last.fm returned HTTP {status_code}"
                ) from error

            raise

        data = response.json()

        if "error" not in data:
            return data

        try:
            error_code = int(data["error"])
        except (TypeError, ValueError):
            error_code = 0

        message = data.get(
            "message",
            "Last.fm API request failed",
        )

        if error_code in LASTFM_RETRYABLE_ERROR_CODES:
            raise LastfmTemporaryError(
                f"Last.fm error {error_code}: {message}"
            )

        raise RuntimeError(
            f"Last.fm error {error_code}: {message}"
        )

    return run_with_retries(
        send_request,
        retryable_exceptions=(
            requests.Timeout,
            requests.ConnectionError,
            LastfmTemporaryError,
        ),
        operation_name=(
            f"Last.fm {params.get('method', 'request')}"
        ),
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
    )


def get_artist_tags(artist_name: str, limit: int = 10) -> list[str]:
    """Fetch an artist's top Last.fm tags.
    
    Return names stripped of surrounding whitespace and converted to lowercase,
    skipping missing or empty names among the first limit tags.
    """

    # Load .env values before reading the Last.fm API key.
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    data = _request_lastfm(
        {
            "method": "artist.gettoptags",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
        }
    )

    tags = data.get("toptags", {}).get("tag", [])

    return [
        tag["name"].strip().lower()
        for tag in tags[:limit]
        if tag.get("name")
    ]


def get_similar_artists(
    artist_name: str,
    limit: int = 10,
) -> list[dict]:
    """Fetch similar artists from Last.fm.

    Return artist names and numeric similarity scores, skipping entries
    without a name.
    """

    # Load .env values before reading the Last.fm API key.
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    data = _request_lastfm(
        {
            "method": "artist.getsimilar",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
            "limit": limit,
        }
    )

    similar_artists = data.get(
        "similarartists",
        {},
    ).get("artist", [])

    return [
        {
            "name": artist["name"],
            "similarity": float(artist.get("match", 0)),
        }
        for artist in similar_artists
        if artist.get("name")
    ]


def get_artist_top_tracks(
    artist_name: str,
    limit: int = 10,
) -> list[dict]:
    """Fetch an artist's top tracks from Last.fm.
    
    Return tracks and artist names, listener and play counts, and Last.fm URLs,
    skipping entries without a track name.
    """
    # Load .env values before reading the Last.fm API key.
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    data = _request_lastfm(
        {
            "method": "artist.gettoptracks",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
            "limit": limit,
        }
    )

    tracks = data.get(
        "toptracks",
        {},
    ).get("track", [])

    return [
        {
            "name": track["name"],
            "artist_name": track.get(
                "artist",
                {},
            ).get("name", artist_name),
            "listeners": int(track.get("listeners", 0)),
            "playcount": int(track.get("playcount", 0)),
            "lastfm_url": track.get("url"),
        }
        for track in tracks
        if track.get("name")
    ]