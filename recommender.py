def calculate_tag_similarity(
    artist_a_tags: list[str],
    artist_b_tags: list[str],
) -> float:
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

    all_tags = tags_a | tags_b

    if not all_tags:
        return 0.0

    shared_tags = tags_a & tags_b

    return len(shared_tags) / len(all_tags)


def find_strongest_artist_pair(
    artist_tags: dict[str, list[str]],
) -> tuple[str, str]:
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

        candidate_score = min(
            similarity_to_first,
            similarity_to_second,
        )

        if candidate_score > best_score:
            best_artist = artist_name
            best_score = candidate_score

    return best_artist