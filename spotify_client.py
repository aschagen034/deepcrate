import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


def authenticate() -> spotipy.Spotify:
    """Authenticate the user and return a Spotify API client."""
    load_dotenv()
    auth_manager = SpotifyOAuth(scope="user-read-private user-top-read")
    return spotipy.Spotify(auth_manager=auth_manager)


def get_top_artists(spotify, limit: int = 10) -> list[dict]:
    response = spotify.current_user_top_artists(
        limit=limit,
        time_range="short_term",
    )
    return response["items"]
