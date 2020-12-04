import aria2p
import os
import signal
import sys

import automateddl

aria2 = aria2p.API(
    aria2p.Client(
        host="http://10.0.2.106",
        port=6800,
        secret="Secret"
    )
)

autodl = automateddl.AutomatedDL(aria2, '/Download', '/Extract', '/Ended')

def signal_handler(sig, frame):
    autodl.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

autodl.start()
