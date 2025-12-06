import logging
import os
import signal
import sys
import threading
from typing import Any

import aria2p

import automateddl

# Configure logging
# Allow overriding log level with environment variable `LOG_LEVEL`.
# Accepts level names like DEBUG, INFO, WARNING, ERROR, CRITICAL.
level_env = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger with format similar to loguru
logging.basicConfig(
    level=getattr(logging, level_env, logging.INFO),
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Log version
logger.info(f"AutomatedDL version: {automateddl.__version__}")

# Get Config from environment


server: str = os.getenv("SERVER", "http://127.0.0.1")
port: int = int(os.getenv("PORT", "6800"))
secret: str = os.getenv("SECRET", "")

downloaddir: str = os.getenv("DOWNLOADDIR", "/downloads")
extractdir: str = os.getenv("EXTRACTDIR", "/downloads/Extract")
endeddir: str = os.getenv("ENDEDDIR", "/downloads/Ended")

sonarr_url: str = os.getenv("SONARR_URL", "")
sonarr_api_key: str = os.getenv("SONARR_API_KEY", "")
radarr_url: str = os.getenv("RADARR_URL", "")
radarr_api_key: str = os.getenv("RADARR_API_KEY", "")

logger.info(f"Server: {server}")
logger.info(f"Port: {port}")
logger.info(f"Download directory: {downloaddir}")
logger.info(f"Extract directory: {extractdir}")
logger.info(f"Ended directory: {endeddir}")

if sonarr_url:
    logger.info(f"Sonarr URL: {sonarr_url}")
if radarr_url:
    logger.info(f"Radarr URL: {radarr_url}")

aria2: aria2p.API = aria2p.API(aria2p.Client(host=server, port=port, secret=secret))

autodl: automateddl.AutomatedDL = automateddl.AutomatedDL(
    aria2,
    downloaddir,
    extractdir,
    endeddir,
    sonarr_url=sonarr_url,
    sonarr_api_key=sonarr_api_key,
    radarr_url=radarr_url,
    radarr_api_key=radarr_api_key,
)

__stop_event: threading.Event = threading.Event()


def signal_handler(sig: int, frame: Any | None) -> None:
    logger.info(f"Quitting with signal: {sig}")
    autodl.stop()
    __stop_event.set()


signal.signal(signal.SIGINT, signal_handler)

__stop_event.clear()

autodl.start()
__stop_event.wait()
