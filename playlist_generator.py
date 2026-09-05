import random


def interleave_tracks_by_artist(
    tracks: list[dict],
) -> list[dict]:
    tracks_by_artist = {}

    for track in tracks:
        artist_id = track["artist_id"]

        if artist_id not in tracks_by_artist:
            tracks_by_artist[artist_id] = []

        tracks_by_artist[artist_id].append(track)

    interleaved_tracks = []

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
    if variation < 0 or variation > 1:
        raise ValueError("Variation must be between 0 and 1")

    if rng is None:
        rng = random.Random()

    varied_tracks = []

    for track in ranked_tracks:
        varied_score = (
            track["recommendation_score"]
            * rng.uniform(1 - variation, 1 + variation)
        )

        varied_tracks.append(
            (varied_score, track)
        )

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
    selected_tracks = []
    seen_track_ids = set()
    artist_track_counts = {}

    for track in ranked_tracks:
        if len(selected_tracks) == target_size:
            break
        track_id = track["spotify_id"]
        artist_id = track["artist_id"]

        if track_id in seen_track_ids:
            continue
        artist_count = artist_track_counts.get(artist_id, 0)

        if artist_count >= max_tracks_per_artist:
            continue

        selected_tracks.append(track)
        seen_track_ids.add(track_id)
        artist_track_counts[artist_id] = artist_count + 1

    return interleave_tracks_by_artist(selected_tracks)