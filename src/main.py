import aria2p
import os
import signal
import sys
import datetime
from typing import Optional, Any

import automateddl

# Get Config fom environnement

server: str = os.getenv("SERVER", "http://127.0.0.1")
port: str = os.getenv("PORT", "6800")
secret: str = os.getenv("SECRET", "")

downloaddir: str = os.getenv("DOWNLOADDIR", "/downloads")
extractdir: str = os.getenv("EXRACTDIR", "/downloads/Extract")
endeddir: str = os.getenv("ENDEDDIR", "/downloads/Ended")

print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " Server: " + server)
print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " Port: " + port)

print(
    datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f")
    + " downloaddir: "
    + downloaddir
)
print(
    datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f")
    + " extractdir: "
    + extractdir
)
print(
    datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " endeddir: " + endeddir
)

aria2: aria2p.API = aria2p.API(aria2p.Client(host=server, port=port, secret=secret))

autodl: automateddl.AutomatedDL = automateddl.AutomatedDL(
    aria2, downloaddir, extractdir, endeddir
)


def signal_handler(sig: int, frame: Optional[Any]) -> None:
    autodl.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

autodl.start()
