import json
from pathlib import Path

import pytest

from config import ConfigError, load_config


def make_config_data() -> dict:
    return {
        "playlist": {
            "name": "Test Playlist",
            "size": 30,
            "max_tracks_per_artist": 5,
        },
        "spotify": {
            "top_artists_per_range": 10,
            "listening_ranges": [
                "short_term",
                "medium_term",
                "long_term",
            ],
        },
        "discovery": {
            "minimum_seed_artists": 2,
            "minimum_genre_affinity": 0.15,
            "lastfm_recommendations_per_seed": 20,
            "related_artist_genre_pool_per_seed": 10,
            "related_artists_per_seed": 5,
            "seed_tracks_per_artist": 10,
            "related_tracks_per_artist": 10,
            "ranking_variation": 0.15,
        },
        "history": {
            "track_cooldown_days": 28,
            "related_artist_cooldown_days": 42,
        },
        "genre_weights": {
            "house": 0.5,
            "microhouse": 2.0,
        },
    }


def test_load_config_returns_structured_settings(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(make_config_data()),
        encoding="utf-8",
    )

    result = load_config(config_path)

    assert result.playlist.name == "Test Playlist"
    assert result.playlist.size == 30
    assert result.spotify.listening_ranges == (
        "short_term",
        "medium_term",
        "long_term",
    )
    assert result.discovery.minimum_genre_affinity == 0.15
    assert result.history.related_artist_cooldown_days == 42
    assert result.genre_weights == {
        "house": 0.5,
        "microhouse": 2.0,
    }


def test_load_config_rejects_missing_file(tmp_path):
    config_path = tmp_path / "missing.json"

    with pytest.raises(
        ConfigError,
        match="Configuration file not found",
    ):
        load_config(config_path)


def test_load_config_rejects_malformed_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        "not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match="Configuration file contains invalid JSON",
    ):
        load_config(config_path)


@pytest.mark.parametrize(
    ("section", "setting", "invalid_value"),
    [
        ("playlist", "size", 0),
        ("playlist", "max_tracks_per_artist", -1),
        ("discovery", "minimum_genre_affinity", 1.1),
        ("discovery", "ranking_variation", -0.1),
        ("history", "track_cooldown_days", -1),
    ],
)
def test_load_config_rejects_invalid_setting(
    tmp_path,
    section,
    setting,
    invalid_value,
):
    config_data = make_config_data()
    config_data[section][setting] = invalid_value

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match=f"{section}.{setting}",
    ):
        load_config(config_path)


def test_load_config_rejects_nonpositive_genre_weight(tmp_path):
    config_data = make_config_data()
    config_data["genre_weights"]["house"] = 0

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match="genre_weights.house",
    ):
        load_config(config_path)


def test_load_config_rejects_empty_playlist_name(tmp_path):
    config_data = make_config_data()
    config_data["playlist"]["name"] = "   "

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match="playlist.name",
    ):
        load_config(config_path)


def test_load_config_rejects_invalid_listening_range(tmp_path):
    config_data = make_config_data()
    config_data["spotify"]["listening_ranges"] = [
        "short_term",
        "weekly",
    ]

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match="spotify.listening_ranges",
    ):
        load_config(config_path)


def test_load_config_rejects_missing_setting(tmp_path):
    config_data = make_config_data()
    del config_data["playlist"]["size"]

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match="missing or invalid settings",
    ):
        load_config(config_path)


def test_project_config_file_is_valid():
    config_path = (
        Path(__file__).resolve().parents[1]
        / "config.json"
    )

    result = load_config(config_path)

    assert result.playlist.name == "DeepCrate Weekly"
    assert result.playlist.size == 50
    assert result.history.track_cooldown_days == 28
    assert result.history.related_artist_cooldown_days == 42