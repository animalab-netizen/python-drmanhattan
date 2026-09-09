from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Protocol as TypingProtocol


Attributes = Mapping[str, str]


def _merge_attributes(*parts: Attributes | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for part in parts:
        if part:
            merged.update(part)
    return merged


@dataclass(frozen=True)
class Event:
    name: str
    attributes: Attributes = field(default_factory=dict)

    def with_attribute(self, key: str, value: str) -> "Event":
        return Event(name=self.name, attributes=_merge_attributes(self.attributes, {key: value}))

    def with_attributes(self, values: Attributes) -> "Event":
        return Event(name=self.name, attributes=_merge_attributes(self.attributes, values))


class EventObserver(TypingProtocol):
    def on_event(self, event: Event) -> None:
        ...


class EventEnricher(TypingProtocol):
    def enrich(self, event: Event) -> Event:
        ...


class EventBus(TypingProtocol):
    def subscribe(self, observer: EventObserver) -> None:
        ...

    def unsubscribe(self, observer: EventObserver) -> None:
        ...

    def publish(self, event: Event) -> None:
        ...


ObserverErrorHandler = Callable[[EventObserver, Event, Exception], None]


class DefaultEventBus:
    def __init__(
        self,
        enrichers: list[EventEnricher] | None = None,
        on_observer_error: ObserverErrorHandler | None = None,
    ) -> None:
        self._observers: list[EventObserver] = []
        self._enrichers = enrichers or []
        self._on_observer_error = on_observer_error

    def subscribe(self, observer: EventObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: EventObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def publish(self, event: Event) -> None:
        enriched = event
        for enricher in self._enrichers:
            enriched = enricher.enrich(enriched)

        for observer in list(self._observers):
            try:
                observer.on_event(enriched)
            except Exception as error:
                if self._on_observer_error is not None:
                    self._on_observer_error(observer, enriched, error)


@dataclass(frozen=True)
class CommonMetadata:
    app_version: str
    platform: str | None = None
    environment: str | None = None
    extra: Attributes = field(default_factory=dict)

    def as_attributes(self) -> dict[str, str]:
        attributes: dict[str, str] = {"app.version": self.app_version}
        if self.platform is not None:
            attributes["platform"] = self.platform
        if self.environment is not None:
            attributes["environment"] = self.environment
        attributes.update(self.extra)
        return attributes


@dataclass(frozen=True)
class CommonMetadataEnricher:
    metadata: CommonMetadata

    def enrich(self, event: Event) -> Event:
        return event.with_attributes(self.metadata.as_attributes())


@dataclass(frozen=True)
class HttpError:
    code: int
    type: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class Protocol:
    name: str


Protocol.Http = Protocol("http")  # type: ignore[attr-defined]
Protocol.WebSocket = Protocol("websocket")  # type: ignore[attr-defined]
Protocol.ServerSentEvents = Protocol("sse")  # type: ignore[attr-defined]
Protocol.Grpc = Protocol("grpc")  # type: ignore[attr-defined]
Protocol.Mqtt = Protocol("mqtt")  # type: ignore[attr-defined]
Protocol.Tcp = Protocol("tcp")  # type: ignore[attr-defined]
Protocol.Udp = Protocol("udp")  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ProtocolEndpoint:
    name: str
    address: str | None = None
    channel: str | None = None

    def as_attributes(self) -> dict[str, str]:
        attributes: dict[str, str] = {"endpoint.name": self.name}
        if self.address is not None:
            attributes["endpoint.address"] = self.address
        if self.channel is not None:
            attributes["endpoint.channel"] = self.channel
        return attributes


class ProtocolMessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass(frozen=True)
class ProtocolMessage:
    direction: ProtocolMessageDirection
    operation: str | None = None
    type: str | None = None
    correlation_id: str | None = None
    size_bytes: int | None = None
    attributes: Attributes = field(default_factory=dict)

    def as_attributes(self) -> dict[str, str]:
        mapped: dict[str, str] = {"message.direction": self.direction.value}
        if self.operation is not None:
            mapped["message.operation"] = self.operation
        if self.type is not None:
            mapped["message.type"] = self.type
        if self.correlation_id is not None:
            mapped["message.correlation_id"] = self.correlation_id
        if self.size_bytes is not None:
            mapped["message.size_bytes"] = str(self.size_bytes)
        mapped.update(self.attributes)
        return mapped


@dataclass(frozen=True)
class ProtocolFailure:
    code: str | None = None
    type: str | None = None
    message: str | None = None
    retryable: bool | None = None
    attributes: Attributes = field(default_factory=dict)

    def as_attributes(self) -> dict[str, str]:
        mapped: dict[str, str] = {}
        if self.code is not None:
            mapped["error.code"] = self.code
        if self.type is not None:
            mapped["error.type"] = self.type
        if self.message is not None:
            mapped["error.message"] = self.message
        if self.retryable is not None:
            mapped["error.retryable"] = str(self.retryable).lower()
        mapped.update(self.attributes)
        return mapped


@dataclass(frozen=True)
class ProtocolClose:
    code: int | None = None
    reason: str | None = None
    graceful: bool | None = None
    attributes: Attributes = field(default_factory=dict)

    def as_attributes(self) -> dict[str, str]:
        mapped: dict[str, str] = {}
        if self.code is not None:
            mapped["close.code"] = str(self.code)
        if self.reason is not None:
            mapped["close.reason"] = self.reason
        if self.graceful is not None:
            mapped["close.graceful"] = str(self.graceful).lower()
        mapped.update(self.attributes)
        return mapped


class EventFactory:
    def __init__(
        self,
        metadata: CommonMetadata | None = None,
        custom_enrichers: list[EventEnricher] | None = None,
    ) -> None:
        enrichers: list[EventEnricher] = []
        if metadata is not None:
            enrichers.append(CommonMetadataEnricher(metadata))
        enrichers.extend(custom_enrichers or [])
        self._enrichers = enrichers

    def screen_viewed(self, screen_name: str) -> Event:
        return self._enrich(Event(name="screen_viewed", attributes={"screen.name": screen_name}))

    def tap(self, screen_name: str, action: str) -> Event:
        return self._enrich(
            Event(
                name="tap",
                attributes={
                    "screen.name": screen_name,
                    "event.action": action,
                },
            )
        )

    def http_error(self, screen_name: str, error: HttpError) -> Event:
        attributes: dict[str, str] = {
            "screen.name": screen_name,
            "error.code": str(error.code),
        }
        if error.type is not None:
            attributes["error.type"] = error.type
        if error.message is not None:
            attributes["error.message"] = error.message
        return self._enrich(Event(name="http_error", attributes=attributes))

    def custom(self, name: str, attributes: Attributes | None = None) -> Event:
        return self._enrich(Event(name=name, attributes=attributes or {}))

    def protocol_connection_started(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self._enrich_protocol_event(
            "protocol_connection_started", protocol, endpoint, session_id, attributes or {}
        )

    def protocol_connection_opened(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self._enrich_protocol_event(
            "protocol_connection_opened", protocol, endpoint, session_id, attributes or {}
        )

    def protocol_message(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        message: ProtocolMessage,
        session_id: str | None = None,
    ) -> Event:
        return self._enrich_protocol_event(
            "protocol_message", protocol, endpoint, session_id, message.as_attributes()
        )

    def protocol_connection_closed(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        close: ProtocolClose | None = None,
        session_id: str | None = None,
    ) -> Event:
        return self._enrich_protocol_event(
            "protocol_connection_closed",
            protocol,
            endpoint,
            session_id,
            (close or ProtocolClose()).as_attributes(),
        )

    def protocol_failure(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        failure: ProtocolFailure,
        session_id: str | None = None,
    ) -> Event:
        return self._enrich_protocol_event(
            "protocol_failure", protocol, endpoint, session_id, failure.as_attributes()
        )

    def protocol_reconnect_scheduled(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        attempt: int,
        delay_millis: int,
        reason: str | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        mapped = {
            "reconnect.attempt": str(attempt),
            "reconnect.delay_ms": str(delay_millis),
        }
        if reason is not None:
            mapped["reconnect.reason"] = reason
        mapped.update(attributes or {})
        return self._enrich_protocol_event(
            "protocol_reconnect_scheduled", protocol, endpoint, session_id, mapped
        )

    def web_socket_connection_started(
        self,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self.protocol_connection_started(Protocol.WebSocket, endpoint, session_id, attributes)

    def web_socket_connection_opened(
        self,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self.protocol_connection_opened(Protocol.WebSocket, endpoint, session_id, attributes)

    def web_socket_message_sent(
        self,
        endpoint: ProtocolEndpoint,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self.protocol_message(
            Protocol.WebSocket,
            endpoint,
            ProtocolMessage(
                direction=ProtocolMessageDirection.OUTBOUND,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                attributes=attributes or {},
            ),
            session_id,
        )

    def web_socket_message_received(
        self,
        endpoint: ProtocolEndpoint,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self.protocol_message(
            Protocol.WebSocket,
            endpoint,
            ProtocolMessage(
                direction=ProtocolMessageDirection.INBOUND,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                attributes=attributes or {},
            ),
            session_id,
        )

    def web_socket_connection_closed(
        self,
        endpoint: ProtocolEndpoint,
        close: ProtocolClose | None = None,
        session_id: str | None = None,
    ) -> Event:
        return self.protocol_connection_closed(Protocol.WebSocket, endpoint, close, session_id)

    def web_socket_failure(
        self,
        endpoint: ProtocolEndpoint,
        failure: ProtocolFailure,
        session_id: str | None = None,
    ) -> Event:
        return self.protocol_failure(Protocol.WebSocket, endpoint, failure, session_id)

    def web_socket_reconnect_scheduled(
        self,
        endpoint: ProtocolEndpoint,
        attempt: int,
        delay_millis: int,
        reason: str | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> Event:
        return self.protocol_reconnect_scheduled(
            Protocol.WebSocket,
            endpoint,
            attempt,
            delay_millis,
            reason,
            session_id,
            attributes,
        )

    def _enrich(self, event: Event) -> Event:
        enriched = event
        for enricher in self._enrichers:
            enriched = enricher.enrich(enriched)
        return enriched

    def _enrich_protocol_event(
        self,
        name: str,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None,
        attributes: Attributes,
    ) -> Event:
        mapped = {
            "protocol.name": protocol.name,
            **endpoint.as_attributes(),
            **attributes,
        }
        if session_id is not None:
            mapped["session.id"] = session_id
        return self._enrich(Event(name=name, attributes=mapped))


class DrManhattan:
    def __init__(self, bus: EventBus, factory: EventFactory) -> None:
        self._bus = bus
        self._factory = factory

    def publish(self, event: Event) -> None:
        self._bus.publish(event)

    def screen_viewed(self, screen_name: str) -> None:
        self.publish(self._factory.screen_viewed(screen_name))

    def tap(self, screen_name: str, action: str) -> None:
        self.publish(self._factory.tap(screen_name, action))

    def http_error(self, screen_name: str, error: HttpError) -> None:
        self.publish(self._factory.http_error(screen_name, error))

    def custom(self, name: str, attributes: Attributes | None = None) -> None:
        self.publish(self._factory.custom(name, attributes))

    def protocol_connection_started(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(self._factory.protocol_connection_started(protocol, endpoint, session_id, attributes))

    def protocol_connection_opened(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(self._factory.protocol_connection_opened(protocol, endpoint, session_id, attributes))

    def protocol_message(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        message: ProtocolMessage,
        session_id: str | None = None,
    ) -> None:
        self.publish(self._factory.protocol_message(protocol, endpoint, message, session_id))

    def protocol_connection_closed(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        close: ProtocolClose | None = None,
        session_id: str | None = None,
    ) -> None:
        self.publish(self._factory.protocol_connection_closed(protocol, endpoint, close, session_id))

    def protocol_failure(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        failure: ProtocolFailure,
        session_id: str | None = None,
    ) -> None:
        self.publish(self._factory.protocol_failure(protocol, endpoint, failure, session_id))

    def protocol_reconnect_scheduled(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        attempt: int,
        delay_millis: int,
        reason: str | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(
            self._factory.protocol_reconnect_scheduled(
                protocol, endpoint, attempt, delay_millis, reason, session_id, attributes
            )
        )

    def web_socket_connection_started(
        self,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(self._factory.web_socket_connection_started(endpoint, session_id, attributes))

    def web_socket_connection_opened(
        self,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(self._factory.web_socket_connection_opened(endpoint, session_id, attributes))

    def web_socket_message_sent(
        self,
        endpoint: ProtocolEndpoint,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(
            self._factory.web_socket_message_sent(
                endpoint,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                session_id=session_id,
                attributes=attributes,
            )
        )

    def web_socket_message_received(
        self,
        endpoint: ProtocolEndpoint,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(
            self._factory.web_socket_message_received(
                endpoint,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                session_id=session_id,
                attributes=attributes,
            )
        )

    def web_socket_connection_closed(
        self,
        endpoint: ProtocolEndpoint,
        close: ProtocolClose | None = None,
        session_id: str | None = None,
    ) -> None:
        self.publish(self._factory.web_socket_connection_closed(endpoint, close, session_id))

    def web_socket_failure(
        self,
        endpoint: ProtocolEndpoint,
        failure: ProtocolFailure,
        session_id: str | None = None,
    ) -> None:
        self.publish(self._factory.web_socket_failure(endpoint, failure, session_id))

    def web_socket_reconnect_scheduled(
        self,
        endpoint: ProtocolEndpoint,
        attempt: int,
        delay_millis: int,
        reason: str | None = None,
        session_id: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.publish(
            self._factory.web_socket_reconnect_scheduled(
                endpoint, attempt, delay_millis, reason, session_id, attributes
            )
        )

    def protocol_session(
        self,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
    ) -> "ProtocolSessionTracker":
        return ProtocolSessionTracker(self, protocol, endpoint, session_id)

    def web_socket_session(
        self,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
    ) -> "WebSocketSessionTracker":
        return WebSocketSessionTracker(self, endpoint, session_id)


class ProtocolSessionTracker:
    def __init__(
        self,
        dr_manhatan: DrManhattan,
        protocol: Protocol,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
    ) -> None:
        self._dr_manhatan = dr_manhatan
        self._protocol = protocol
        self.endpoint = endpoint
        self.session_id = session_id

    def connection_started(self, attributes: Attributes | None = None) -> None:
        self._dr_manhatan.protocol_connection_started(
            self._protocol, self.endpoint, self.session_id, attributes
        )

    def connection_opened(self, attributes: Attributes | None = None) -> None:
        self._dr_manhatan.protocol_connection_opened(
            self._protocol, self.endpoint, self.session_id, attributes
        )

    def message(self, message: ProtocolMessage) -> None:
        self._dr_manhatan.protocol_message(self._protocol, self.endpoint, message, self.session_id)

    def inbound_message(
        self,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.message(
            ProtocolMessage(
                direction=ProtocolMessageDirection.INBOUND,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                attributes=attributes or {},
            )
        )

    def outbound_message(
        self,
        *,
        operation: str | None = None,
        type: str | None = None,
        correlation_id: str | None = None,
        size_bytes: int | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self.message(
            ProtocolMessage(
                direction=ProtocolMessageDirection.OUTBOUND,
                operation=operation,
                type=type,
                correlation_id=correlation_id,
                size_bytes=size_bytes,
                attributes=attributes or {},
            )
        )

    def heartbeat_sent(self, correlation_id: str | None = None, attributes: Attributes | None = None) -> None:
        self.outbound_message(
            operation="heartbeat",
            type="heartbeat",
            correlation_id=correlation_id,
            attributes=attributes,
        )

    def heartbeat_received(self, correlation_id: str | None = None, attributes: Attributes | None = None) -> None:
        self.inbound_message(
            operation="heartbeat",
            type="heartbeat",
            correlation_id=correlation_id,
            attributes=attributes,
        )

    def reconnect_scheduled(
        self,
        attempt: int,
        delay_millis: int,
        reason: str | None = None,
        attributes: Attributes | None = None,
    ) -> None:
        self._dr_manhatan.protocol_reconnect_scheduled(
            self._protocol,
            self.endpoint,
            attempt,
            delay_millis,
            reason,
            self.session_id,
            attributes,
        )

    def failure(self, failure: ProtocolFailure) -> None:
        self._dr_manhatan.protocol_failure(self._protocol, self.endpoint, failure, self.session_id)

    def closed(self, close: ProtocolClose | None = None) -> None:
        self._dr_manhatan.protocol_connection_closed(
            self._protocol, self.endpoint, close, self.session_id
        )


class WebSocketSessionTracker(ProtocolSessionTracker):
    def __init__(
        self,
        dr_manhatan: DrManhattan,
        endpoint: ProtocolEndpoint,
        session_id: str | None = None,
    ) -> None:
        super().__init__(dr_manhatan, Protocol.WebSocket, endpoint, session_id)
