from recommender import calculate_tag_similarity


def test_partial_tag_overlap():
    artist_a = ["minimal", "microhouse", "rominimal"]
    artist_b = ["minimal", "microhouse", "house"]

    result = calculate_tag_similarity(artist_a, artist_b)

    assert result == 0.5


def test_no_tag_overlap():
    artist_a = ["techno", "minimal"]
    artist_b = ["metal", "rock"]

    result = calculate_tag_similarity(artist_a, artist_b)

    assert result == 0.0


def test_identical_tags():
    artist_a = ["techno", "house"]
    artist_b = ["techno", "house"]

    result = calculate_tag_similarity(artist_a, artist_b)

    assert result == 1.0


def test_empty_tag_lists():
    result = calculate_tag_similarity([], [])

    assert result == 0.0


def test_tags_are_normalized():
    artist_a = [" Techno ", "HOUSE", "techno"]
    artist_b = ["techno", "house"]

    result = calculate_tag_similarity(artist_a, artist_b)

    assert result == 1.0