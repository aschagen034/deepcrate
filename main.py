from lastfm_client import get_artist_tags, get_similar_artists
from recommender import (
    find_strongest_artist_pair,
    find_third_artist,
    merge_similar_artists,
)
from spotify_client import authenticate, get_top_artists


def main():
    print("DeepCrate starting...")

    spotify = authenticate()
    current_user = spotify.current_user()
    top_artists = get_top_artists(spotify)

    print(f"Connected to Spotify as: {current_user['display_name']}")

    print("\nTop artists:")

    for position, artist in enumerate(top_artists, start=1):
        print(f"{position}. {artist['name']}")

    artist_tags = {}

    print("\nLast.fm tags:")

    for artist in top_artists:
        artist_name = artist["name"]
        tags = get_artist_tags(artist_name)

        if tags:
            artist_tags[artist_name] = tags
            print(f"{artist_name}: {', '.join(tags)}")
        else:
            print(f"{artist_name}: no tags found")

    if len(artist_tags) < 2:
        print("\nNot enough tagged artists to create a cluster.")
        return

    strongest_pair = find_strongest_artist_pair(artist_tags)
    third_artist = find_third_artist(artist_tags, strongest_pair)

    seed_artists = list(strongest_pair)

    if third_artist:
        seed_artists.append(third_artist)

    print("\nDeepCrate seeds:")

    for artist_name in seed_artists:
        print(artist_name)

    recommendations_by_seed = {}

    for seed_artist in seed_artists:
        recommendations_by_seed[seed_artist] = get_similar_artists(
            seed_artist,
        )

    candidate_artists = merge_similar_artists(
        recommendations_by_seed,
    )

    print(f"\nSimilar artist candidates ({len(candidate_artists)}):")

    for candidate in candidate_artists:
        relationships = ", ".join(
            (
                f"{seed_name} "
                f"({candidate['similarities'][seed_name]:.2f})"
            )
            for seed_name in candidate["recommended_by"]
        )

        print(f"{candidate['name']} - recommended by: {relationships}")


if __name__ == "__main__":
    main()