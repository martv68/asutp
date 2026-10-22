import argparse
import asyncio
import inspect
import logging
import os
import random
import shlex
import sys
import threading
from datetime import datetime

from asyncua import Client, ua

try:
    import readline

    line_buffer = readline.get_line_buffer
except ImportError:
    def line_buffer() -> str:
        return ""

URL = os.getenv("OPCUA_URL", "opc.tcp://opcua-server:4840/")
NS_URI = "urn:bdz:opcua:stand"
PAUSE = float(os.getenv("CYCLE_PAUSE", "5"))
WATCHDOG = 60
PROMPT = "opcua> "

HELP = """\
Команды:
  connect                  Hello / OpenSecureChannel / CreateSession / ActivateSession
  disconnect               CloseSession / CloseSecureChannel
  endpoints                GetEndpoints (в отдельном защищённом канале)
  browse [узел]            Browse, по умолчанию Device
  read <узел>              Read атрибута Value
  write <узел> <значение>  Write, тип значения берётся из DataType узла
  call <метод>             Call метода объекта Device
  sub <узел>               CreateSubscription (при первой) + CreateMonitoredItems
  unsub [узел]             DeleteMonitoredItems; без аргумента — DeleteSubscriptions
  help, quit               (quit или Ctrl+D закрывают сеанс)
Узел: Counter, Setpoint, Enabled, Reset, Device, Objects, Server или NodeId (ns=2;s=Counter, i=2258)."""

INT_TYPES = {
    ua.VariantType.SByte, ua.VariantType.Byte, ua.VariantType.Int16, ua.VariantType.UInt16,
    ua.VariantType.Int32, ua.VariantType.UInt32, ua.VariantType.Int64, ua.VariantType.UInt64,
}


def log(direction: str, msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction} {msg}", flush=True)


async def get_endpoints() -> None:
    log("->", f"GetEndpoints {URL}")
    for ep in await Client(URL, timeout=5).connect_and_get_server_endpoints():
        log("<-", f"Endpoint {ep.EndpointUrl} mode={ep.SecurityMode.name.rstrip('_')} policy={ep.SecurityPolicyUri.split('#')[-1]}")


def parse_value(text: str, vtype: ua.VariantType):
    if vtype == ua.VariantType.Boolean:
        if text.lower() in ("1", "true", "on"):
            return True
        if text.lower() in ("0", "false", "off"):
            return False
        raise ValueError(f"ожидается true/false: {text}")
    if vtype in (ua.VariantType.Float, ua.VariantType.Double):
        return float(text)
    if vtype in INT_TYPES:
        return int(text)
    if vtype == ua.VariantType.String:
        return text
    raise ValueError(f"запись типа {vtype.name} не поддерживается")


