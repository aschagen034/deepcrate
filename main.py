from lastfm_client import (
    get_artist_tags,
    get_artist_top_tracks,
    get_similar_artists,
)
from recommender import (
    find_strongest_artist_pair,
    find_third_artist,
    merge_similar_artists,
    rank_candidates,
)
from spotify_client import (
    authenticate,
    get_top_artists,
    search_track,
)
from playlist_generator import build_playlist


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

    seed_track_candidates = []

    print("\nSeed artist tracks:")
    for seed_artist in seed_artists:
        lastfm_tracks = get_artist_top_tracks(
            seed_artist,
            limit=5,
        )

        for lastfm_track in lastfm_tracks:
            spotify_track = search_track(
                spotify,
                lastfm_track["name"],
                lastfm_track["artist_name"],
            )

            if spotify_track is None:
                print(
                    f"Not found on Spotify: "
                    f"{lastfm_track['name']} - "
                    f"{lastfm_track['artist_name']}"
                )
                continue

            candidate_track = spotify_track.copy()
            candidate_track["source"] = "seed_artist"
            candidate_track["source_artist"] = seed_artist
            candidate_track["lastfm_listeners"] = (
                lastfm_track["listeners"]
            )
            candidate_track["lastfm_playcount"] = (
                lastfm_track["playcount"]
            )

            seed_track_candidates.append(candidate_track)

            print(
                f"{candidate_track['name']} - "
                f"{candidate_track['artist_name']} "
                f"({candidate_track['album_name']})"
            )

    print(
        f"\nVerified seed track candidates: "
        f"{len(seed_track_candidates)}"
    )

    related_artists_per_seed = 4
    tracks_per_related_artist = 5

    seed_name_keys = {
        seed_artist.casefold()
        for seed_artist in seed_artists
    }
    candidate_lookup = {
        candidate["name"].casefold(): candidate
        for candidate in candidate_artists
    }

    selected_related_artists = []
    selected_related_keys = set()

    for seed_artist in seed_artists:
        selected_for_seed = 0

        for related_artist in recommendations_by_seed[seed_artist]:
            artist_key = related_artist["name"].casefold()

            if artist_key in seed_name_keys:
                continue

            if artist_key in selected_related_keys:
                continue

            merged_artist = candidate_lookup.get(artist_key)

            if merged_artist is None:
                continue

            selected_related_artists.append(merged_artist)
            selected_related_keys.add(artist_key)
            selected_for_seed += 1

            if selected_for_seed == related_artists_per_seed:
                break

    print("\nRelated artists selected for track testing:")

    for related_artist in selected_related_artists:
        print(
            f"{related_artist['name']} - recommended by: "
            f"{', '.join(related_artist['recommended_by'])}"
        )

    related_track_candidates = []

    print("\nRelated artist tracks:")

    for related_artist in selected_related_artists:
        related_artist_name = related_artist["name"]
        lastfm_tracks = get_artist_top_tracks(
            related_artist_name,
            limit=tracks_per_related_artist,
        )

        for lastfm_track in lastfm_tracks:
            spotify_track = search_track(
                spotify,
                lastfm_track["name"],
                lastfm_track["artist_name"],
            )

            if spotify_track is None:
                print(
                    f"Not found on Spotify: "
                    f"{lastfm_track['name']} - "
                    f"{lastfm_track['artist_name']}"
                )
                continue

            candidate_track = spotify_track.copy()
            candidate_track["source"] = "similar_artist"
            candidate_track["source_artist"] = related_artist_name
            candidate_track["recommended_by"] = (
                related_artist["recommended_by"].copy()
            )
            candidate_track["artist_similarities"] = (
                related_artist["similarities"].copy()
            )
            candidate_track["lastfm_listeners"] = (
                lastfm_track["listeners"]
            )
            candidate_track["lastfm_playcount"] = (
                lastfm_track["playcount"]
            )

            related_track_candidates.append(candidate_track)

            print(
                f"{candidate_track['name']} - "
                f"{candidate_track['artist_name']} "
                f"({candidate_track['album_name']})"
            )

    print(
        f"\nVerified related track candidates: "
        f"{len(related_track_candidates)}"
    )

    candidate_tracks = (
        seed_track_candidates
        + related_track_candidates
    )

    print(f"\nTotal candidate tracks: {len(candidate_tracks)}")

    ranked_candidates = rank_candidates(candidate_tracks)

    print("\nRanked track candidates:")

    for position, track in enumerate(ranked_candidates, start=1):
        print(
            f"{position}. "
            f"{track['name']} - "
            f"{track['artist_name']} - "
            f"Score: {track['recommendation_score']:.3f} - "
            f"Source: {track['source']}"
        )

    final_tracks = build_playlist(
        ranked_candidates,
        target_size=50,
        max_tracks_per_artist=5,
    )

    print(f"\nFinal DeepCrate tracks ({len(final_tracks)}):")

    for position, track in enumerate(final_tracks, start=1):
        print(
            f"{position}. "
            f"{track['name']} - "
            f"{track['artist_name']} - "
            f"Score: {track['recommendation_score']:.3f}"
        )


if __name__ == "__main__":
    main()