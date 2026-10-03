"""
Unit tests for Single-Instance application enforcement in app.py.
"""

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from app import SINGLE_INSTANCE_KEY, ensure_single_instance


def test_ensure_single_instance_first_and_second():
    app = QApplication.instance() or QApplication([])

    # Clean up any leftover server key before test
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)

    # 1. First instance check -> should return True and a listening QLocalServer
    is_first, server = ensure_single_instance()
    assert is_first is True
    assert server is not None
    assert server.isListening()

    # 2. Second instance check -> should detect running server, send activation, and return False
    is_second, server_second = ensure_single_instance()
    assert is_second is False
    assert server_second is None

    # Clean up
    server.close()
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
