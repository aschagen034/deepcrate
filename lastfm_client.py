import os

import requests
from dotenv import load_dotenv

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"


def get_artist_tags(artist_name: str, limit: int = 10) -> list[str]:
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": "artist.gettoptags",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data.get("message", "Last.fm API request failed"))

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
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": "artist.getsimilar",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data.get("message", "Last.fm API request failed"))

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
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from .env")

    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": "artist.gettoptracks",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1,
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data.get("message", "Last.fm API request failed"))
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