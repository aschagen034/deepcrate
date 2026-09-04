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
            "playlist-modify-private"
        )
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_top_artists(spotify, limit: int = 10) -> list[dict]:
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


def create_playlist(
    spotify,
    name: str,
    description: str = "",
) -> dict:
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