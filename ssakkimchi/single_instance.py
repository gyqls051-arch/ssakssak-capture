from typing import Callable, Optional

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket


INSTANCE_KEY = "SSAKKIMCHI_CAPTURE_SINGLE_INSTANCE_v1"
HANDSHAKE_TIMEOUT_MS = 800
RETRY_COUNT = 3


def already_running() -> bool:
    for _ in range(RETRY_COUNT):
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_KEY)
        if socket.waitForConnected(HANDSHAKE_TIMEOUT_MS):
            try:
                socket.write(b"show")
                socket.flush()
                socket.waitForBytesWritten(HANDSHAKE_TIMEOUT_MS)
            finally:
                socket.disconnectFromServer()
            return True
    return False


class InstanceServer(QObject):
    def __init__(self, on_message: Callable[[str], None]) -> None:
        super().__init__()
        self._on_message = on_message
        QLocalServer.removeServer(INSTANCE_KEY)
        self._server = QLocalServer(self)
        self._server.listen(INSTANCE_KEY)
        self._server.newConnection.connect(self._on_new_connection)

    def _on_new_connection(self) -> None:
        conn: Optional[QLocalSocket] = self._server.nextPendingConnection()
        if conn is None:
            return
        if conn.waitForReadyRead(HANDSHAKE_TIMEOUT_MS):
            try:
                data = bytes(conn.readAll()).decode("utf-8", errors="ignore")
            except Exception:
                data = ""
            self._on_message(data)
        conn.disconnectFromServer()
