# automated-dl

Aria2 companion that automatically processes completed downloads:

- Extracts archives (zip/rar)
- Moves files to structured output folders
- Cleans up original parts
- Optionally triggers Sonarr/Radarr library scans for media files

Powered by `aria2p`, `patool`, and `httpx`.

## Features

- Listens to Aria2 download-complete events via RPC/WebSocket
- Handles single and multi-part archives (`.zip`, `.rar`, `*.partN.rar`)
- Moves extracted/output files to a final directory
- Deletes original parts after successful processing
- Detects media files (episodes vs movies) and triggers:
  - Sonarr: `DownloadedEpisodesScan`
  - Radarr: `DownloadedMoviesScan`
- Safe concurrent processing using a per-title lock

## Requirements

- Python 3.9+
- Aria2 running with RPC enabled
- System binaries for archive extraction (for rar support, `unrar` should be installed)

Python dependencies (installed automatically):

- `aria2p`
- `patool`
- `httpx`

## Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/PoppyPop/automated-dl.git
cd automated-dl
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install .
```

## Quickstart

Run the service pointing at your Aria2 RPC server. The service listens for completed downloads and processes them.

```bash
export SERVER=http://127.0.0.1
export PORT=6800
export SECRET=""              # aria2 rpc-secret if configured

export DOWNLOADDIR=/downloads
export EXTRACTDIR=/downloads/Extract
export ENDEDDIR=/downloads/Ended

# Optional Sonarr/Radarr integration
export SONARR_URL="http://localhost:8989"
export SONARR_API_KEY="<sonarr_api_key>"
export RADARR_URL="http://localhost:7878"
export RADARR_API_KEY="<radarr_api_key>"

python -m src.main
```

Logging level can be controlled via `LOG_LEVEL` (e.g. `DEBUG`, `INFO`).

## Configuration (env vars)

- `SERVER`: Aria2 RPC host (default `http://127.0.0.1`)
- `PORT`: Aria2 RPC port (default `6800`)
- `SECRET`: Aria2 RPC secret if enabled
- `DOWNLOADDIR`: Directory where Aria2 writes files (default `/downloads`)
- `EXTRACTDIR`: Temporary extraction directory (default `/downloads/Extract`)
- `ENDEDDIR`: Final destination directory (default `/downloads/Ended`)
- `SONARR_URL`, `SONARR_API_KEY`: Enable Sonarr scan trigger when episodes are detected
- `RADARR_URL`, `RADARR_API_KEY`: Enable Radarr scan trigger when movies are detected
- `LOG_LEVEL`: Python logging level (default `INFO`)

## How It Works

The core class `AutomatedDL` subscribes to Aria2 notifications. On each completed download it:

1. Identifies file type (nfo, archive, or other)
2. For `.nfo`: removes the download entry
3. For `.zip`/`.rar` or multi-part rar: extracts to `EXTRACTDIR`, moves the result to `ENDEDDIR`, and cleans parts
4. For other files: moves to `ENDEDDIR` and removes from Aria2
5. If the final file is a media file, triggers Sonarr or Radarr accordingly

See `src/automateddl/automateddl.py` for the full logic.

### Destination Layout

Within your `ENDEDDIR`, automated-dl categorizes processed items:

- `series/`: TV episodes (filenames matching patterns like `S01E01`, `1x01`, etc.)
- `movies/`: Movie files (media files that are not detected as episodes)
- `others/`: Non-media files and extracted archive folders

Archives are categorized by inspecting their extracted contents. If any extracted file is a media file with an episode pattern, the folder goes to `series/`; otherwise, if media files are present it goes to `movies/`; if no media is found it goes to `others/`.

## Docker

This repository includes a `Dockerfile` and VS Code tasks to build and run. To build locally:

```bash
docker build -t automateddl:latest .
```

Prebuilt image on Docker Hub:

```bash
docker pull poppypop/automated-dl
```

Docker Hub: https://hub.docker.com/r/poppypop/automated-dl

Prebuilt image on GitHub Container Registry (GHCR):

```bash
docker pull ghcr.io/poppypop/automated-dl:latest
```

GHCR: https://ghcr.io/poppypop/automated-dl

Run with required env vars and volume mounts so the container can access your download folders and Aria2 RPC:

```bash
docker run --rm \
	-e SERVER=http://host.docker.internal \
	-e PORT=6800 \
	-e DOWNLOADDIR=/downloads \
	-e EXTRACTDIR=/downloads/Extract \
	-e ENDEDDIR=/downloads/Ended \
	-e SONARR_URL=... -e SONARR_API_KEY=... \
	-e RADARR_URL=... -e RADARR_API_KEY=... \
	-v /path/to/downloads:/downloads \
	poppypop/automated-dl
	# or use GHCR image:
	# ghcr.io/poppypop/automated-dl:latest
```

## Development

Install dev dependencies and run tests:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if present

# Run tests
pytest -v

# Or via Makefile
make test
```

Pre-commit is configured for formatting and linting:

```bash
pre-commit run -a
```

### Test Suite

The test suite mixes one integration test (with a real Aria2 instance) and fast unit tests using mocks. This keeps end-to-end coverage while maintaining speed.

- Integration: `test_nfo_dl` spins up Aria2 and validates `.nfo` handling
- Mocked: zip/rar/multi-part extraction and Sonarr/Radarr triggers are validated using an in-memory mock of the Aria2 API

To run only the AutomatedDL tests:

```bash
pytest tests/test_automateddl.py -v
```

To run media detection and API trigger tests:

```bash
pytest tests/test_media_detection.py -v
```

## CI

GitHub Actions runs pre-commit checks and the test suite on pull requests. Merges are configured to enforce rebase-and-merge.

## License

GPL-3.0-or-later. See `LICENSE`.
