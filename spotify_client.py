import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


def authenticate() -> spotipy.Spotify:
    """Authenticate the user and return a Spotify API client."""
    load_dotenv()
    auth_manager = SpotifyOAuth(scope="user-read-private")
    return spotipy.Spotify(auth_manager=auth_manager)
