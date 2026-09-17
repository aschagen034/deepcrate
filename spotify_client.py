import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


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
    return spotipy.Spotify(auth_manager=auth_manager)


def get_top_artists(spotify, limit: int = 10) -> list[dict]:
    """Return the user's top artists over Spotify's short-term time range."""
    response = spotify.current_user_top_artists(
        limit=limit,
        time_range="short_term",
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

    response = spotify.search(
        q=query,
        type="track",
        limit=5,
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

    response = spotify.search(
        q=f"artist:{artist_name}",
        type="track",
        limit=10,
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
    playlist = spotify.current_user_playlist_create(
        name=name,
        public=False,
        description=description,
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

    response = spotify.playlist_add_items(
        playlist_id,
        track_uris,
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
        response = spotify.current_user_playlists(
            limit=50,
            offset=offset,
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

    response = spotify.playlist_replace_items(
        playlist_id,
        track_uris,
    )

    return response["snapshot_id"]