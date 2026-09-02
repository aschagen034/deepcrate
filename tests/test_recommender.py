import pytest

from recommender import (
    calculate_tag_similarity,
    find_strongest_artist_pair,
    find_third_artist,
)


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


def test_find_strongest_artist_pair():
    artist_tags = {
        "Chris Lake": ["house", "tech house", "electronic"],
        "FISHER": ["house", "tech house", "electronic"],
        "Disclosure": ["house", "garage", "electronic"],
    }

    result = find_strongest_artist_pair(artist_tags)

    assert result == ("Chris Lake", "FISHER")


def test_strongest_pair_requires_two_artists():
    artist_tags = {
        "Traumer": ["minimal", "microhouse"],
    }

    with pytest.raises(ValueError, match="At least two artists"):
        find_strongest_artist_pair(artist_tags)


def test_find_third_artist_compatible_with_both_seeds():
    artist_tags = {
        "Chris Lake": ["house", "tech house", "electronic"],
        "FISHER": ["house", "tech house", "dance"],
        "Disclosure": ["house", "garage", "electronic"],
        "Cloonee": ["house", "tech house", "electronic", "dance"],
    }
    strongest_pair = ("Chris Lake", "FISHER")

    result = find_third_artist(artist_tags, strongest_pair)

    assert result == "Cloonee"


def test_find_third_artist_returns_none_without_shared_tags():
    artist_tags = {
        "Chris Lake": ["house", "tech house"],
        "FISHER": ["house", "electronic"],
        "Metallica": ["metal", "thrash metal"],
    }
    strongest_pair = ("Chris Lake", "FISHER")

    result = find_third_artist(artist_tags, strongest_pair)

    assert result is None