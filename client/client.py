"""OPC UA клиент стенда БДЗ.

Циклически выполняет сценарий: GetEndpoints, подключение, Browse, Read,
Write, Call, подписка на Counter. Каждый запрос и ответ печатается в консоль.
"""

import asyncio
import logging
import os
import random
from datetime import datetime

from asyncua import Client, ua

URL = os.getenv("OPCUA_URL", "opc.tcp://opcua-server:4840/")
NS_URI = "urn:bdz:opcua:stand"
PAUSE = float(os.getenv("CYCLE_PAUSE", "5"))


def log(direction: str, msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction} {msg}", flush=True)


class SubHandler:
    def datachange_notification(self, node, val, _data) -> None:
        log("<-", f"Publish Counter = {val}")


async def cycle(n: int) -> None:
    log("**", f"--- cycle {n} ---")

    client = Client(URL, timeout=5)
    client.session_timeout = 600_000

    log("->", f"GetEndpoints {URL}")
    endpoints = await client.connect_and_get_server_endpoints()
    for ep in endpoints:
        log("<-", f"Endpoint {ep.EndpointUrl} mode={ep.SecurityMode.name.rstrip('_')} policy={ep.SecurityPolicyUri.split('#')[-1]}")

    log("->", "Hello / OpenSecureChannel / CreateSession / ActivateSession (Anonymous)")
    async with client:
        log("<-", "session active")
        idx = await client.get_namespace_index(NS_URI)

        device = await client.nodes.objects.get_child(f"{idx}:Device")
        log("->", "Browse Objects/Device")
        for child in await device.get_children():
            log("<-", f"  {(await child.read_browse_name()).Name} ({child.nodeid.to_string()})")

        counter = await device.get_child(f"{idx}:Counter")
        setpoint = await device.get_child(f"{idx}:Setpoint")
        enabled = await device.get_child(f"{idx}:Enabled")

        values = {}
        for name, node in (("Counter", counter), ("Setpoint", setpoint), ("Enabled", enabled)):
            log("->", f"Read  {name}")
            values[name] = await node.read_value()
            log("<-", f"Read  {name} = {values[name]}")

        new_sp = round(random.uniform(0, 100), 1)
        log("->", f"Write Setpoint := {new_sp}")
        await setpoint.write_value(ua.Variant(new_sp, ua.VariantType.Double))
        log("<-", "Write Setpoint Good")

        new_en = not values["Enabled"]
        log("->", f"Write Enabled := {new_en}")
        await enabled.write_value(ua.Variant(new_en, ua.VariantType.Boolean))
        log("<-", "Write Enabled Good")

        log("->", "Call  Device.Reset()")
        result = await device.call_method(f"{idx}:Reset")
        log("<-", f"Call  Reset -> {result}")

        log("->", "CreateSubscription + CreateMonitoredItems Counter")
        sub = await client.create_subscription(500, SubHandler())
        await sub.subscribe_data_change(counter)
        await asyncio.sleep(3)
        await sub.delete()

        log("->", "CloseSession / CloseSecureChannel")
    log("<-", "disconnected")


async def main() -> None:
    n = 1
    while True:
        try:
            await cycle(n)
        except Exception as exc:  # сервер ещё не поднялся или разорвал соединение
            log("!!", f"{type(exc).__name__}: {exc}")
        n += 1
        await asyncio.sleep(PAUSE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
