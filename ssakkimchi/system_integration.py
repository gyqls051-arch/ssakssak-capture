"""Windows PrtSc 가로채기 자동 설정.

Windows 11(과 일부 10 버전)은 PrtSc를 누르면 Snipping Tool을 띄우는 게 기본.
HKCU\\Control Panel\\Keyboard\\PrintScreenKeyForSnippingEnabled = 0 으로 두면 OS가
PrtSc 라우팅을 안 해서 우리 글로벌 핫키가 받을 수 있다.

- HKCU 라 UAC 불필요
- 적용을 즉시 보장하려면 explorer.exe 재시작이 필요할 수도 있지만, Win11 최신
  빌드에서는 즉시 적용되는 케이스가 많다. 본 모듈은 explorer를 안 건드린다 -
  거슬리기 때문. 사용자에게 재로그인을 권장하는 것은 호출 측의 몫.
"""
from __future__ import annotations

import sys
import winreg
from typing import Optional


_KEY_PATH = r"Control Panel\Keyboard"
_VALUE_NAME = "PrintScreenKeyForSnippingEnabled"


def get_prtsc_routes_to_snipping() -> Optional[bool]:
    """True=Snipping Tool로 라우팅됨, False=안 됨, None=Windows 아님/읽기 실패."""
    if sys.platform != "win32":
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_READ) as k:
            try:
                value, _ = winreg.QueryValueEx(k, _VALUE_NAME)
                return bool(value)
            except FileNotFoundError:
                return True
    except OSError:
        return None


def disable_snipping_route() -> bool:
    """PrtSc → Snipping 라우팅을 끈다. 성공 True."""
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, _VALUE_NAME, 0, winreg.REG_DWORD, 0)
        return True
    except OSError:
        return False


def enable_snipping_route() -> bool:
    """원상복귀: PrtSc → Snipping Tool. 사용자가 우리 앱 빼고 싶을 때."""
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, _VALUE_NAME, 0, winreg.REG_DWORD, 1)
        return True
    except OSError:
        return False


def read_snipping_route_raw() -> Optional[int]:
    """앱 시작 시 '원래 값'을 그대로 보존해 두기 위한 raw 읽기.

    반환:
      - int: 레지스트리에 있던 DWORD 원본 값 (보통 0 또는 1)
      - None: 값이 없음(=OS 기본값 사용 상태) / Windows 아님 / 읽기 실패

    None과 0/1을 구분해서 저장해 두면 종료 시 '원래 없던 값을 우리가
    만들어 두는' 부작용 없이 정확히 복원할 수 있다."""
    if sys.platform != "win32":
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_READ) as k:
            try:
                value, _ = winreg.QueryValueEx(k, _VALUE_NAME)
                return int(value)
            except FileNotFoundError:
                return None
    except OSError:
        return None


def restore_snipping_route(original: Optional[int]) -> bool:
    """앱 시작 시 read_snipping_route_raw()로 저장해 둔 원래 값으로 복원.

    - original is None: 원래 값이 아예 없었으므로 우리가 만든 값을 삭제해
      OS 기본 상태로 되돌린다.
    - original is int: 그 값(0/1)을 그대로 다시 써넣는다.

    비정상 종료 보완용 안전망의 핵심 함수. 성공/이미 정상이면 True."""
    if sys.platform != "win32":
        return False
    try:
        if original is None:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE
                ) as k:
                    winreg.DeleteValue(k, _VALUE_NAME)
            except FileNotFoundError:
                pass  # 이미 없으면 그게 곧 복원 완료 상태
            return True
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, _VALUE_NAME, 0, winreg.REG_DWORD, int(original))
        return True
    except OSError:
        return False
