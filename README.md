# DeepCrate

DeepCrate is a Python music-discovery application that builds a personalized Spotify playlist focused on underground electronic and house music.

DeepCrate uses the listener's recent Spotify activity as a personalization signal, then filters seed and related artists using Last.fm tags
associated with several subgenres of house music and adjacent styles.

The result is a focused 30-track discovery playlist that prioritizes fresh tracks while retaining older recommendations as fallback candidates
when necessary.

When weekly scheduling is configured, the playlist updates automatically and changes alongside the listener's recent taste.

## Features

- Authenticates with the Spotify Web API
- Retrieves the current user’s recent top artists
- Fetches artist tags and similar artists from Last.fm
- Groups top artists using tag similarity
- Selects up to three related artists as recommendation seeds
- Discovers tracks from seed and related artists
- Ranks candidates by artist similarity
- Limits tracks per artist for better variety
- Interleaves artists instead of grouping their tracks together
- Adds controlled ranking variation between runs
- Tracks previously selected songs using Spotify track IDs
- Prioritizes tracks not used within the last 28 days
- Updates the same Spotify playlist instead of creating duplicates
- Supports interactive, unattended, and dry-run execution
- Writes persistent runtime logs
- Includes a PowerShell runner for Windows Task Scheduler
- Includes automated tests with pytest
- Retries temporary Spotify and Last.fm failures with exponential backoff
- Respects Spotify 'Retry-After' responses while avoiding retries that could create duplicate writes

## How It Works

DeepCrate follows this recommendation pipeline:

1. Retrieve the user’s 10 most-listened-to Spotify artists from the short-term listening range.
2. Retrieve Last.fm tags and calculate each artist’s affinity with the target underground house profile.
3. If fewer than two compatible artists are found, repeat the search using the medium-term and then long-term Spotify listening ranges.
4. Stop checking additional listening ranges once at least two compatible artists have been found.
5. Exclude unrelated top artists from seed selection.
6. Compare compatible artists using Jaccard tag similarity.
7. Select up to three genre-compatible top artists as recommendation seeds.
8. Retrieve similar artists for each seed from Last.fm.
9. Retrieve tags for a limited pool of related artists.
10. Exclude related artists that do not meet the minimum genre affinity.
11. Search Spotify for tracks from the accepted seed and related artists.
12. Score and rank candidate tracks using their recommendation relationships.
13. Add controlled variation to similarly ranked tracks.
14. Prioritize tracks that have not appeared within the 28-day cooldown.
15. Limit each artist to five final tracks.
16. Interleave artists throughout the playlist.
17. Create or update the `DeepCrate Weekly` Spotify playlist.
18. Save selected track IDs and timestamps to local history.

If there are not enough fresh tracks to create a 30-track playlist, DeepCrate uses the oldest recently selected tracks as fallback candidates.

## Requirements

- Python 3.12 or newer
- A Spotify account
- A Spotify developer application
- A Last.fm API key
- Windows PowerShell for the included scheduled-task runner

## Project Structure

```text
deepcrate/
├── main.py
├── spotify_client.py
├── lastfm_client.py
├── recommender.py
├── playlist_generator.py
├── history.py
├── logging_config.py
├── retry.py
├── run_deepcrate.ps1
├── requirements.txt
├── README.md
└── tests/
    ├── test_history.py
    ├── test_lastfm_client.py
    ├── test_logging_config.py
    ├── test_main.py
    ├── test_playlist_generator.py
    ├── test_recommender.py
    ├── test_retry.py
    └── test_spotify_client.py
```

Runtime files are created locally and excluded from Git:

```text
.deepcrate_history.json
logs/deepcrate.log
```

## Installation

Clone the repository and enter the project directory:

```powershell
git clone <repository-url>
cd deepcrate
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Confirm that the virtual environment is active:

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

The executable path should point to:

```text
deepcrate\.venv\Scripts\python.exe
```

## Spotify Setup

1. Create an application in the Spotify Developer Dashboard.
2. Add a redirect URI to the application.
3. Store the application credentials in a `.env` file in the project root.

Example:

```dotenv
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

The redirect URI in `.env` must exactly match one of the redirect URIs configured for the Spotify application.

DeepCrate requests these Spotify authorization scopes:

