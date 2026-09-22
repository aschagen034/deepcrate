import argparse
import logging

from lastfm_client import (
    get_artist_tags,
    get_similar_artists,
)
from recommender import (
    calculate_target_genre_affinity,
    filter_artists_by_genre_affinity,
    filter_similar_artists_by_genre_affinity,
    find_strongest_artist_pair,
    find_third_artist,
    merge_similar_artists,
    rank_candidates,
)
from spotify_client import (
    add_tracks_to_playlist,
    authenticate,
    create_playlist,
    find_owned_playlist_by_name,
    get_current_user,
    get_top_artists,
    replace_playlist_tracks,
    search_artist_tracks,
)
from playlist_generator import (
    add_ranking_variety,
    build_playlist,
)
from history import (
    filter_recent_tracks,
    load_track_history,
    record_playlist_tracks,
    save_track_history,
    was_track_used_recently,
)

from logging_config import configure_logging

logger = logging.getLogger("deepcrate")

TOP_ARTIST_TIME_RANGES = (
    "short_term",
    "medium_term",
    "long_term",
)

TARGET_GENRE_TAGS = [
    "deep house",
    "minimal house",
    "microhouse",
    "rominimal",
    "tech house",
    "deep tech",
    "minimal",
    "house",
]

MINIMUM_SEED_ARTISTS = 2
MINIMUM_GENRE_AFFINITY = 0.15
RELATED_ARTIST_GENRE_POOL_PER_SEED = 10
PLAYLIST_SIZE = 30


def parse_args(
        arguments: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a DeepCrate Spotify playlist,",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Update Spotify without asking for confirmation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the track list without updating Spotify."
    )

    return parser.parse_args(arguments)

