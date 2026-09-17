import random


def interleave_tracks_by_artist(
    tracks: list[dict],
) -> list[dict]:
    """Arrange tracks by taking one track per artist on each pass.
    
    Preserve each artist's track order and visit artists in first-seen
    order. Consecutive tracks from the same artist may remain when other artists run out.
    """
    tracks_by_artist = {}

    # Group tracks by artist while preserving their original order.
    for track in tracks:
        artist_id = track["artist_id"]

        if artist_id not in tracks_by_artist:
            tracks_by_artist[artist_id] = []

        tracks_by_artist[artist_id].append(track)

    interleaved_tracks = []

    # Take one track from each nonempty artist group until all groups are empty.
    while any(tracks_by_artist.values()):
        for artist_tracks in tracks_by_artist.values():
            if artist_tracks:
                interleaved_tracks.append(
                    artist_tracks.pop(0)
                )

    return interleaved_tracks


def add_ranking_variety(
    ranked_tracks: list[dict],
    variation: float = 0.15,
    rng: random.Random | None = None,
) -> list[dict]:
    """Reorder tracks using randomly adjusted recommendation scores.
    
    Variation must be between 0 and 1. Pass a seeded random generator for reproductible results.
    Original track dictionaries and scores are unchanged.
    """
    if variation < 0 or variation > 1:
        raise ValueError("Variation must be between 0 and 1")

    if rng is None:
        rng = random.Random()

    varied_tracks = []

    for track in ranked_tracks:
        # Scale each score randomly; the default variation allows a 15% adjustment.
        varied_score = (
            track["recommendation_score"]
            * rng.uniform(1 - variation, 1 + variation)
        )

        varied_tracks.append(
            (varied_score, track)
        )

    # Rank by the temporary scores without changing the stored recommendation scores.
    varied_tracks.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        track
        for _, track in varied_tracks
    ]


def build_playlist(
    ranked_tracks: list[dict],
    target_size: int = 50,
    max_tracks_per_artist: int = 5,
) -> list[dict]:
    """Select unique tracks in input order, enforce an artist cap, and interleave them.
    
    Aim for target_size tracks, returning fewer if not enough eligible tracks exist.
    Duplicate identified by Spotify track ID.
    """
    selected_tracks = []
    seen_track_ids = set()
    artist_track_counts = {}

    # Give earlier tracks priority when filling the playlist.
    for track in ranked_tracks:
        if len(selected_tracks) == target_size:
            break
        track_id = track["spotify_id"]
        artist_id = track["artist_id"]

        # Skip tracks already selected, even if they appear again in the ranking.
        if track_id in seen_track_ids:
            continue
        artist_count = artist_track_counts.get(artist_id, 0)

        # Limit how many selected tracks come from any one artist.
        if artist_count >= max_tracks_per_artist:
            continue

        selected_tracks.append(track)
        seen_track_ids.add(track_id)
        artist_track_counts[artist_id] = artist_count + 1

    # Spread each artist's selected tracks across the playlist.
    return interleave_tracks_by_artist(selected_tracks)