import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_track_history(
    history_path: str | Path,
) -> dict[str, datetime]:
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
    if cooldown_days < 0:
        raise ValueError("Cooldown days cannot be negative")

    if now is None:
        now = datetime.now(timezone.utc)

    cutoff = now - timedelta(days=cooldown_days)

    available_tracks = []
    recent_tracks = []

    for track in tracks:
        last_used = history.get(track["spotify_id"])

        if last_used is not None and last_used >= cutoff:
            recent_tracks.append((last_used, track))
        else:
            available_tracks.append(track)

    if len(available_tracks) >= target_size:
        return available_tracks

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
    path = Path(history_path)

    serialized_history = {
        track_id: used_at.astimezone(timezone.utc).isoformat()
        for track_id, used_at in history.items()
    }

    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp"
    )

    temporary_path.write_text(
        json.dumps(serialized_history, indent=2),
        encoding="utf-8",
    )

    temporary_path.replace(path)