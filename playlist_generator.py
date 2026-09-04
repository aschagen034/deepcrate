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

    return selected_tracks