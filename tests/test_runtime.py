from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from python_drmanhatan import (  # noqa: E402
    CommonMetadata,
    DefaultEventBus,
    DrManhatan,
    Event,
    EventFactory,
    HttpError,
    Protocol,
    ProtocolClose,
    ProtocolEndpoint,
    ProtocolFailure,
)


class Recorder:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def on_event(self, event: Event) -> None:
        self.events.append(event)


class RuntimeTests(unittest.TestCase):
    def test_event_factory_enriches_common_metadata(self) -> None:
        factory = EventFactory(
            metadata=CommonMetadata("1.0.0", platform="python", environment="prod")
        )

        event = factory.custom("custom_event", {"feature": "chat"})

        self.assertEqual("custom_event", event.name)
        self.assertEqual("chat", event.attributes["feature"])
        self.assertEqual("1.0.0", event.attributes["app.version"])
        self.assertEqual("python", event.attributes["platform"])
        self.assertEqual("prod", event.attributes["environment"])

    def test_default_event_bus_keeps_order_and_isolates_errors(self) -> None:
        deliveries: list[str] = []
        errors: list[Exception] = []

        class FailingObserver:
            def on_event(self, event: Event) -> None:
                deliveries.append("first")
                raise ValueError(event.name)

        class SuccessObserver:
            def on_event(self, event: Event) -> None:
                deliveries.append("second")

        bus = DefaultEventBus(on_observer_error=lambda _o, _e, error: errors.append(error))
        bus.subscribe(FailingObserver())
        bus.subscribe(SuccessObserver())

        bus.publish(Event("ordered"))

        self.assertEqual(["first", "second"], deliveries)
        self.assertEqual(1, len(errors))
        self.assertIsInstance(errors[0], ValueError)

    def test_drmanhatan_publishes_websocket_events(self) -> None:
        recorder = Recorder()
        bus = DefaultEventBus()
        bus.subscribe(recorder)

        tracker = DrManhatan(bus, EventFactory(metadata=CommonMetadata("1.0.0")))
        endpoint = ProtocolEndpoint(
            "chat", address="wss://socket.example.com", channel="rooms/general"
        )

        tracker.web_socket_connection_started(endpoint, "ws-42")
        tracker.web_socket_message_sent(
            endpoint,
            operation="join_room",
            type="json",
            correlation_id="corr-1",
            session_id="ws-42",
        )
        tracker.web_socket_failure(
            endpoint,
            ProtocolFailure(
                code="WS_TIMEOUT",
                type="transport",
                message="heartbeat timeout",
                retryable=True,
            ),
            "ws-42",
        )

        self.assertEqual(3, len(recorder.events))
        self.assertEqual("protocol_connection_started", recorder.events[0].name)
        self.assertEqual("outbound", recorder.events[1].attributes["message.direction"])
        self.assertEqual("join_room", recorder.events[1].attributes["message.operation"])
        self.assertEqual("protocol_failure", recorder.events[2].name)
        self.assertEqual("true", recorder.events[2].attributes["error.retryable"])

    def test_protocol_session_tracker_emits_heartbeat_and_reconnect(self) -> None:
        recorder = Recorder()
        bus = DefaultEventBus()
        bus.subscribe(recorder)

        tracker = DrManhatan(bus, EventFactory())
        session = tracker.protocol_session(Protocol.Mqtt, ProtocolEndpoint("broker"), "mqtt-9")

        session.heartbeat_sent("hb-out-1")
        session.heartbeat_received("hb-in-1")
        session.reconnect_scheduled(2, 1500, "network_lost")
        session.closed(ProtocolClose(code=1001, reason="going away", graceful=False))

        self.assertEqual(4, len(recorder.events))
        self.assertEqual("heartbeat", recorder.events[0].attributes["message.operation"])
        self.assertEqual("outbound", recorder.events[0].attributes["message.direction"])
        self.assertEqual("inbound", recorder.events[1].attributes["message.direction"])
        self.assertEqual("2", recorder.events[2].attributes["reconnect.attempt"])
        self.assertEqual("1001", recorder.events[3].attributes["close.code"])

    def test_http_error_maps_screen_and_error_attributes(self) -> None:
        event = EventFactory().http_error(
            "Checkout",
            HttpError(503, type="maintenance", message="temporarily unavailable"),
        )

        self.assertEqual("http_error", event.name)
        self.assertEqual("Checkout", event.attributes["screen.name"])
        self.assertEqual("503", event.attributes["error.code"])
        self.assertEqual("maintenance", event.attributes["error.type"])
