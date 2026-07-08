"""Windows 셸 연동 헬퍼."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def reveal_in_explorer(file_path: Path) -> None:
    """탐색기에서 파일을 선택된 상태로 표시. 실패 시 폴더만 연다.

    `/select,경로`는 반드시 한 인자로 붙여야 한다 — 콤마와 경로를
    분리하면 일부 환경에서 파일 선택이 무시되고 폴더만 열린다.
    """
    file_path = Path(file_path)
    if sys.platform != "win32" or not file_path.exists():
        return
    try:
        subprocess.Popen(
            ["explorer", f"/select,{file_path}"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        try:
            os.startfile(str(file_path.parent))
        except Exception:
            pass
