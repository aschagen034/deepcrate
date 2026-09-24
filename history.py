import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_track_history(
    history_path: str | Path,
) -> dict[str, datetime]:
    """Load track usage timestamps from a JSON file and convert them to UTC.
    
    Return an empty dictionary for a missing, unreadable, or invalid JSON file.
    Skip invalid entries and timestamps without timezone information.
    """
    path = Path(history_path)

    if not path.exists():
        return {}

    try:
        saved_history = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(saved_history, dict):
        return {}

    history = {}

    for track_id, timestamp in saved_history.items():
        if not isinstance(track_id, str):
            continue

        if not isinstance(timestamp, str):
            continue

        try:
            used_at = datetime.fromisoformat(timestamp)
        except ValueError:
            continue

        # Ignore timestamps whose timezone cannot be determined reliably.
        if used_at.tzinfo is None:
            continue

        history[track_id] = used_at.astimezone(timezone.utc)

    return history


def filter_recent_tracks(
    tracks: list[dict],
    history: dict[str, datetime],
    cooldown_days: int = 28,
    target_size: int = 50,
    now: datetime | None = None,
) -> list[dict]:
    """Prefer tracks outside the cooldown period, preserving their input order.
    
    If fewer than target_size tracks qualify, append all recent tracks,
    ordered from least recently used to most recently used.
    The returned list is not trucnated to target_size.
    """
    if cooldown_days < 0:
        raise ValueError("Cooldown days cannot be negative")

    if now is None:
        now = datetime.now(timezone.utc)


    available_tracks = []
    recent_tracks = []

    for track in tracks:
        last_used = history.get(track["spotify_id"])

        if was_track_used_recently(
            track["spotify_id"],
            history,
            cooldown_days=cooldown_days,
            now=now,
        ):
            recent_tracks.append((last_used, track))
        else:
            available_tracks.append(track)

    if len(available_tracks) >= target_size:
        return available_tracks

    # Reintroduce the least recently used tracks first when more candidates are needed.
    recent_tracks.sort(
        key=lambda item: item[0],
    )

    return available_tracks + [
        track
        for _, track in recent_tracks
    ]


def record_playlist_tracks(
    history: dict[str, datetime],
    tracks: list[dict],
    used_at: datetime | None = None,
) -> dict[str, datetime]:
    """Return a copy of the history with the supplied tracks marked as used.
    
    Store timestamps in UTC and leave the original history unchanged.
    Use the current time when used_at is omitted.
    """
    if used_at is None:
        used_at = datetime.now(timezone.utc)

    if used_at.tzinfo is None:
        raise ValueError("History timestamp must include a timezone")

    updated_history = history.copy()
    utc_used_at = used_at.astimezone(timezone.utc)

    for track in tracks:
        updated_history[track["spotify_id"]] = utc_used_at

    return updated_history


def save_track_history(
    history: dict[str, datetime],
    history_path: str | Path,
) -> None:
    """Save track history as JSON containing ISO-formatted UTC timestamps.
    
    Write to a temporary file before replacing the destination.
    """
    path = Path(history_path)

    serialized_history = {
        track_id: used_at.astimezone(timezone.utc).isoformat()
        for track_id, used_at in history.items()
    }

    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp"
    )

    # Finish writing the new history before replacing the existing file.
    temporary_path.write_text(
        json.dumps(serialized_history, indent=2),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def was_track_used_recently(
    track_id: str,
    history: dict[str, datetime],
    cooldown_days: int = 28,
    now: datetime | None = None,
) -> bool:
    if cooldown_days < 0:
        raise ValueError("Cooldown days cannot be negative")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("Current timestamp must include a timezone")

    last_used = history.get(track_id)

    if last_used is None:
        return False

    cutoff = now - timedelta(days=cooldown_days)

    # A timestamp exactly at the cutoff still counts as recent.
    return last_used >= cutoff


def was_related_artist_used_recently(
    artist_name: str,
    history: dict[str, datetime],
    cooldown_days: int = 42,
    now: datetime | None = None,
) -> bool:
    """Return whether an artist was used within the cooldown period."""
    if cooldown_days < 0:
        raise ValueError("Cooldown days cannot be negative")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("Current timestamp must include a timezone")

    artist_key = artist_name.strip().casefold()
    last_used = history.get(artist_key)

    if last_used is None:
        return False

    cutoff = now - timedelta(days=cooldown_days)

    return last_used >= cutoff


def prioritize_related_artists_by_history(
        artists: list[dict],
        history: dict[str, datetime],
        cooldown_days: int = 42,
        now: datetime | None = None,
) -> list[dict]:
    """Place fresh artists before recent artists.

    Preserve the input order of fresh artists. Order recent fallback artists
    from least recently used to most recently used.
    """
    if cooldown_days < 0:
        raise ValueError("Cooldown days cannot be negative")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("Current timestamp must include a timezone")

    fresh_artists = []
    recent_artists = []

    for artist in artists:
        artist_key = artist["name"].strip().casefold()
        last_used = history.get(artist_key)

        if was_related_artist_used_recently(
            artist["name"],
            history,
            cooldown_days=cooldown_days,
            now=now,
        ):
            recent_artists.append((last_used, artist))
        else:
            fresh_artists.append(artist)

    recent_artists.sort(
        key=lambda item: item[0],
    )

    return fresh_artists + [
        artist
        for _, artist in recent_artists
    ]


def record_related_artists(
        history: dict[str, datetime],
        artists: list[dict],
        used_at: datetime | None = None,
) -> dict[str, datetime]:
    """Return updated history with selected related artists marked as used."""
    if used_at is None:
        used_at = datetime.now(timezone.utc)

    if used_at.tzinfo is None:
        raise ValueError("History timestamp must include a timezone")

    updated_history = history.copy()
    utc_used_at = used_at.astimezone(timezone.utc)

    for artist in artists:
        artist_key = artist["name"].strip().casefold()

        if artist_key:
            updated_history[artist_key] = utc_used_at

    return updated_history


def load_artist_history(
    history_path: str | Path
) -> dict[str, datetime]:
    """Load normalized artist usage timestamps from a JSON file."""
    return load_track_history(history_path)


def save_artist_history(
    history: dict[str, datetime],
    history_path: str | Path,
) -> None:
    """Save normalized artist usage timestamps as JSON."""
    save_track_history(history, history_path)