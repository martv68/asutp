#!/bin/sh
# Захват трафика OPC UA из сети стенда в Wireshark в реальном времени (macOS/Linux).
# Запускать после docker compose up.
WIRESHARK="${WIRESHARK:-$(command -v wireshark || echo /Applications/Wireshark.app/Contents/MacOS/Wireshark)}"
docker run --rm --net container:opcua-server nicolaka/netshoot \
  tcpdump -U -n -i eth0 -w - 'tcp port 4840' | "$WIRESHARK" -k -i -