async def ainput(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def resolve(value, exc) -> None:
        if not fut.done():
            fut.set_exception(exc) if exc else fut.set_result(value)

    def worker() -> None:
        try:
            value, exc = input(prompt), None
        except Exception as e:
            value, exc = None, e
        try:
            loop.call_soon_threadsafe(resolve, value, exc)
        except RuntimeError:
            pass

    threading.Thread(target=worker, daemon=True).start()
    return await fut


class Console:
    def __init__(self) -> None:
        self.client: Client | None = None
        self.nodes = {}
        self.names: dict[ua.NodeId, str] = {}
        self.types: dict[ua.NodeId, ua.VariantType] = {}
        self.sub = None
        self.handles: dict[ua.NodeId, int] = {}
        self.prompting = False

    def session(self) -> Client:
        if self.client is None:
            raise RuntimeError("нет сеанса, сначала connect")
        return self.client

    def node(self, ref: str):
        client = self.session()
        if ref in self.nodes:
            return self.nodes[ref]
        if "=" in ref:
            return client.get_node(ref)
        raise ValueError(f"неизвестный узел {ref}")

    def label(self, node) -> str:
        return self.names.get(node.nodeid, node.nodeid.to_string())

    def datachange_notification(self, node, val, _data) -> None:
        if self.prompting:
            sys.stdout.write("\r\033[K")
        log("<-", f"Publish {self.label(node)} = {val}")
        if self.prompting:
            sys.stdout.write(PROMPT + line_buffer())
            sys.stdout.flush()

    async def do_connect(self) -> None:
        if self.client is not None:
            raise RuntimeError("сеанс уже открыт")
        client = Client(URL, timeout=5, watchdog_intervall=WATCHDOG)
        log("->", f"Hello / OpenSecureChannel / CreateSession / ActivateSession (Anonymous) {URL}")
        await client.connect()
        self.client = client
        log("<-", "session active")

        log("->", "Read NamespaceArray / TranslateBrowsePaths Objects/Device / Browse Device")
        idx = await client.get_namespace_index(NS_URI)
        device = await client.nodes.objects.get_child(f"{idx}:Device")
        self.nodes = {"Objects": client.nodes.objects, "Server": client.nodes.server, "Device": device}
        children = await device.get_children_descriptions()
        for ref in children:
            self.nodes[ref.BrowseName.Name] = client.get_node(ref.NodeId)
        self.names = {node.nodeid: name for name, node in self.nodes.items()}
        log("<-", f"ns={idx}, Device: {', '.join(ref.BrowseName.Name for ref in children)}")

    async def do_disconnect(self) -> None:
        client = self.session()
        self.client, self.sub = None, None
        self.handles.clear()
        self.types.clear()
        log("->", "CloseSession / CloseSecureChannel")
        await client.disconnect()
        log("<-", "disconnected")

    async def do_endpoints(self) -> None:
        await get_endpoints()

    async def do_browse(self, ref: str = "Device") -> None:
        node = self.node(ref)
        log("->", f"Browse {self.label(node)}")
        for d in await node.get_children_descriptions():
            log("<-", f"  {d.BrowseName.Name} [{d.NodeClass.name}] {d.NodeId.to_string()}")

    async def do_read(self, ref: str) -> None:
        node = self.node(ref)
        name = self.label(node)
        log("->", f"Read  {name}")
        dv = await node.read_data_value()
        log("<-", f"Read  {name} = {dv.Value.Value} ({dv.Value.VariantType.name})")

    async def do_write(self, ref: str, text: str) -> None:
        node = self.node(ref)
        name = self.label(node)
        vtype = self.types.get(node.nodeid)
        if vtype is None:
            log("->", f"Read  {name}.DataType")
            vtype = self.types[node.nodeid] = await node.read_data_type_as_variant_type()
            log("<-", f"Read  {name}.DataType = {vtype.name}")
        value = parse_value(text, vtype)
        log("->", f"Write {name} := {value}")
        await node.write_value(ua.Variant(value, vtype))
        log("<-", f"Write {name} Good")

    async def do_call(self, ref: str) -> None:
        method = self.node(ref)
        name = self.label(method)
        log("->", f"Call  Device.{name}()")
        result = await self.nodes["Device"].call_method(method.nodeid)
        log("<-", f"Call  {name} -> {result}")

    async def do_sub(self, ref: str) -> None:
        node = self.node(ref)
        name = self.label(node)
        if node.nodeid in self.handles:
            raise RuntimeError(f"{name} уже в подписке")
        if self.sub is None:
            log("->", "CreateSubscription 500 ms")
            self.sub = await self.session().create_subscription(500, self)
            log("<-", f"Subscription id={self.sub.subscription_id}")
        log("->", f"CreateMonitoredItems {name}")
        self.handles[node.nodeid] = await self.sub.subscribe_data_change(node)
        log("<-", f"MonitoredItem {name} handle={self.handles[node.nodeid]}")

    async def do_unsub(self, ref: str | None = None) -> None:
        if self.sub is None:
            raise RuntimeError("подписки нет")
        if ref is None:
            sub, self.sub = self.sub, None
            self.handles.clear()
            log("->", "DeleteSubscriptions")
            await sub.delete()
            log("<-", "subscription deleted")
            return
        node = self.node(ref)
        name = self.label(node)
        handle = self.handles.pop(node.nodeid, None)
        if handle is None:
            raise RuntimeError(f"{name} не в подписке")
        log("->", f"DeleteMonitoredItems {name}")
        await self.sub.unsubscribe(handle)
        log("<-", f"MonitoredItem {name} deleted")

    async def run(self) -> None:
        print(HELP)
        try:
            while True:
                self.prompting = True
                try:
                    line = await ainput(PROMPT)
                except EOFError:
                    print()
                    break
                finally:
                    self.prompting = False
                try:
                    words = shlex.split(line)
                except ValueError as exc:
                    log("!!", str(exc))
                    continue
                if not words:
                    continue
                cmd, *args = words
                if cmd in ("quit", "exit"):
                    break
                if cmd == "help":
                    print(HELP)
                    continue
                handler = getattr(self, f"do_{cmd}", None)
                if handler is None:
                    log("!!", f"неизвестная команда {cmd}, см. help")
                    continue
                try:
                    inspect.signature(handler).bind(*args)
                except TypeError:
                    log("!!", f"неверные аргументы {cmd}, см. help")
                    continue
                try:
                    await handler(*args)
                except ua.UaStatusCodeError as exc:
                    log("<-", type(exc).__name__)
                except Exception as exc:
                    log("!!", f"{type(exc).__name__}: {exc}")
        finally:
            if self.client is not None:
                await self.do_disconnect()


class SubHandler:
    def datachange_notification(self, node, val, _data) -> None:
        log("<-", f"Publish Counter = {val}")


async def cycle(n: int) -> None:
    log("**", f"--- cycle {n} ---")

    client = Client(URL, timeout=5, watchdog_intervall=WATCHDOG)
    client.session_timeout = 600_000

    await get_endpoints()

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


async def auto() -> None:
    n = 1
    while True:
        try:
            await cycle(n)
        except Exception as exc:
            log("!!", f"{type(exc).__name__}: {exc}")
        n += 1
        await asyncio.sleep(PAUSE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OPC UA клиент стенда БДЗ")
    parser.add_argument("--auto", action="store_true", help="циклический сценарий вместо консоли")
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR)
    try:
        asyncio.run(auto() if args.auto else Console().run())
    except KeyboardInterrupt:
        pass
