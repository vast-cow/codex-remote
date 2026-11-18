# Codex Remote Control Setup

Connect to an existing Codex App Server, enable Remote Control, and pair it
using the manual code shown by the script.

## Prerequisites

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Have a running Codex App Server that supports Remote Control and manual
  pairing, and access to the ChatGPT Remote screen to enter the code.
- Internet access on the first run to download dependencies and, if needed,
  a compatible Python interpreter (Python 3.9 or newer).

## Run

From this directory:

```bash
uv run main.py
```

uv reads the inline metadata in `main.py` and automatically manages Python and
the `websockets>=13` dependency. No manual pip installation or virtual environment
setup is needed. Enter the displayed pairing code on the ChatGPT Remote screen.

## Optional environment variables

- `CODEX_APP_SERVER_URL`: Set a WebSocket endpoint (`ws://host:port` or
  `wss://host:port`), an explicit Unix socket (`unix:///path/to/socket`), or
  `unix://` to use the default Unix socket. When unset, the script first tries
  `ws://127.0.0.1:4500`, then the default Unix socket.
- `CODEX_HOME`: Base directory for the default Unix socket,
  `$CODEX_HOME/app-server-control/app-server-control.sock`. Defaults to
  `~/.codex`. Unix sockets require a platform that supports them.

For example:

```bash
CODEX_APP_SERVER_URL=ws://127.0.0.1:4500 uv run main.py
```

If no App Server is reachable, the script reports a connection error after
startup; dependency installation alone does not verify Remote Control pairing.
