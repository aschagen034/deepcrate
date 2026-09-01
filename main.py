from spotify_client import authenticate, get_top_artists


def main():
    print("DeepCrate starting...")

    spotify = authenticate()
    current_user = spotify.current_user()
    top_artists = get_top_artists(spotify)

    print(f"Connected to Spotify as: {current_user['display_name']}")

    for position, artist in enumerate(top_artists, start=1):
        print(f"{position}. {artist['name']}")


if __name__ == "__main__":
    main()