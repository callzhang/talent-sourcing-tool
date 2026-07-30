from __future__ import annotations

import socket
import sys


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(
    preferred_port: int,
    *,
    host: str = "127.0.0.1",
    max_tries: int = 100,
) -> int:
    for port in range(preferred_port, preferred_port + max_tries):
        if is_port_available(port, host=host):
            return port
    raise RuntimeError(
        f"No available port found from {preferred_port} to {preferred_port + max_tries - 1} on {host}."
    )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) not in {1, 2}:
        print("Usage: python scripts/port_utils.py <preferred_port> [host]", file=sys.stderr)
        return 2
    preferred_port = int(args[0])
    host = args[1] if len(args) == 2 else "127.0.0.1"
    print(find_available_port(preferred_port, host=host))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
