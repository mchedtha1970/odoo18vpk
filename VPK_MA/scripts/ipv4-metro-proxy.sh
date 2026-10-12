#!/usr/bin/env bash
# Bridge Expo Go (127.0.0.1) -> Metro (::1) on macOS IPv6-only localhost.
set -euo pipefail
PORT="${1:-8081}"

python3 - "$PORT" <<'PY'
import socket, threading, sys
port = int(sys.argv[1])

def pipe(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except Exception:
        pass
    finally:
        for s in (a, b):
            try: s.shutdown(socket.SHUT_RDWR)
            except Exception: pass

def handle(client):
    up = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        up.connect(("::1", port))
    except Exception as e:
        print("upstream failed:", e, flush=True)
        client.close()
        return
    threading.Thread(target=pipe, args=(client, up), daemon=True).start()
    pipe(up, client)
    client.close(); up.close()

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port))
srv.listen(100)
print(f"ipv4-proxy 127.0.0.1:{port} -> [::1]:{port}", flush=True)
while True:
    c, _ = srv.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
PY
