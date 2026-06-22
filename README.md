# python-drmanhatan

`python-drmanhatan` is the Python member of the DrManhatan observability family.

It preserves the same event and protocol interpretation model established in `kotlin-drmanhatan` while remaining natural for Python services, workers and async-adjacent applications.

## Scope

- immutable event records
- observer publication
- enricher composition
- protocol failure and reconnect modeling
- session-oriented timeline tracking
- WebSocket-focused convenience helpers in the core runtime

## Coordinates

- package: `python-drmanhatan`
- repository: `python-drmanhatan`
- version: `0.1.0`

Installation:

```bash
pip install python-drmanhatan
```

## Public API

- `Event`
- `EventObserver`
- `EventEnricher`
- `EventBus`
- `DefaultEventBus`
- `CommonMetadata`
- `CommonMetadataEnricher`
- `HttpError`
- `Protocol`
- `ProtocolEndpoint`
- `ProtocolMessage`
- `ProtocolMessageDirection`
- `ProtocolFailure`
- `ProtocolClose`
- `EventFactory`
- `DrManhatan`
- `ProtocolSessionTracker`
- `WebSocketSessionTracker`

## Basic Example

```python
from python_drmanhatan import (
    CommonMetadata,
    DefaultEventBus,
    DrManhatan,
    EventFactory,
    HttpError,
)


class Printer:
    def on_event(self, event):
        print(event.name, event.attributes)


bus = DefaultEventBus()
bus.subscribe(Printer())

tracker = DrManhatan(
    bus,
    EventFactory(
        metadata=CommonMetadata(
            "1.0.0",
            platform="python",
            environment="prod",
        )
    ),
)

tracker.screen_viewed("Home")
tracker.http_error("Checkout", HttpError(500, type="server_error"))
```

## Session Example

```python
from python_drmanhatan import DefaultEventBus, DrManhatan, EventFactory, Protocol, ProtocolEndpoint

tracker = DrManhatan(DefaultEventBus(), EventFactory())

session = tracker.protocol_session(
    Protocol.Mqtt,
    ProtocolEndpoint("broker"),
    "mqtt-9",
)

session.connection_started()
session.heartbeat_sent("hb-out-1")
session.reconnect_scheduled(2, 1500, "network_lost")
```

## Validation

```bash
python3 -m unittest discover tests
python3 -m pip wheel . --no-build-isolation --no-deps -w /tmp/python-drmanhatan-dist
```

## Notes

- semantic parity with `kotlin-drmanhatan` matters more than textual symmetry
- transport adapters should stay optional and ecosystem-specific
