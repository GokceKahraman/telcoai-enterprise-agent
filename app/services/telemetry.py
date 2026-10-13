"""Only operational metadata leaves the process; no chat text or session IDs."""

from loguru import logger


class Telemetry:
    def __init__(self, enabled: bool = False) -> None:
        self._client = None
        if enabled:
            import os

            from langfuse import get_client

            if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
                raise ValueError("Langfuse enabled but keys are missing")
            self._client = get_client()

    def record(self, response) -> None:
        metadata = {
            "trace_id": str(response.trace_id),
            "intent": response.intent,
            "fallback": response.fallback,
            "handoff": response.handoff,
            "pii_redacted": response.pii_redacted,
            "cache_hit": response.cache_hit,
            "latency_ms": response.latency_ms,
            "steps": response.steps,
            "source_id": response.source.entry_id if response.source else None,
        }
        logger.bind(**metadata).info("support_turn_completed")
        if self._client is None:
            return
        try:
            with self._client.start_as_current_observation(
                name="telcoai.support",
                as_type="span",
                metadata=metadata,
                trace_context={"trace_id": response.trace_id.hex},
            ):
                pass
        except Exception:
            logger.warning("telemetry_export_failed")

    def close(self) -> None:
        if self._client is not None:
            self._client.flush()
