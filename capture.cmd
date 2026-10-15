@echo off
rem Live capture of OPC UA traffic from the stand into Wireshark (Windows).
rem Run from cmd.exe after "docker compose up" (PowerShell 5 corrupts binary pipes).
set WIRESHARK=%ProgramFiles%\Wireshark\Wireshark.exe
docker run --rm --net container:opcua-server nicolaka/netshoot tcpdump -U -n -i eth0 -w - "tcp port 4840" | "%WIRESHARK%" -k -i -
