# python-drmanhattan

`python-drmanhattan` is the Python member of the DrManhattan observability family.

It preserves the same event and protocol interpretation model established in `kotlin-drmanhattan` while remaining natural for Python services, workers and async-adjacent applications.

The package provides a compact runtime for:

- immutable event records
- observer publication
- enricher composition
- protocol failure and reconnect modeling
- session-oriented timeline tracking
- WebSocket-focused convenience helpers in the core runtime

The goal is to make event flow easier to standardize, easier to reason about, and less vulnerable to common mistakes around vendor coupling, protocol lifecycle tracking, retry visibility and message-oriented observability.

## Why Use DrManhattan

`python-drmanhattan` is useful when a system needs observability but should not let transport or telemetry concerns leak into business code.

Typical gains include:

- a single event vocabulary across jobs, services and protocol layers
- lower coupling to analytics, logging and monitoring vendors
- easier migration between providers because the domain emits neutral events
- more explicit communication timelines for stateful protocols
- better operational visibility during failures, retries and reconnect flows

In practice, this means teams can treat observability as part of architecture instead of as scattered implementation detail.

## Asynchronous Work

The package is especially useful in asynchronous and message-oriented systems.

Asynchrony usually makes systems harder to interpret because cause and effect are separated in time:

- a connection starts in one place
- a message arrives later in another place
- a retry is scheduled elsewhere
- an error is observed after the original action has already left the current call stack

`python-drmanhattan` improves this by giving those steps a shared event model and a shared session context.

This helps teams:

- reconstruct communication timelines more reliably
- track retries and reconnects without inventing ad hoc logging everywhere
- correlate outbound intent with inbound outcomes
- expose protocol failures with enough metadata to support analysis and debugging
- keep asynchronous work observable without forcing domain code to know the final monitoring backend

## What DrManhattan Does Not Claim

`python-drmanhattan` does not try to replace your network stack, your analytics provider or your monitoring backend.

It does not open WebSocket connections, execute HTTP calls or guarantee that every team will model events with identical naming conventions. The package is intentionally narrower than that: it standardizes event construction, enrichment and publication so the rest of the system can evolve without forcing the domain layer to know too much about the final destination of those events.

The reason is pragmatic: a communication observability package should make transport and vendor integration easier, not become another hard dependency that application code cannot escape later.

## Repository

