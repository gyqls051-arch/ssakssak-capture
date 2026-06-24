from typing import Dict, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .actions import action_labels, default_hotkeys
from .hotkeys import HotkeyTester, pynput_to_qt, qt_to_pynput
from .tokens import COLORS, FONT_FAMILY


ACTION_LABELS: List[Tuple[str, str]] = action_labels()


class _Row(QWidget):
    def __init__(self, label: str, qt_seq: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        name = QLabel(label)
        name.setFixedWidth(96)
        name.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(name)

        self.edit = QKeySequenceEdit()
        self.edit.setKeySequence(QKeySequence(qt_seq))
        self.edit.setMaximumSequenceLength(1)
        self.edit.setStyleSheet(
            f"""
            QKeySequenceEdit {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: {FONT_FAMILY};
                font-size: 13px;
                color: {COLORS['text_primary']};
                min-height: 22px;
            }}
            QKeySequenceEdit:focus {{
                border: 1px solid #06B6D4;
            }}
            """
        )
        layout.addWidget(self.edit, 1)

        small_btn_css = f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border_solid']};
                border-radius: 6px;
                color: {COLORS['text_secondary']};
                font-size: 12px;
                padding: 4px 0;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
            }}
            QPushButton:disabled {{
                color: {COLORS['text_tertiary']};
            }}
        """

        self.test_btn = QPushButton("테스트")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.setFixedWidth(58)
        self.test_btn.setStyleSheet(small_btn_css)
        self.test_btn.setToolTip("5초 안에 이 키를 눌러 동작 확인")
        layout.addWidget(self.test_btn)

        self.status = QLabel("")
        self.status.setFixedWidth(20)
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        layout.addWidget(self.status)

        clear = QPushButton("지우기")
        clear.setCursor(Qt.PointingHandCursor)
        clear.setFixedWidth(58)
        clear.setStyleSheet(small_btn_css)
        clear.clicked.connect(self.edit.clear)
        layout.addWidget(clear)

        self._tester = None
        self.test_btn.clicked.connect(self._run_test)

    def qt_value(self) -> str:
        return self.edit.keySequence().toString(QKeySequence.PortableText)

    def _run_test(self) -> None:
        combo = qt_to_pynput(self.qt_value())
        if not combo:
            self.status.setText("·")
            self.status.setStyleSheet("color: #94A3B8; font-size: 14px;")
            self.status.setToolTip("키가 비어있음")
            return
        self.test_btn.setEnabled(False)
        self.test_btn.setText("…")
        self.status.setText("")
        self.status.setToolTip("5초 동안 이 단축키를 눌러보세요")
        self._tester = HotkeyTester(combo, timeout_ms=5000)
        self._tester.result.connect(self._on_test_result)
        if not self._tester.start():
            self._on_test_result(False)

    def _on_test_result(self, ok: bool) -> None:
        self.test_btn.setEnabled(True)
        self.test_btn.setText("테스트")
        if ok:
            self.status.setText("✓")
            self.status.setStyleSheet("color: #10B981; font-size: 14px; font-weight: 700;")
            self.status.setToolTip("정상 작동")
        else:
            self.status.setText("✗")
            self.status.setStyleSheet("color: #EF4444; font-size: 14px; font-weight: 700;")
            self.status.setToolTip("5초 안에 키 입력 못 받음 — 다른 앱과 충돌 가능")
        self._tester = None


class HotkeyDialog(QDialog):
    def __init__(self, current: Dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("단축키 설정")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(440)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS['bg_primary']};
                font-family: {FONT_FAMILY};
            }}
            QLabel#hint {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
            QDialogButtonBox QPushButton {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_solid']};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                color: {COLORS['text_primary']};
                min-width: 64px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: {COLORS['bg_secondary']};
            }}
            QDialogButtonBox QPushButton:default {{
                background: #06B6D4;
                color: white;
                border: 1px solid #06B6D4;
            }}
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(10)

        hint = QLabel(
            "입력란을 클릭하고 원하는 키를 누르세요 (Ctrl, Shift, Alt 조합 가능).\n"
            "[테스트]를 누르면 5초 동안 그 키 입력을 받아 동작 여부 확인합니다."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self._rows: Dict[str, _Row] = {}
        for action, label in ACTION_LABELS:
            qt_seq = pynput_to_qt(current.get(action, ""))
            row = _Row(label, qt_seq)
            self._rows[action] = row
            outer.addWidget(row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLORS['border_solid']};")
        outer.addWidget(sep)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Reset | QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("저장")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
        buttons.button(QDialogButtonBox.Reset).setText("기본값으로 초기화")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self._reset_defaults)
        outer.addWidget(buttons)

    def _reset_defaults(self) -> None:
        confirm = QMessageBox.question(
            self,
            "단축키 초기화",
            "모든 단축키를 기본값(Alt+숫자)으로 되돌릴까요?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        defaults = default_hotkeys()
        for action, row in self._rows.items():
            qt_seq = pynput_to_qt(defaults.get(action, ""))
            row.edit.setKeySequence(QKeySequence(qt_seq))

    def _on_accept(self) -> None:
        bindings = self._collect_bindings()
        conflicts = self._find_conflicts(bindings)
        if conflicts:
            lines = [
                f"• {' / '.join(self._label_for(a) for a in actions)} → {pynput_to_qt(combo)}"
                for combo, actions in conflicts.items()
            ]
            QMessageBox.warning(
                self,
                "단축키 충돌",
                "같은 키 조합이 여러 도구에 지정되어 있어요:\n\n"
                + "\n".join(lines)
                + "\n\n하나만 남기고 비워주세요.",
            )
            return
        self._final_bindings = bindings
        self.accept()

    def _collect_bindings(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for action, row in self._rows.items():
            out[action] = qt_to_pynput(row.qt_value())
        return out

    @staticmethod
    def _find_conflicts(bindings: Dict[str, str]) -> Dict[str, List[str]]:
        seen: Dict[str, List[str]] = {}
        for action, combo in bindings.items():
            if not combo:
                continue
            seen.setdefault(combo, []).append(action)
        return {c: actions for c, actions in seen.items() if len(actions) > 1}

    @staticmethod
    def _label_for(action: str) -> str:
        for key, label in ACTION_LABELS:
            if key == action:
                return label
        return action

    def result_bindings(self) -> Dict[str, str]:
        if hasattr(self, "_final_bindings"):
            return self._final_bindings
        return self._collect_bindings()
