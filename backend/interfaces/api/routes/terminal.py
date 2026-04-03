"""WebSocket terminal — spawns a PTY shell on the server and relays it to the browser.

Auth: JWT passed as query param `?token=<jwt>` (browsers cannot set custom headers
on WebSocket connections). Any authenticated user may access the terminal.

Protocol:
  - Client sends raw text/bytes  → written to PTY stdin
  - Client sends JSON {"type": "resize", "cols": N, "rows": N}  → resize PTY
  - Server sends raw bytes  → PTY stdout/stderr output
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import subprocess
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.config.settings import get_settings
from backend.domain.services.auth_service import (
    AuthService,
    InvalidTokenError,
    TokenPayload,
)
from backend.infra.database.repositories.user_repository import UserRepository
from backend.interfaces.api.dependencies import _get_session_factory

router = APIRouter(tags=["terminal"])
logger = logging.getLogger(__name__)

_SHELL = os.environ.get("SHELL", "/bin/bash")


def _decode_token(token: str) -> TokenPayload:
    """Verify JWT and return the decoded payload."""
    if not token:
        raise ValueError("token required")
    settings = get_settings()
    session = _get_session_factory()()
    try:
        repo = UserRepository(session)
        auth_svc = AuthService(
            user_repo=repo,
            jwt_secret=settings.jwt_secret,
            jwt_expire_hours=settings.jwt_expire_hours,
        )
        return auth_svc.decode_token(token)
    except InvalidTokenError as exc:
        raise ValueError(str(exc)) from exc
    finally:
        session.close()


def _resize_pty(fd: int, rows: int, cols: int) -> None:
    """Send TIOCSWINSZ to update terminal size."""
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


def _read_from_pty(fd: int) -> bytes | None:
    """Blocking read from PTY master. Returns None on EOF/error."""
    try:
        return os.read(fd, 4096)
    except OSError:
        return None


@router.websocket("/terminal")
async def terminal_ws(websocket: WebSocket, token: str = "") -> None:
    """Spawn a PTY shell and relay I/O over WebSocket."""
    # --- Auth before accept ---
    try:
        payload = _decode_token(token)
    except ValueError as exc:
        await websocket.close(code=4001, reason=str(exc))
        return

    await websocket.accept()
    username = payload.username
    logger.info("terminal: session opened by user=%s", username)

    # --- Spawn shell in a PTY ---
    master_fd, slave_fd = pty.openpty()
    _resize_pty(master_fd, rows=24, cols=80)  # initial size

    # Per-user AWS credential isolation
    import shutil

    aws_user_dir = os.path.expanduser(f"~/.aws/users/{username}")
    os.makedirs(aws_user_dir, exist_ok=True)

    _template = os.path.expanduser("~/.aws/aws-config.template")
    _system_config = os.path.expanduser("~/.aws/config")
    _user_config = f"{aws_user_dir}/config"
    _source = (
        _template
        if os.path.exists(_template)
        else (_system_config if os.path.exists(_system_config) else None)
    )

    if _source:
        # Always keep per-user config in sync with the source (template or system).
        # This keeps each user terminal profile baseline aligned with admin config.
        # If the user has personalised their config (mtime newer than source) keep it.
        _should_copy = not os.path.exists(_user_config)
        if not _should_copy and os.path.exists(_user_config):
            source_mtime = os.path.getmtime(_source)
            user_mtime = os.path.getmtime(_user_config)
            # Re-copy only when the source changed after the user config was last written,
            # meaning an admin updated the template but the user config is stale.
            _should_copy = source_mtime > user_mtime
        if _should_copy:
            shutil.copy(_source, _user_config)
            label = "template" if _source == _template else "system config"
            logger.info("terminal: synced aws %s to user=%s", label, username)

    env = os.environ.copy()
    env["AWS_CONFIG_FILE"] = _user_config
    # SSO cache intentionally NOT overridden — keeps shared at ~/.aws/sso/cache
    # so tokens from terminal login are also readable by the app's boto3 sessions
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("COLORTERM", "truecolor")

    # Each user gets their own workspace directory so the shell starts
    # in a clean place, not the backend project root.
    workspace = os.path.expanduser(f"~/terminal-workspace/{username}")
    _first_session = not os.path.exists(workspace)
    os.makedirs(workspace, exist_ok=True)

    proc = subprocess.Popen(
        [_SHELL, "-l"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        preexec_fn=os.setsid,
        env=env,
        cwd=workspace,
    )
    os.close(slave_fd)  # parent doesn't need the slave end

    loop = asyncio.get_event_loop()

    # --- Task: PTY output → WebSocket ---
    async def _pty_to_ws() -> None:
        try:
            while True:
                data = await loop.run_in_executor(None, _read_from_pty, master_fd)
                if data is None:
                    break
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_bytes(data)
        except Exception:
            pass

    reader = asyncio.create_task(_pty_to_ws())

    # --- Notify frontend of first-session (triggers LoginHint auto-expand) ---
    if _first_session:
        try:
            await websocket.send_text(json.dumps({"type": "first_session"}))
        except Exception:
            pass

    # --- Main loop: WebSocket input → PTY ---
    try:
        while True:
            msg = await websocket.receive()

            if msg["type"] == "websocket.disconnect":
                break

            if "text" in msg and msg["text"]:
                text = msg["text"]
                # Resize control message
                try:
                    parsed = json.loads(text)
                    if parsed.get("type") == "resize":
                        cols = max(1, int(parsed.get("cols", 80)))
                        rows = max(1, int(parsed.get("rows", 24)))
                        _resize_pty(master_fd, rows, cols)
                        continue
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
                # Regular keystroke
                os.write(master_fd, text.encode("utf-8", errors="replace"))

            elif "bytes" in msg and msg["bytes"]:
                os.write(master_fd, msg["bytes"])

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("terminal: unexpected error: %s", exc)
    finally:
        reader.cancel()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        try:
            os.close(master_fd)
        except OSError:
            pass
        logger.info("terminal: session closed (pid=%s)", proc.pid)
