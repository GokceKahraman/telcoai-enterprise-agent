"""Run with python -m app.grpc.server. Same validation, masking and auth as HTTP."""

import sys
from concurrent import futures
from secrets import compare_digest

import grpc
from loguru import logger
from pydantic import ValidationError

from app.config import get_settings
from app.grpc.generated import telcoai_pb2, telcoai_pb2_grpc
from app.models.schemas import ChatRequest
from app.runtime import build_runtime


class SupportServicer(telcoai_pb2_grpc.SupportServiceServicer):
    def __init__(self, runtime) -> None:
        self.runtime = runtime

    def Chat(self, request, context):
        key = self.runtime.settings.api_key
        auth = dict(context.invocation_metadata()).get("authorization", "")
        if key and not compare_digest(auth, f"Bearer {key.get_secret_value()}"):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "API access token required")
        try:
            payload = ChatRequest(
                message=request.message,
                session_id=request.session_id or None,
                category=request.category or None,
            )
        except ValidationError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid message or session UUID")
        try:
            response = self.runtime.service.reply(
                payload.message, payload.session_id, payload.category
            )
        except Exception as exc:
            logger.bind(error_type=type(exc).__name__).error("grpc_request_failed")
            context.abort(grpc.StatusCode.UNAVAILABLE, "Support service temporarily unavailable")
        result = telcoai_pb2.ChatResponse(
            answer=response.answer,
            fallback=response.fallback,
            session_id=str(response.session_id),
            trace_id=str(response.trace_id),
            intent=response.intent,
            handoff=response.handoff,
            pii_redacted=response.pii_redacted,
            cache_hit=response.cache_hit,
            latency_ms=response.latency_ms,
            steps=response.steps,
            safe_message=response.safe_message,
        )
        if response.source is not None:
            result.source.CopyFrom(telcoai_pb2.SourceInfo(**response.source.model_dump()))
        return result


def make_server(runtime, address: str):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=8),
        options=[("grpc.max_receive_message_length", 16384)],
    )
    telcoai_pb2_grpc.add_SupportServiceServicer_to_server(SupportServicer(runtime), server)
    port = server.add_insecure_port(address)
    if port == 0:
        raise RuntimeError("gRPC port could not be bound")
    return server, port


def main() -> None:
    settings = get_settings()
    try:
        logger.remove(0)
    except ValueError:
        pass
    sink = logger.add(sys.stderr, serialize=True, enqueue=True, backtrace=False, diagnose=False)
    runtime = build_runtime(settings)
    server, _ = make_server(runtime, f"{settings.grpc_host}:{settings.grpc_port}")
    server.start()
    logger.info("grpc_server_started")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=5).wait()
    finally:
        runtime.close()
        logger.complete()
        logger.remove(sink)


if __name__ == "__main__":
    main()
