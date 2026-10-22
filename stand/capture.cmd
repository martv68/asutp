@echo off
set WIRESHARK=%ProgramFiles%\Wireshark\Wireshark.exe
docker run --rm --net container:opcua-server nicolaka/netshoot tcpdump -U -n -i eth0 -w - "tcp port 4840" | "%WIRESHARK%" -k -i -
