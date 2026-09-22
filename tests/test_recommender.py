import pytest

from recommender import (
    calculate_tag_similarity,
    calculate_target_genre_affinity,
    filter_artists_by_genre_affinity,
    find_strongest_artist_pair,
    find_third_artist,
    merge_similar_artists,
    rank_candidates,
    score_track_candidate,
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


def test_merge_similar_artists_tracks_seed_relationships():
    recommendations_by_seed = {
        "PAWSA": [
            {"name": "Cloonee", "similarity": 1.0},
            {"name": "ANOTR", "similarity": 0.736},
            {"name": "Michael Bibi", "similarity": 0.868},
        ],
        "Michael Bibi": [
            {"name": "Cloonee", "similarity": 0.8},
            {"name": "ANOTR", "similarity": 0.9},
            {"name": "PAWSA", "similarity": 0.85},
        ],
    }

    result = merge_similar_artists(recommendations_by_seed)

    assert result == [
        {
            "name": "Cloonee",
            "recommended_by": ["PAWSA", "Michael Bibi"],
            "similarities": {
                "PAWSA": 1.0,
                "Michael Bibi": 0.8,
            },
        },
        {
            "name": "ANOTR",
            "recommended_by": ["PAWSA", "Michael Bibi"],
            "similarities": {
                "PAWSA": 0.736,
                "Michael Bibi": 0.9,
            },
        },
    ]


def test_merge_similar_artists_ignores_name_capitalization():
    recommendations_by_seed = {
        "PAWSA": [
            {"name": "FISHER", "similarity": 0.7},
        ],
        "ANOTR": [
            {"name": "Fisher", "similarity": 0.6},
        ],
    }

    result = merge_similar_artists(recommendations_by_seed)

    assert len(result) == 1
    assert result[0]["name"] == "FISHER"
    assert result[0]["recommended_by"] == ["PAWSA", "ANOTR"]


def test_seed_artist_track_score():
    track = {
        "source": "seed_artist",
    }

    result = score_track_candidate(track)

    assert result == 1.0


def test_similar_artist_track_score():
    track = {
        "source": "similar_artist",
        "artist_similarities": {
            "PAWSA": 0.8,
        },
    }

    result = score_track_candidate(track)

    assert result == 0.8


def test_multiple_seed_relationships_increase_track_score():
    track = {
        "source": "similar_artist",
        "artist_similarities": {
            "PAWSA": 0.7,
            "Michael Bibi": 0.6,
        },
    }

    result = score_track_candidate(track)

    assert result == pytest.approx(1.3)


def test_unknown_track_source_scores_zero():
    track = {
        "source": "unknown",
    }

    result = score_track_candidate(track)

    assert result == 0.0


def test_rank_candidates_highest_score_first():
    candidate_tracks = [
        {
            "name": "Single relationship",
            "source": "similar_artist",
            "artist_similarities": {
                "PAWSA": 0.6,
            },
        },
        {
            "name": "Seed track",
            "source": "seed_artist",
        },
        {
            "name": "Multiple relationships",
            "source": "similar_artist",
            "artist_similarities": {
                "PAWSA": 0.7,
                "Michael Bibi": 0.6,
            },
        },
    ]

    result = rank_candidates(candidate_tracks)

    assert [
        track["name"]
        for track in result
    ] == [
        "Multiple relationships",
        "Seed track",
        "Single relationship",
    ]

    assert result[0]["recommendation_score"] == pytest.approx(1.3)
    assert result[1]["recommendation_score"] == 1.0
    assert result[2]["recommendation_score"] == 0.6


def test_rank_candidates_does_not_change_original_tracks():
    candidate_tracks = [
        {
            "name": "Seed track",
            "source": "seed_artist",
        },
    ]

    rank_candidates(candidate_tracks)

    assert "recommendation_score" not in candidate_tracks[0]


def test_target_genre_affinity_full_match():
    artist_tags = [
        "deep house",
        "minimal house",
        "house",
    ]
    target_tags = [
        "deep house",
        "minimal house",
        "microhouse",
        "rominimal",
        "tech house",
        "house",
    ]

    result = calculate_target_genre_affinity(
        artist_tags,
        target_tags,
    )

    assert result == 1.0


def test_target_genre_affinity_partial_match():
    artist_tags = [
        "deep house",
        "house",
        "electronic",
        "uk",
    ]
    target_tags = [
        "deep house",
        "minimal house",
        "microhouse",
        "rominimal",
        "tech house",
        "house",
    ]

    result = calculate_target_genre_affinity(
        artist_tags,
        target_tags,
    )

    assert result == 0.5


def test_target_genre_affinity_no_match():
    result = calculate_target_genre_affinity(
        ["reggae", "dub", "ska"],
        ["deep house", "minimal house", "tech house"],
    )

    assert result == 0.0


def test_target_genre_affinity_normalizes_tags():
    result = calculate_target_genre_affinity(
        [
            " Deep House ",
            "HOUSE",
            "deep house",
        ],
        [
            "deep house",
            "house",
        ],
    )

    assert result == 1.0


def test_target_genre_affinity_empty_artist_tags():
    result = calculate_target_genre_affinity(
        [],
        ["deep house", "minimal house", "tech house"],
    )

    assert result == 0.0


def test_target_genre_affinity_empty_target_tags():
    result = calculate_target_genre_affinity(
        ["deep house", "house"],
        [],
    )

    assert result == 0.0


def test_filter_artists_by_genre_affinity():
    artist_tags = {
        "Janeret": [
            "deep house",
            "minimal house",
            "microhouse",
            "electronic",
        ],
        "Demuja": [
            "house",
            "deep house",
            "electronic",
            "austria",
        ],
        "The Beatles": [
            "rock",
            "classic rock",
            "british",
            "pop",
        ],
    }
    target_tags = [
        "deep house",
        "minimal house",
        "microhouse",
        "tech house",
        "house",
    ]

    result = filter_artists_by_genre_affinity(
        artist_tags,
        target_tags,
        minimum_affinity=0.15,
    )

    assert result == {
        "Janeret": [
            "deep house",
            "minimal house",
            "microhouse",
            "electronic",
        ],
        "Demuja": [
            "house",
            "deep house",
            "electronic",
            "austria",
        ],
    }


def test_filter_artists_includes_threshold_boundary():
    artist_tags = {
        "Test Artist": [
            "deep house",
            "electronic",
            "dance",
            "uk",
        ],
    }

    result = filter_artists_by_genre_affinity(
        artist_tags,
        ["deep house", "tech house"],
        minimum_affinity=0.25,
    )

    assert "Test Artist" in result


@pytest.mark.parametrize(
    "minimum_affinity",
    [-0.1, 1.1],
)
def test_filter_artists_rejects_invalid_affinity(
    minimum_affinity,
):
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        filter_artists_by_genre_affinity(
            {},
            ["deep house"],
            minimum_affinity=minimum_affinity,
        )