```text
user-read-private
user-top-read
playlist-read-private
playlist-modify-private
playlist-modify-public
```

On the first run, Spotify opens an authorization page in the browser. Spotipy then stores a local token cache and uses the refresh token for later unattended runs.

Never commit `.env`, Spotify credentials, or authentication tokens.

## Last.fm Setup

Create a Last.fm API account and add the API key to `.env`:

```dotenv
LASTFM_API_KEY=your_lastfm_api_key
```

The complete file should resemble:

```dotenv
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
LASTFM_API_KEY=your_lastfm_api_key
```

Some underground artists may not have Last.fm tags or similar-artist information. DeepCrate handles missing tags by excluding those artists from tag-based clustering.

## Running DeepCrate

### Interactive mode

```powershell
python main.py
```

DeepCrate generates and prints the proposed playlist, then asks:

```text
Create or update this playlist in Spotify? [y/N]:
```

Enter `y` to update Spotify and save the selected tracks to history.

### Dry-run mode

```powershell
python main.py --dry-run
```

Dry-run mode:

- Authenticates with Spotify
- Calls the Spotify and Last.fm read APIs
- Generates and prints the proposed playlist
- Displays fresh and recently used track counts
- Writes runtime information to the log
- Does not update the Spotify playlist
- Does not update track history

### Unattended mode

```powershell
python main.py --yes
```

This skips the confirmation prompt, updates Spotify, and records the selected tracks in history. It is intended for scheduled execution.

### Command help

```powershell
python main.py --help
```

## Playlist History

DeepCrate stores local selection history in:

```text
.deepcrate_history.json
```

The history maps Spotify track IDs to UTC timestamps:

```json
{
  "spotify-track-id": "2026-09-05T16:30:00+00:00"
}
```

Spotify IDs are used because track names are not guaranteed to be unique.

By default, tracks used during the previous 28 days are considered recent. DeepCrate prioritizes fresh candidates and only reintroduces recent tracks when needed to reach the target playlist size.

History is saved only after Spotify successfully creates or updates the playlist. Cancelling an interactive run or using `--dry-run` does not change it.

A malformed or missing history file is safely treated as empty history.

## Freshness Summary

Each run reports how many selected tracks are fresh and how many are recent fallbacks:

```text
Playlist freshness:
Fresh tracks selected: 18
Recently used fallback tracks: 12
```

The number of fresh tracks depends on the current recommendation pool. Similar listening history across multiple runs may produce more fallback tracks.

## Logging

DeepCrate writes logs to:

```text
logs/deepcrate.log
```

A successful run includes information such as:

```text
DeepCrate run started
Collected 90 candidate tracks
Selected 30 tracks: 18 fresh, 12 recent fallback
Updated Spotify playlist 'DeepCrate Weekly' with 30 tracks
DeepCrate run completed successfully
```

Unexpected exceptions are logged with their traceback, and the program exits with a nonzero status so Task Scheduler can recognize failures.

View recent log entries with:

```powershell
Get-Content logs\deepcrate.log -Tail 30
```

Temporary API failures and retry delays are written to the runtime log. If all retry attempts are exhausted, DeepCrate records the final error and exits with a nonzero status so Windows Task Scheduler can retry the complete run.

## API Retry Behavior

DeepCrate attempts temporary API operations up to three times.

- Last.fm requests use exponential backoff for network failures, rate limits, temporary server errors, and retryable Last.fm error codes.
- Spotify requests honor the `Retry-After` header for ordinary rate limits.
- Permanent request errors are not retried.
- Spotify quota exhaustion is left to Windows Task Scheduler to retry later.
- Playlist creation and track-appending operations avoid retries after ambiguous network or server failures, preventing duplicate playlists or tracks.
- Replacing a playlist's complete contents can be retried safely because repeating the operation produces the same final state.

If all attempts are exhausted, DeepCrate logs the final error and exits with a nonzero status.

## PowerShell Runner

The repository includes `run_deepcrate.ps1`.

Safe dry run:

```powershell
.\run_deepcrate.ps1 -DryRun
```

Live unattended update:

```powershell
.\run_deepcrate.ps1
```

The runner:

- Locates the project using `$PSScriptRoot`
- Uses `.venv\Scripts\python.exe` directly
- Runs from the correct working directory
- Uses `--dry-run` when requested
- Uses `--yes` during normal scheduled execution
- Returns a failure exit code if DeepCrate fails

