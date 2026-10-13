"""TTL-bound redacted session history and response cache, memory or Redis."""

import json
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock
from time import time
from typing import Protocol
from uuid import UUID

from app.models.schemas import SessionMessage


class Store(Protocol):
    def history(self, session_id: UUID) -> list[SessionMessage]: ...
    def append_turn(self, session_id: UUID, user: str, assistant: str) -> None: ...
    def delete_session(self, session_id: UUID) -> None: ...
    def cache_get(self, key: str) -> dict | None: ...
    def cache_set(self, key: str, value: dict) -> None: ...
    def candidates(self) -> list[dict]: ...
    def ready(self) -> bool: ...
    def close(self) -> None: ...


def cache_key(query: str) -> str:
    return sha256(query.strip().encode()).hexdigest()


def turn_messages(user: str, assistant: str) -> list[SessionMessage]:
    now = datetime.now(UTC)
    return [
        SessionMessage(role="user", content=user, created_at=now),
        SessionMessage(role="assistant", content=assistant, created_at=now),
    ]


class MemoryStore:
    def __init__(
        self,
        session_ttl: int = 1800,
        cache_ttl: int = 300,
        max_messages: int = 40,
        max_keys: int = 2000,
    ) -> None:
        self._session_ttl, self._cache_ttl = session_ttl, cache_ttl
        self._max_messages, self._max_keys = max_messages, max_keys
        self._sessions: OrderedDict[str, tuple[float, list[SessionMessage]]] = OrderedDict()
        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._lock = RLock()

    def _prune(self, mapping: OrderedDict) -> None:
        for key in [k for k, (expires, _) in mapping.items() if expires <= time()]:
            del mapping[key]
        while len(mapping) > self._max_keys:
            mapping.popitem(last=False)

    def history(self, session_id: UUID) -> list[SessionMessage]:
        with self._lock:
            self._prune(self._sessions)
            item = self._sessions.get(str(session_id))
            return [message.model_copy(deep=True) for message in item[1]] if item else []

    def append_turn(self, session_id: UUID, user: str, assistant: str) -> None:
        with self._lock:
            items = (self.history(session_id) + turn_messages(user, assistant))[
                -self._max_messages :
            ]
            self._sessions[str(session_id)] = (time() + self._session_ttl, items)
            self._sessions.move_to_end(str(session_id))
            self._prune(self._sessions)

    def delete_session(self, session_id: UUID) -> None:
        with self._lock:
            self._sessions.pop(str(session_id), None)

    def cache_get(self, key: str) -> dict | None:
        with self._lock:
            self._prune(self._cache)
            item = self._cache.get(key)
            return deepcopy(item[1]) if item else None

    def cache_set(self, key: str, value: dict) -> None:
        with self._lock:
            self._cache[key] = (time() + self._cache_ttl, deepcopy(value))
            self._cache.move_to_end(key)
            self._prune(self._cache)

    def candidates(self) -> list[dict]:
        with self._lock:
            self._prune(self._cache)
            return [deepcopy(item[1]) for item in list(self._cache.values())[-100:]]

    def ready(self) -> bool:
        return True

    def close(self) -> None:
        pass


class RedisStore:
    def __init__(
        self,
        client,
        namespace: str,
        session_ttl: int = 1800,
        cache_ttl: int = 300,
        max_messages: int = 40,
    ) -> None:
        self._client, self._namespace = client, namespace
        self._session_ttl, self._cache_ttl = session_ttl, cache_ttl
        self._max_messages = max_messages

    def _key(self, kind: str, identifier: str) -> str:
        return f"telcoai:{self._namespace}:{kind}:{identifier}"

    def history(self, session_id: UUID) -> list[SessionMessage]:
        return [
            SessionMessage.model_validate_json(item)
            for item in self._client.lrange(self._key("session", str(session_id)), 0, -1)
        ]

    def append_turn(self, session_id: UUID, user: str, assistant: str) -> None:
        key = self._key("session", str(session_id))
        with self._client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *(msg.model_dump_json() for msg in turn_messages(user, assistant)))
            pipe.ltrim(key, -self._max_messages, -1)
            pipe.expire(key, self._session_ttl)
            pipe.execute()

    def delete_session(self, session_id: UUID) -> None:
        self._client.delete(self._key("session", str(session_id)))

    def cache_get(self, key: str) -> dict | None:
        value = self._client.get(self._key("cache", key))
        return json.loads(value) if value else None

    def cache_set(self, key: str, value: dict) -> None:
        index = self._key("cache_index", "recent")
        with self._client.pipeline(transaction=True) as pipe:
            pipe.set(self._key("cache", key), json.dumps(value), ex=self._cache_ttl)
            pipe.zadd(index, {key: time()})
            pipe.zremrangebyrank(index, 0, -101)
            pipe.expire(index, self._cache_ttl)
            pipe.execute()

    def candidates(self) -> list[dict]:
        keys = self._client.zrevrange(self._key("cache_index", "recent"), 0, 99)
        if not keys:
            return []
        values = self._client.mget(
            [self._key("cache", k.decode() if isinstance(k, bytes) else k) for k in keys]
        )
        return [json.loads(value) for value in values if value]

    def ready(self) -> bool:
        return bool(self._client.ping())

    def close(self) -> None:
        self._client.close()