def main(
    auto_confirm: bool = False,
    dry_run: bool = False,
):
    print("DeepCrate starting...")
    logger.info("Deepcrate run started")

    spotify = authenticate()
    current_user = get_current_user(spotify)

    if current_user is None:
        raise RuntimeError("Spotify did not return a current user profile")

    print(f"Connected to Spotify as: {current_user['display_name']}")

    artist_tags = {}
    artist_time_ranges = {}
    seen_artist_keys = set()
    genre_artist_tags = {}

    for time_range in TOP_ARTIST_TIME_RANGES:
        top_artists = get_top_artists(
            spotify,
            limit=10,
            time_range=time_range,
        )

        print(f"\nTop artists ({time_range}):")

        for position, artist in enumerate(
            top_artists,
            start=1,
        ):
            print(f"{position}. {artist['name']}")

        print(
            f"\nNew artist Last.fm tag and genre analysis "
            f"({time_range}):"
        )

        for artist in top_artists:
            artist_name = artist["name"]
            artist_key = artist_name.casefold()

            if artist_key in seen_artist_keys:
                continue

            seen_artist_keys.add(artist_key)
            artist_time_ranges[artist_name] = time_range

            tags = get_artist_tags(artist_name)

            if not tags:
                print(
                    f"{artist_name}: "
                    f"no tags found"
                )
                continue

            artist_tags[artist_name] = tags

            affinity = calculate_target_genre_affinity(
                tags,
                TARGET_GENRE_TAGS,
            )

            print(
                f"{artist_name}: "
                f"{affinity:.2f} - "
                f"{', '.join(tags)}"
            )

        genre_artist_tags = (
            filter_artists_by_genre_affinity(
                artist_tags,
                TARGET_GENRE_TAGS,
                minimum_affinity=(
                    MINIMUM_GENRE_AFFINITY
                ),
            )
        )

        if (
            len(genre_artist_tags)
            >= MINIMUM_SEED_ARTISTS
        ):
            logger.info(
                "Found %d genre-compatible top artists "
                "after checking %s",
                len(genre_artist_tags),
                time_range,
            )
            break

    print("\nGenre-compatible top artists:")

    for artist_name in genre_artist_tags:
        print(
            f"{artist_name} "
            f"({artist_time_ranges[artist_name]})"
        )

    if len(genre_artist_tags) < MINIMUM_SEED_ARTISTS:
        logger.warning(
            "Only %d genre-compatible top artists were found",
            len(genre_artist_tags),
        )
        print(
            "\nNot enough genre-compatible top artists "
            "to create a seed cluster."
        )
        return

    strongest_pair = find_strongest_artist_pair(
        genre_artist_tags
    )
    third_artist = find_third_artist(
        genre_artist_tags,
        strongest_pair,
    )

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
            limit=20,
        )

    candidate_artists = merge_similar_artists(
        recommendations_by_seed,
    )

    candidate_keys_to_check = {
        related_artist["name"].casefold()
        for seed_artist in seed_artists
        for related_artist in (
            recommendations_by_seed[seed_artist][
                :RELATED_ARTIST_GENRE_POOL_PER_SEED
            ]
        )
    }

    candidate_artist_tags = {}

    print("\nRelated artist genre analysis:")

    for candidate in candidate_artists:
        artist_key = candidate["name"].casefold()

        if artist_key not in candidate_keys_to_check:
            continue

        tags = get_artist_tags(candidate["name"])
        candidate_artist_tags[candidate["name"]] = tags

        affinity = calculate_target_genre_affinity(
            tags,
            TARGET_GENRE_TAGS,
        )

        print(
            f"{candidate['name']}: "
            f"{affinity:.2f}"
        )

    candidate_artists = (
        filter_similar_artists_by_genre_affinity(
            candidate_artists,
            candidate_artist_tags,
            TARGET_GENRE_TAGS,
            minimum_affinity=MINIMUM_GENRE_AFFINITY,
        )
    )

    logger.info(
        "Selected %d genre-compatible related artists "
        "from %d checked candidates",
        len(candidate_artists),
        len(candidate_artist_tags),
    )

    print(
        f"\nGenre-compatible similar artist candidates "
        f"({len(candidate_artists)}):"
    )

    for candidate in candidate_artists:
        relationships = ", ".join(
            (
                f"{seed_name} "
                f"({candidate['similarities'][seed_name]:.2f})"
            )
            for seed_name in candidate["recommended_by"]
        )

        print(
            f"{candidate['name']} - "
            f"genre affinity: "
            f"{candidate['genre_affinity']:.2f} - "
            f"recommended by: {relationships}"
        )

    seed_track_candidates = []

    print("\nSeed artist tracks:")
    for seed_artist in seed_artists:
        spotify_tracks = search_artist_tracks(
            spotify,
            seed_artist,
            limit=10,
        )

        for spotify_track in spotify_tracks:
            candidate_track = spotify_track.copy()
            candidate_track["source"] = "seed_artist"
            candidate_track["source_artist"] = seed_artist

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

    related_artists_per_seed = 5
    tracks_per_related_artist = 10

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
        spotify_tracks = search_artist_tracks(
            spotify,
            related_artist_name,
            limit=tracks_per_related_artist,
        )

        for spotify_track in spotify_tracks:
            candidate_track = spotify_track.copy()
            candidate_track["source"] = "similar_artist"
            candidate_track["source_artist"] = related_artist_name
            candidate_track["genre_affinity"] = (
                related_artist["genre_affinity"]
            )
            candidate_track["recommended_by"] = (
                related_artist["recommended_by"].copy()
            )
            candidate_track["artist_similarities"] = (
                related_artist["similarities"].copy()
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

    logger.info(
        "Collected %d candidate tracks",
        len(candidate_tracks),
    )

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

    history_path = ".deepcrate_history.json"
    track_history = load_track_history(history_path)

    varied_candidates = add_ranking_variety(
        ranked_candidates,
        variation=0.15,
    )

    history_filtered_candidates = filter_recent_tracks(
        varied_candidates,
        track_history,
        cooldown_days=28,
        target_size=PLAYLIST_SIZE,
    )

    final_tracks = build_playlist(
        history_filtered_candidates,
        target_size=PLAYLIST_SIZE,
        max_tracks_per_artist=5,
    )

    reused_track_count = sum(
        was_track_used_recently(
            track["spotify_id"],
            track_history,
            cooldown_days=28,
        )
        for track in final_tracks
    )
    fresh_track_count = len(final_tracks) - reused_track_count

    print("\nPlaylist freshness:")
    print(f"Fresh tracks selected: {fresh_track_count}")
    print(f"Recently used fallback tracks: {reused_track_count}")

    logger.info(
        "Selected %d tracks: %d fresh, %d recent fallback",
        len(final_tracks),
        fresh_track_count,
        reused_track_count,
    )

    print(f"\nFinal DeepCrate tracks ({len(final_tracks)}):")

    for position, track in enumerate(final_tracks, start=1):
        print(
            f"{position}. "
            f"{track['name']} - "
            f"{track['artist_name']} - "
            f"Score: {track['recommendation_score']:.3f}"
        )

    if dry_run:
        print(
            "\nDry run complete. Spotify playlist and "
            "track history were not updated."
        )
        logger.info(
            "Dry run completed without updating Spotify or history"
        )
        return

    if not auto_confirm:
        confirmation = input(
            "\nCreate or update this playlist in Spotify? [y/N]: "
        ).strip().lower()

        if confirmation != "y":
            print("Playlist update cancelled.")
            logger.info("Playlist update cancelled by user")
            return

    playlist_name = "DeepCrate Weekly"

    track_uris = [
        track["spotify_uri"]
        for track in final_tracks
    ]

    existing_playlist = find_owned_playlist_by_name(
        spotify,
        user_id=current_user["id"],
        playlist_name=playlist_name,
    )

    if existing_playlist:
        replace_playlist_tracks(
            spotify,
            existing_playlist["spotify_id"],
            track_uris,
        )

        playlist = existing_playlist
        action = "Updated"
    else:
        playlist = create_playlist(
            spotify,
            name=playlist_name,
            description=(
                "A playlist generated from Spotify listening "
                "history and Last.fm recommendations."
            ),
        )

        add_tracks_to_playlist(
            spotify,
            playlist["spotify_id"],
            track_uris,
        )

        action = "Created"

    updated_history = record_playlist_tracks(
        track_history,
        final_tracks,
    )
    save_track_history(
        updated_history,
        history_path,
    )

    logger.info(
        "%s Spotify playlist '%s' with %d tracks",
        action,
        playlist_name,
        len(final_tracks),
    )
    logger.info("DeepCrate run completed successfully")

    print(
        f"\n{action} playlist: "
        f"{playlist['spotify_url']}"
    )


if __name__ == "__main__":
    configure_logging()
    args = parse_args()

    try:
        main(
            auto_confirm=args.yes,
            dry_run=args.dry_run,
        )
    except Exception:
        logger.exception("DeepCrate run failed")
        raise