def calculate_tag_similarity(
    artist_a_tags: list[str],
    artist_b_tags: list[str],
) -> float:
    """Return the Jaccard similarity between two artists' tag sets.
    
    Tags are normalized by trimming whitespace, converting to lowercase, 
    removing empty values, and collapsing duplicates.
    """
    tags_a = {
        tag.strip().lower()
        for tag in artist_a_tags
        if tag.strip()
    }
    tags_b = {
        tag.strip().lower()
        for tag in artist_b_tags
        if tag.strip()
    }

    # The union contains every unique tag used by either artist.
    all_tags = tags_a | tags_b

    if not all_tags:
        return 0.0

    # The intersection contains only tags shared by both artists.
    shared_tags = tags_a & tags_b

    # Jaccard similarity divides shared tags by all unique tags.
    return len(shared_tags) / len(all_tags)


def find_strongest_artist_pair(
    artist_tags: dict[str, list[str]],
) -> tuple[str, str]:
    """Return the pair of artists with the highest tag similarity

    Raises:
        ValueError: If fewer than two artists are provided.
    """
    artist_names = list(artist_tags)

    if len(artist_names) < 2:
        raise ValueError("At least two artists are required")

    best_pair = (artist_names[0], artist_names[1])
    best_score = calculate_tag_similarity(
        artist_tags[best_pair[0]],
        artist_tags[best_pair[1]],
    )

    for index, artist_a in enumerate(artist_names):
        for artist_b in artist_names[index + 1:]:
            score = calculate_tag_similarity(
                artist_tags[artist_a],
                artist_tags[artist_b],
            )

            if score > best_score:
                best_pair = (artist_a, artist_b)
                best_score = score

    return best_pair


def find_third_artist(
    artist_tags: dict[str, list[str]],
    strongest_pair: tuple[str, str],
) -> str | None:
    """Find the artist that is most compatible with both seed artists.

    Each candidate is scored using its weaker similarity to the two
    seeds, which prevents a strong match with only one seed from winning.
    """
    first_artist, second_artist = strongest_pair

    best_artist = None
    best_score = 0.0

    for artist_name, tags in artist_tags.items():
        if artist_name in strongest_pair:
            continue

        similarity_to_first = calculate_tag_similarity(
            tags,
            artist_tags[first_artist],
        )
        similarity_to_second = calculate_tag_similarity(
            tags,
            artist_tags[second_artist],
        )

        # Use the weaker of the two relationships so the third artist
        # must fit both members of the strongest pair.
        candidate_score = min(
            similarity_to_first,
            similarity_to_second,
        )

        if candidate_score > best_score:
            best_artist = artist_name
            best_score = candidate_score

    return best_artist


def merge_similar_artists(
    recommendations_by_seed: dict[str, list[dict]],
) -> list[dict]:
    """Merge similar-artist results from multiple seed artists.

    Artist names are matched case-insensitively. Seed artists are excluded,
    while every recommendation relationship and similarity score is preserved.
    """
    merged_artists = {}
    # Case-insensitive keys prevent differently capitalized artist names
    # from becoming separate recommendation candidates.
    seed_names = {
        seed_name.casefold()
        for seed_name in recommendations_by_seed
    }

    for seed_name, similar_artists in recommendations_by_seed.items():
        for artist in similar_artists:
            artist_name = artist["name"]
            artist_key = artist_name.casefold()

            # Seed artists are already represented directly and should
            # not also appear as related-artist candidates.
            if artist_key in seed_names:
                continue

            if artist_key not in merged_artists:
                merged_artists[artist_key] = {
                    "name": artist_name,
                    "recommended_by": [],
                    "similarities": {},
                }

            merged_artists[artist_key]["recommended_by"].append(seed_name)
            merged_artists[artist_key]["similarities"][seed_name] = (
                artist["similarity"]
            )

    return list(merged_artists.values())


def score_track_candidate(track: dict) -> float:
    """Return a recommendation score for a candidate track.

    Seed-artist tracks receive a base score of 1.0. Similar-artist
    tracks combine their similarity scores across all recommending
    seed artists.
    """
    if track.get("source") == "seed_artist":
        return 1.0

    if track.get("source") == "similar_artist":
        similarities = track.get("artist_similarities", {})
        # Multiple seed relationships strengthen a recommendation, so
        # their similarity contributions are combined.
        return sum(similarities.values())

    return 0.0


def rank_candidates(candidate_tracks: list[dict]) -> list[dict]:
    """Score candidate tracks and return them from strongest to weakest.

    Each track is copied before its recommendation score is added,
    leaving the caller's original dictionaries unchanged.
    """
    scored_tracks = []

    for track in candidate_tracks:
        # Copy each track so ranking does not mutate the original candidate data.
        scored_track = track.copy()
        scored_track["recommendation_score"] = (
            score_track_candidate(track)
        )
        scored_tracks.append(scored_track)

    return sorted(
        scored_tracks,
        key=lambda track: track["recommendation_score"],
        reverse=True,
    )