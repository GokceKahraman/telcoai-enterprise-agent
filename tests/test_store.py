"""Exercise RedisStore using Redis command semantics, without an external server."""

from concurrent.futures import ThreadPoolExecutor
from time import sleep
from uuid import uuid4

import fakeredis
import pytest

from app.services.store import MemoryStore, RedisStore, cache_key


@pytest.fixture
def redis_client():
    client = fakeredis.FakeRedis()
    yield client
    client.close()


def test_redis_turn_append_is_atomic_under_concurrent_writers(redis_client):
    store = RedisStore(redis_client, "tenant-a:tr:revision-one", max_messages=40)
    session_id = uuid4()
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(
            pool.map(
                lambda index: store.append_turn(session_id, f"user-{index}", f"assistant-{index}"),
                range(12),
            )
        )
    messages = store.history(session_id)
    assert len(messages) == 24
    for user, assistant in zip(messages[::2], messages[1::2], strict=True):
        assert (user.role, assistant.role) == ("user", "assistant")
        assert user.content.removeprefix("user-") == assistant.content.removeprefix("assistant-")
        assert user.created_at == assistant.created_at


def test_redis_history_cap_ttl_refresh_and_delete(redis_client):
    store = RedisStore(redis_client, "tenant-a", session_ttl=30, max_messages=4)
    session_id = uuid4()
    for index in range(3):
        store.append_turn(session_id, f"user-{index}", f"assistant-{index}")
    assert [message.content for message in store.history(session_id)] == [
        "user-1",
        "assistant-1",
        "user-2",
        "assistant-2",
    ]
    key = store._key("session", str(session_id))
    assert 0 < redis_client.ttl(key) <= 30
    redis_client.expire(key, 1)
    store.append_turn(session_id, "user-3", "assistant-3")
    assert redis_client.ttl(key) >= 29
    store.delete_session(session_id)
    assert store.history(session_id) == []


def test_redis_namespace_isolates_history_exact_cache_and_semantic_candidates(redis_client):
    first = RedisStore(redis_client, "tenant-a:tr:revision-one")
    second = RedisStore(redis_client, "tenant-b:tr:revision-one")
    new_revision = RedisStore(redis_client, "tenant-a:tr:revision-two")
    session_id = uuid4()
    first.append_turn(session_id, "<EMAIL_ADDRESS>", "approved answer")
    first.cache_set("shared-query", {"answer": "tenant-a", "vector": [1.0, 0.0]})
    assert first.history(session_id)
    assert first.cache_get("shared-query")["answer"] == "tenant-a"
    for isolated in (second, new_revision):
        assert isolated.history(session_id) == []
        assert isolated.cache_get("shared-query") is None
        assert isolated.candidates() == []


@pytest.mark.parametrize("decode_responses", [False, True])
def test_redis_candidates_handle_bytes_and_decoded_responses(decode_responses):
    client = fakeredis.FakeRedis(decode_responses=decode_responses)
    try:
        store = RedisStore(client, "demo")
        store.cache_set("query", {"answer": "safe", "vector": [0.0, 1.0]})
        assert store.candidates() == [{"answer": "safe", "vector": [0.0, 1.0]}]
    finally:
        client.close()


def test_redis_semantic_index_keeps_100_most_recent_and_skips_expired_values(
    redis_client, monkeypatch
):
    clock = iter(range(101))
    monkeypatch.setattr("app.services.store.time", lambda: float(next(clock)))
    store = RedisStore(redis_client, "demo", cache_ttl=30)
    for index in range(101):
        store.cache_set(str(index), {"order": index})
    candidates = store.candidates()
    assert [item["order"] for item in candidates] == list(range(100, 0, -1))
    index_key = store._key("cache_index", "recent")
    assert redis_client.zcard(index_key) == 100
    assert 0 < redis_client.ttl(index_key) <= 30
    redis_client.delete(store._key("cache", "100"))
    assert [item["order"] for item in store.candidates()] == list(range(99, 0, -1))


def test_redis_expired_session_and_response_are_unavailable(redis_client):
    store = RedisStore(redis_client, "demo")
    session_id = uuid4()
    store.append_turn(session_id, "safe", "answer")
    store.cache_set("query", {"answer": "safe"})
    redis_client.pexpire(store._key("session", str(session_id)), 1)
    redis_client.pexpire(store._key("cache", "query"), 1)
    sleep(0.02)
    assert store.history(session_id) == []
    assert store.cache_get("query") is None
    assert store.candidates() == []


def test_memory_expiration_and_history_refresh(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.services.store.time", lambda: now[0])
    store = MemoryStore(session_ttl=10, cache_ttl=5, max_messages=4)
    session_id = uuid4()
    store.append_turn(session_id, "first", "answer")
    store.cache_set("query", {"answer": "safe"})
    now[0] = 105.0
    assert store.cache_get("query") is None
    assert store.candidates() == []
    assert store.history(session_id)
    store.append_turn(session_id, "second", "answer")
    now[0] = 110.0
    assert store.history(session_id)
    now[0] = 115.0
    assert store.history(session_id) == []


def test_memory_key_bounds_and_message_cap(monkeypatch):
    monkeypatch.setattr("app.services.store.time", lambda: 100.0)
    store = MemoryStore(max_messages=4, max_keys=2)
    sessions = [uuid4() for _ in range(3)]
    for index, session_id in enumerate(sessions):
        store.append_turn(session_id, f"user-{index}", f"assistant-{index}")
        store.cache_set(str(index), {"index": index})
    assert store.history(sessions[0]) == []
    assert store.cache_get("0") is None
    assert store.candidates() == [{"index": 1}, {"index": 2}]
    store.append_turn(sessions[-1], "user-3", "assistant-3")
    store.append_turn(sessions[-1], "user-4", "assistant-4")
    assert [item.content for item in store.history(sessions[-1])] == [
        "user-3",
        "assistant-3",
        "user-4",
        "assistant-4",
    ]


def test_exact_cache_key_preserves_negation_and_numbers():
    assert cache_key("  Fatura  ") == cache_key("Fatura")
    assert cache_key("Fatura") != cache_key("fatura")
    assert cache_key("100 Mbps") != cache_key("200 Mbps")
    assert cache_key("internet var") != cache_key("internet yok")


def test_memory_store_does_not_expose_mutable_history_or_cache_values():
    store = MemoryStore()
    session_id = uuid4()
    store.append_turn(session_id, "safe user", "approved answer")
    store.history(session_id)[0].content = "mutated outside store"
    assert store.history(session_id)[0].content == "safe user"
    value = {"source": {"entry_id": "approved"}, "vector": [1.0, 0.0]}
    store.cache_set("query", value)
    value["source"]["entry_id"] = "caller mutation"
    first_read = store.cache_get("query")
    first_read["source"]["entry_id"] = "reader mutation"
    store.candidates()[0]["vector"][0] = 9.0
    assert store.cache_get("query") == {"source": {"entry_id": "approved"}, "vector": [1.0, 0.0]}
