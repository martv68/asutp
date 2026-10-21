import asyncio
import logging
import os
from datetime import datetime

from asyncua import Server, ua
from asyncua.common.callback import CallbackType
from asyncua.common.methods import uamethod

ENDPOINT = os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/")
NS_URI = "urn:bdz:opcua:stand"


def log(direction: str, msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction} {msg}", flush=True)


class Stand:
    def __init__(self) -> None:
        self.server = Server()
        self.names: dict[ua.NodeId, str] = {}

    def name(self, node_id: ua.NodeId) -> str:
        return self.names.get(node_id, node_id.to_string())

    def on_read(self, event, _dispatcher) -> None:
        if not event.is_external:
            return
        for rv, dv in zip(event.request_params.NodesToRead, event.response_params):
            if rv.NodeId in self.names and rv.AttributeId == ua.AttributeIds.Value:
                log("<-", f"Read  {self.name(rv.NodeId)} = {dv.Value.Value if dv.Value else None}")

    def on_write(self, event, _dispatcher) -> None:
        if not event.is_external:
            return
        for wv, status in zip(event.request_params.NodesToWrite, event.response_params):
            log("<-", f"Write {self.name(wv.NodeId)} := {wv.Value.Value.Value} [{status.name}]")

    def on_subscribe(self, event, _dispatcher) -> None:
        for item in event.request_params.ItemsToCreate:
            log("<-", f"Subscribe {self.name(item.ItemToMonitor.NodeId)}")

    async def run(self) -> None:
        s = self.server
        await s.init()
        s.set_endpoint(ENDPOINT)
        s.set_server_name("BDZ OPC UA stand")
        s.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        s.set_identity_tokens([ua.AnonymousIdentityToken])

        idx = await s.register_namespace(NS_URI)
        device = await s.nodes.objects.add_object(ua.NodeId("Device", idx), ua.QualifiedName("Device", idx))
        counter = await device.add_variable(ua.NodeId("Counter", idx), ua.QualifiedName("Counter", idx), 0, ua.VariantType.UInt32)
        setpoint = await device.add_variable(ua.NodeId("Setpoint", idx), ua.QualifiedName("Setpoint", idx), 0.0, ua.VariantType.Double)
        enabled = await device.add_variable(ua.NodeId("Enabled", idx), ua.QualifiedName("Enabled", idx), False, ua.VariantType.Boolean)
        await setpoint.set_writable()
        await enabled.set_writable()

        @uamethod
        async def reset(_parent):
            await counter.write_value(ua.Variant(0, ua.VariantType.UInt32))
            log("<-", "Call  Reset() -> Counter = 0")
            return True

        await device.add_method(
            ua.NodeId("Reset", idx), ua.QualifiedName("Reset", idx), reset, [], [ua.VariantType.Boolean]
        )

        for node, name in ((counter, "Counter"), (setpoint, "Setpoint"), (enabled, "Enabled")):
            self.names[node.nodeid] = name

        s.subscribe_server_callback(CallbackType.PostRead, self.on_read)
        s.subscribe_server_callback(CallbackType.PostWrite, self.on_write)
        s.subscribe_server_callback(CallbackType.ItemSubscriptionCreated, self.on_subscribe)

        log("**", f"server listening on {ENDPOINT} (SecurityPolicy None, Anonymous)")
        async with s:
            value = 0
            while True:
                await asyncio.sleep(1)
                value = (await counter.read_value() + 1) % 1000
                await counter.write_value(ua.Variant(value, ua.VariantType.UInt32))


class ConnectionLog(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("New connection from"):
            record.msg, record.args = "** client connected: %s:%s", record.args[0] if isinstance(record.args[0], tuple) else record.args
            return True
        if msg.startswith("Lost connection from"):
            record.msg, record.args = "** client disconnected: %s:%s", record.args[0] if isinstance(record.args[0], tuple) else record.args
            return True
        return False


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", "%H:%M:%S"))
    handler.addFilter(ConnectionLog())
    net_log = logging.getLogger("asyncua.server.binary_server_asyncio")
    net_log.setLevel(logging.INFO)
    net_log.addHandler(handler)
    net_log.propagate = False
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger("asyncua.server.uaprocessor").addFilter(lambda r: "BadNoSubscription" not in r.getMessage())
    asyncio.run(Stand().run())