Running the script without `-DryRun` updates the Spotify playlist.

## Weekly Windows Task

DeepCrate can be registered with Windows Task Scheduler to run automatically on a chosen day and time. The example configuration below schedules it for Friday at 12:00 AM.

From the project directory, run:

```powershell
$taskName = "DeepCrate Weekly"
$projectRoot = $PWD.Path
$runnerPath = Join-Path $projectRoot "run_deepcrate.ps1"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$actionArguments = (
    "-NoProfile -NonInteractive " +
    "-ExecutionPolicy Bypass " +
    "-File `"$runnerPath`""
)

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $actionArguments `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Friday `
    -At "12:00 AM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Description "Generate and update the DeepCrate Spotify playlist every Friday at midnight." `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal
```

Verify the task:

```powershell
Get-ScheduledTask -TaskName "DeepCrate Weekly"
Get-ScheduledTaskInfo -TaskName "DeepCrate Weekly"
```

A task state of `Ready` means Windows is waiting for the next trigger. After a scheduled run, a `LastTaskResult` of `0` indicates success.

The scheduled task currently runs under the interactive Windows account:

- The user must remain signed in.
- The computer may be locked.
- `WakeToRun` may wake the computer from sleep if supported.
- The task cannot run while the computer is shut down.
- `StartWhenAvailable` allows Windows to start a missed task later.

The Windows scheduled-task registration is system configuration and is not stored in Git. The reusable PowerShell runner is stored in the repository.

## Testing

Run the complete test suite through the active virtual environment:

```powershell
python -m pytest
```

Using `python -m pytest` ensures the correct virtual-environment interpreter is used. On some systems, running `pytest` directly may invoke a global or stale pytest installation.

Check files for whitespace errors before committing:

```powershell
git diff --check
```

## Recommendation Scoring

Seed-artist tracks receive a strong base score.

Tracks from similar artists receive scores based on their Last.fm similarity relationships with the seed artists. If an artist is recommended by multiple seeds, those similarity contributions may be combined. As a result, valid recommendation scores can be greater than `1.0`.

The displayed score remains the transparent recommendation score. Controlled variation changes selection order without overwriting the original score.

## Current Defaults

```text
Spotify listening ranges: short_term, medium_term, then long_term as needed
Minimum genre-compatible top artists: 2
Top Spotify artists per listening range: 10
Seed artists: up to 3
Target genre minimum affinity: 0.15
Last.fm recommendations per seed: 20
Related artists checked per seed: 10
Selected related artists per seed: 5
Candidate tracks per artist: 10
Final playlist size: 30
Maximum final tracks per artist: 5
Ranking variation: 15%
Recent-track cooldown: 28 days
Playlist name: DeepCrate Weekly
Schedule: Friday at 12:00 AM
```

These settings are currently defined in the Python source and can be moved into a configuration file or environment variables in a future milestone.

## Known Limitations

- Recommendation quality depends on Spotify and Last.fm metadata.
- Some underground artists do not have Last.fm tags.
- Spotify searches may return remasters, radio edits, alternate editions, or duplicate recordings.
- A completely fresh 30-track playlist is not guaranteed if the genre-compatible candidate pool is limited.
- Last.fm tags are user-generated, so some relevant underground artists may receive low affinity scores or be excluded.
- DeepCrate expects the listener to have at least two genre-compatible artists across their short-, medium-, or long-term Spotify listening history.
- Repeated runs with similar top artists may produce many recent fallback tracks.
- Prolonged Spotify or Last.fm outages, rate limits, or quota exhaustion may still prevent a run from completing after all retries are exhausted.
- The Windows scheduled task only runs while the configured user is signed in.

## Future Improvements

Potential future milestones include:

- Smarter duplicate detection for remasters, radio edits, and alternate releases
- Configurable playlist size, cooldown period, artist limits, and Spotify listening range
- Improved history retention and cleanup
- More flexible seed selection from larger groups of highly similar artists
- A web interface for playlist generation, configuration, and preview
- Cloud deployment so weekly playlist generation does not depend on a personal computer

## Disclaimer

DeepCrate is an independent project and is not affiliated with Spotify or Last.fm.