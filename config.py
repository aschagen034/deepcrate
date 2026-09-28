import json
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when DeepCrate configuration cannot be loaded."""


@dataclass(frozen=True)
class PlaylistConfig:
    name: str
    size: int
    max_tracks_per_artist: int


@dataclass(frozen=True)
class SpotifyConfig:
    top_artists_per_range: int
    listening_ranges: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveryConfig:
    minimum_seed_artists: int
    minimum_genre_affinity: float
    lastfm_recommendations_per_seed: int
    related_artist_genre_pool_per_seed: int
    related_artists_per_seed: int
    seed_tracks_per_artist: int
    related_tracks_per_artist: int
    ranking_variation: float


@dataclass(frozen=True)
class HistoryConfig:
    track_cooldown_days: int
    related_artist_cooldown_days: int


@dataclass(frozen=True)
class DeepCrateConfig:
    playlist: PlaylistConfig
    spotify: SpotifyConfig
    discovery: DiscoveryConfig
    history: HistoryConfig
    genre_weights: dict[str, float]


def _validate_config(config: DeepCrateConfig) -> None:
    if (
        not isinstance(config.playlist.name, str)
        or not config.playlist.name.strip()
    ):
        raise ConfigError(
            "playlist.name must be a nonempty string"
        )

    valid_listening_ranges = {
        "short_term",
        "medium_term",
        "long_term",
    }

    if (
        not config.spotify.listening_ranges
        or any(
            time_range not in valid_listening_ranges
            for time_range in config.spotify.listening_ranges
        )
    ):
        raise ConfigError(
            "spotify.listening_ranges contains an invalid range"
        )

    _validate_positive_integer(
        config.playlist.size,
        "playlist.size",
    )
    _validate_positive_integer(
        config.playlist.max_tracks_per_artist,
        "playlist.max_tracks_per_artist",
    )
    _validate_positive_integer(
        config.spotify.top_artists_per_range,
        "spotify.top_artists_per_range",
    )
    _validate_positive_integer(
        config.discovery.minimum_seed_artists,
        "discovery.minimum_seed_artists",
    )
    _validate_fraction(
        config.discovery.minimum_genre_affinity,
        "discovery.minimum_genre_affinity",
    )
    _validate_positive_integer(
        config.discovery.lastfm_recommendations_per_seed,
        "discovery.lastfm_recommendations_per_seed",
    )
    _validate_positive_integer(
        config.discovery.related_artist_genre_pool_per_seed,
        "discovery.related_artist_genre_pool_per_seed",
    )
    _validate_positive_integer(
        config.discovery.related_artists_per_seed,
        "discovery.related_artists_per_seed",
    )
    _validate_positive_integer(
        config.discovery.seed_tracks_per_artist,
        "discovery.seed_tracks_per_artist",
    )
    _validate_positive_integer(
        config.discovery.related_tracks_per_artist,
        "discovery.related_tracks_per_artist",
    )
    _validate_fraction(
        config.discovery.ranking_variation,
        "discovery.ranking_variation",
    )
    _validate_nonnegative_integer(
        config.history.track_cooldown_days,
        "history.track_cooldown_days",
    )
    _validate_nonnegative_integer(
        config.history.related_artist_cooldown_days,
        "history.related_artist_cooldown_days",
    )

    if not config.genre_weights:
        raise ConfigError(
            "genre_weights must contain at least one genre"
        )

    for genre, weight in config.genre_weights.items():
        if not genre.strip():
            raise ConfigError(
                "genre_weights contains an empty genre name"
            )

        _validate_positive_number(
            weight,
            f"genre_weights.{genre}",
        )


def _validate_positive_integer(
    value: object,
    setting_name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ConfigError(
            f"{setting_name} must be a positive integer"
        )


def _validate_nonnegative_integer(
    value: object,
    setting_name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ConfigError(
            f"{setting_name} must be a nonnegative integer"
        )


def _validate_fraction(
    value: object,
    setting_name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value < 0
        or value > 1
    ):
        raise ConfigError(
            f"{setting_name} must be between 0 and 1"
        )


def _validate_positive_number(
    value: object,
    setting_name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
    ):
        raise ConfigError(
            f"{setting_name} must be greater than zero"
        )


def load_config(
    config_path: str | Path,
) -> DeepCrateConfig:
    """Load DeepCrate settings from a JSON configuration file."""
    path = Path(config_path)

    try:
        config_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ConfigError(
            f"Configuration file not found: {path}"
        ) from error
    except OSError as error:
        raise ConfigError(
            f"Configuration file could not be read: {path}"
        ) from error

    try:
        data = json.loads(config_text)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Configuration file contains invalid JSON: {path}"
        ) from error

    try:
        config = DeepCrateConfig(
            playlist=PlaylistConfig(
                name=data["playlist"]["name"],
                size=data["playlist"]["size"],
                max_tracks_per_artist=(
                    data["playlist"]["max_tracks_per_artist"]
                ),
            ),
            spotify=SpotifyConfig(
                top_artists_per_range=(
                    data["spotify"]["top_artists_per_range"]
                ),
                listening_ranges=tuple(
                    data["spotify"]["listening_ranges"]
                ),
            ),
            discovery=DiscoveryConfig(
                minimum_seed_artists=(
                    data["discovery"]["minimum_seed_artists"]
                ),
                minimum_genre_affinity=(
                    data["discovery"]["minimum_genre_affinity"]
                ),
                lastfm_recommendations_per_seed=(
                    data["discovery"][
                        "lastfm_recommendations_per_seed"
                    ]
                ),
                related_artist_genre_pool_per_seed=(
                    data["discovery"][
                        "related_artist_genre_pool_per_seed"
                    ]
                ),
                related_artists_per_seed=(
                    data["discovery"]["related_artists_per_seed"]
                ),
                seed_tracks_per_artist=(
                    data["discovery"]["seed_tracks_per_artist"]
                ),
                related_tracks_per_artist=(
                    data["discovery"]["related_tracks_per_artist"]
                ),
                ranking_variation=(
                    data["discovery"]["ranking_variation"]
                ),
            ),
            history=HistoryConfig(
                track_cooldown_days=(
                    data["history"]["track_cooldown_days"]
                ),
                related_artist_cooldown_days=(
                    data["history"][
                        "related_artist_cooldown_days"
                    ]
                ),
            ),
            genre_weights={
                genre: weight
                for genre, weight in data["genre_weights"].items()
            },
        )
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ConfigError(
            "Configuration file has missing or invalid settings"
        ) from error

    _validate_config(config)

    return config