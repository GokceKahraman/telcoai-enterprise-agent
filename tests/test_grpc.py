import grpc
import pytest

from app.config import Settings
from app.grpc.generated import telcoai_pb2, telcoai_pb2_grpc
from app.grpc.server import make_server
from app.runtime import build_runtime


@pytest.fixture
def rpc_client():
    runtime = build_runtime(Settings(api_key="test-token"))
    server, port = make_server(runtime, "127.0.0.1:0")
    server.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = telcoai_pb2_grpc.SupportServiceStub(channel)
    yield stub
    channel.close()
    server.stop(0).wait()
    runtime.close()


def test_grpc_roundtrip_same_source_and_privacy(rpc_client):
    response = rpc_client.Chat(
        telcoai_pb2.ChatRequest(message="Faturamı nereden ödeyebilirim? test@example.com"),
        metadata=[("authorization", "Bearer test-token")],
        timeout=10,
    )
    assert response.source.entry_id == "bill-001"
    assert response.pii_redacted
    assert "test@example.com" not in response.safe_message
    assert response.session_id and response.trace_id


def test_grpc_auth_and_validation(rpc_client):
    with pytest.raises(grpc.RpcError) as error:
        rpc_client.Chat(telcoai_pb2.ChatRequest(message="fatura"), timeout=10)
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED
    with pytest.raises(grpc.RpcError) as error:
        rpc_client.Chat(
            telcoai_pb2.ChatRequest(message="fatura", session_id="test@example.com"),
            metadata=[("authorization", "Bearer test-token")],
            timeout=10,
        )
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "test@example.com" not in error.value.details()
