from PySide6.QtCore import QObject, Signal, Slot, Qt


class UpdateBridge(QObject):
    received = Signal(dict)

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self.received.connect(self._deliver, Qt.QueuedConnection)

    @Slot(dict)
    def _deliver(self, result):
        self._callback(result)
