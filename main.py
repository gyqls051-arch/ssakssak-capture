import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from ssakkimchi.app import SsakKimchiApp
from ssakkimchi.logging_setup import get_logger, setup_logging
from ssakkimchi.single_instance import InstanceServer, already_running
from ssakkimchi.version import version_string


def main():
    setup_logging()
    log = get_logger("main")
    log.info("=== %s starting ===", version_string())

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("싹싹김치 캡처")
    app.setApplicationDisplayName("싹싹김치 캡처")
    app.setQuitOnLastWindowClosed(False)

    if already_running():
        log.info("already running, bringing existing instance to front")
        sys.exit(0)

    try:
        ssakkimchi = SsakKimchiApp()
    except Exception:
        log.exception("SsakKimchiApp init failed")
        raise

    # 이벤트 루프 종료 직전에도 PrtSc 레지스트리 안전망 복원을 보장.
    # (OS 로그오프 등으로 quit()을 안 거치고 app이 내려가는 경로 대비)
    app.aboutToQuit.connect(ssakkimchi._restore_prtsc_on_exit)

    def handle_other_launch(_message: str) -> None:
        ssakkimchi.bring_to_front()

    _server = InstanceServer(handle_other_launch)

    try:
        ssakkimchi.start()
    except Exception:
        log.exception("SsakKimchiApp.start() failed")
        raise

    log.info("entering event loop")
    rc = app.exec()
    log.info("event loop exited with %s", rc)
    sys.exit(rc)


if __name__ == "__main__":
    main()
