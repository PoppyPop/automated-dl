import aria2p
import os
import signal
import sys

import automateddl

# Get Config fom environnement

server = os.getenv('SERVER', 'http://aria2-pro')
port = os.getenv('PORT', '6800')
secret = os.getenv('SECRET', '')

downloaddir = os.getenv('DOWNLOADDIR', '/downloads')
extractdir = os.getenv('EXRACTDIR', '/downloads/Extract')
endeddir = os.getenv('ENDEDDIR', '/downloads/Ended')

aria2 = aria2p.API(
    aria2p.Client(
        host=server,
        port=port,
        secret=secret
    )
)

autodl = automateddl.AutomatedDL(aria2, downloaddir, extractdir, endeddir)

def signal_handler(sig, frame):
    autodl.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

autodl.start()
