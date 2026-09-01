from spotify_client import authenticate



def main():
    print("DeepCrate starting...")

    spotify = authenticate()
    current_user = spotify.current_user()

    print(f"Connected to Spotify as: {current_user['display_name']}")

if __name__ == "__main__":
    main()