import aria2p
import os
import signal
import sys
import logging
from typing import Optional, Any

import automateddl

# Configure logging
# Allow overriding log level with environment variable `LOG_LEVEL`.
# Accepts level names like DEBUG, INFO, WARNING, ERROR, CRITICAL or
# numeric levels (e.g. 10, 20).
level_env = os.getenv("LOG_LEVEL", "INFO")
try:
    if str(level_env).isdigit():
        level = int(level_env)
    else:
        level = getattr(logging, str(level_env).upper(), None)
        if level is None:
            # Fallback to INFO if the provided name isn't valid
            level = logging.INFO
except Exception:
    level = logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y/%m/%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Get Config fom environnement

server: str = os.getenv("SERVER", "http://127.0.0.1")
port: str = os.getenv("PORT", "6800")
secret: str = os.getenv("SECRET", "")

downloaddir: str = os.getenv("DOWNLOADDIR", "/downloads")
extractdir: str = os.getenv("EXRACTDIR", "/downloads/Extract")
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


def signal_handler(sig: int, frame: Optional[Any]) -> None:
    autodl.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

autodl.start()