- source: [github.com/animalab-netizen/python-drmanhattan](https://github.com/animalab-netizen/python-drmanhattan)

## Status

`python-drmanhattan` is in early public release stage and evolving through incremental compatibility-safe improvements.

The API is usable and unit-tested, but it is still under refinement. Expect incremental improvements in publication maturity, adapter coverage and protocol semantics as the package evolves.

## Coordinates

- package: `python-drmanhattan`
- repository: `python-drmanhattan`
- version: `0.1.2`

Installation:

```bash
pip install python-drmanhattan
```

## API Stability Notes

Current guidance:

- prefer matching on explicit event names and attributes instead of coupling domain code to transport callbacks directly
- keep telemetry vocabulary neutral so application code does not depend on a specific vendor
- use `ProtocolSessionTracker` when the important thing is the whole communication timeline rather than one isolated event
- do not treat local packaging or workflow details as part of the product contract

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
- `DrManhattan`
- `ProtocolSessionTracker`
- `WebSocketSessionTracker`

Internal publication details, local scripts and workflow implementation details are intentionally not part of the product contract and may change without notice.

## Core Concepts

### 1. Event

`Event` is the immutable unit of observation in the package.

It gives the system:

- a stable event name
- explicit string attributes
- a simple representation that can be forwarded to logs, analytics, metrics or custom observers

### 2. Enricher

`EventEnricher` adds context without requiring the producer to know the final destination of the event.

Typical usage includes:

- app version
- platform
- environment
- protocol metadata
- transport-specific attributes

### 3. EventBus

`EventBus` publishes events to one or more observers.

This keeps event production separate from event handling, so application code does not need to bind directly to a specific monitoring vendor or output mechanism.

`DefaultEventBus` delivers observers in subscription order and isolates observer exceptions so a failing observer does not prevent later observers from receiving the same event. An optional error callback can be used to report those failures.

### 4. EventFactory

`EventFactory` is the main construction layer for common event categories.

It provides helpers for:

- screen events
- tap events
- HTTP failures
- protocol connection lifecycle
- message-oriented communication events
- WebSocket-specific convenience builders

### 5. Protocol Sessions

`ProtocolSessionTracker` and `WebSocketSessionTracker` provide a higher-level model for stateful communication.

This is the preferred abstraction when the important thing is not one isolated event, but the whole communication timeline:

- connection started
- connection opened
- inbound and outbound messages
- heartbeat signals
- reconnect scheduling
- failure
- close

## Protocol Coverage

`python-drmanhattan` covers stateful and message-oriented protocols without depending on a specific transport engine.

This includes use cases such as:

- WebSocket
- SSE
- gRPC streaming
- MQTT
- custom TCP/UDP communication channels

The purpose is not transport execution. The purpose is observability of protocol lifecycle and message flow.

## Basic Example

```python
from python_drmanhattan import (
    CommonMetadata,
    DefaultEventBus,
    DrManhattan,
    EventFactory,
    HttpError,
)


class Printer:
    def on_event(self, event):
        print(event.name, event.attributes)


bus = DefaultEventBus()
bus.subscribe(Printer())

tracker = DrManhattan(
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

## WebSocket Example

```python
from python_drmanhattan import (
    CommonMetadata,
    DefaultEventBus,
    DrManhattan,
    EventFactory,
    ProtocolClose,
    ProtocolEndpoint,
    ProtocolFailure,
)


class Printer:
    def on_event(self, event):
        print(event.name, event.attributes)


bus = DefaultEventBus()
bus.subscribe(Printer())

tracker = DrManhattan(
    bus,
    EventFactory(
        metadata=CommonMetadata(
            "1.0.0",
            platform="python",
            environment="prod",
        )
    ),
)

endpoint = ProtocolEndpoint(
    "chat",
    address="wss://socket.example.com",
    channel="rooms/general",
)

tracker.web_socket_connection_started(endpoint, "ws-42")
tracker.web_socket_connection_opened(endpoint, "ws-42")
tracker.web_socket_message_sent(
    endpoint,
    operation="join_room",
    type="json",
    correlation_id="corr-1",
    session_id="ws-42",
)
tracker.web_socket_message_received(
    endpoint,
    operation="chat_message",
    type="json",
    size_bytes=512,
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
tracker.web_socket_connection_closed(
    endpoint,
    ProtocolClose(code=1001, reason="going away", graceful=False),
    "ws-42",
)
```

## Session Example

```python
from python_drmanhattan import DefaultEventBus, DrManhattan, EventFactory, Protocol, ProtocolEndpoint

tracker = DrManhattan(DefaultEventBus(), EventFactory())

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
python3 -m pip wheel . --no-build-isolation --no-deps -w /tmp/python-drmanhattan-dist
```

## Publishing

See [PUBLICATION.md](/Users/caiosanchezchristino/Desktop/drmanhattan-projects/python-drmanhattan/PUBLICATION.md).

## Contributing

See [CONTRIBUTING.md](/Users/caiosanchezchristino/Desktop/drmanhattan-projects/python-drmanhattan/CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](/Users/caiosanchezchristino/Desktop/drmanhattan-projects/python-drmanhattan/CHANGELOG.md).

## License

Apache-2.0. See [LICENSE](/Users/caiosanchezchristino/Desktop/drmanhattan-projects/python-drmanhattan/LICENSE).

## Notes

- semantic parity with `kotlin-drmanhattan` matters more than textual symmetry
- transport adapters should stay optional and ecosystem-specific
