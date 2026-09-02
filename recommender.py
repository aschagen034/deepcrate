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