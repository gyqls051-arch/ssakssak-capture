import sys
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, QThread
from ssakkimchi.update_bridge import UpdateBridge


def test_worker_result_delivered_on_gui_thread():
    app = QCoreApplication.instance() or QCoreApplication([])
    received = []
    def callback(result):
        assert QThread.currentThread() == app.thread()
        received.append(result)
    bridge = UpdateBridge(callback)
    worker = threading.Thread(target=lambda: bridge.received.emit({"kind": "new_version"}))
    worker.start()
    worker.join()
    until = time.monotonic() + 1
    while not received and time.monotonic() < until:
        app.processEvents()
        time.sleep(.005)
    assert received == [{"kind": "new_version"}]
