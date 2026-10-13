from uuid import uuid4

from app.models.schemas import ChatResponse
from app.services.telemetry import Telemetry


def test_langfuse_receives_only_operational_metadata():
    captured = []

    class Span:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Client:
        def start_as_current_observation(self, **kwargs):
            captured.append(kwargs)
            return Span()

        def flush(self):
            captured.append("flush")

    telemetry = Telemetry()
    telemetry._client = Client()
    response = ChatResponse(
        answer="private response", safe_message="private prompt", session_id=uuid4()
    )
    telemetry.record(response)
    telemetry.close()
    serialized = str(captured)
    assert "private response" not in serialized and "private prompt" not in serialized
    assert str(response.session_id) not in serialized
    assert captured[0]["trace_context"]["trace_id"] == response.trace_id.hex
    assert captured[-1] == "flush"
