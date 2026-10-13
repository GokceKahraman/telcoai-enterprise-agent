"""Regenerate checked-in stubs using the locked grpcio-tools dependency."""

from pathlib import Path

from grpc_tools import protoc

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "grpc" / "generated"


def main() -> None:
    code = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{ROOT / 'proto'}",
            f"--python_out={OUT}",
            f"--grpc_python_out={OUT}",
            str(ROOT / "proto" / "telcoai.proto"),
        ]
    )
    if code:
        raise SystemExit(code)
    stub = OUT / "telcoai_pb2_grpc.py"
    text = stub.read_text().replace(
        "import telcoai_pb2 as telcoai__pb2", "from . import telcoai_pb2 as telcoai__pb2"
    )
    stub.write_text(text)


if __name__ == "__main__":
    main()
