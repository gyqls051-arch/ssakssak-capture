"""싹싹김치 캡처 — 배포용 패키징 한 방 스크립트.

1) bin/ffmpeg.exe 확보 (이미 있으면 skip / 시스템 PATH에서 복사 / 마지막엔 다운로드)
2) pyinstaller build.spec 실행
3) dist/싹싹김치 캡처/ 폴더에 README.txt 한 장 넣기
4) dist/싹싹김치 캡처.zip 으로 압축

실행: 프로젝트 루트에서 `python tools/package.py`  또는 `package.bat` 더블클릭.
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "bin"
FFMPEG_PATH = BIN_DIR / "ffmpeg.exe"
DIST_ROOT = ROOT / "dist"
APP_FOLDER_NAME = "싹싹김치 캡처"
APP_FOLDER = DIST_ROOT / APP_FOLDER_NAME
README_PATH = APP_FOLDER / "README.txt"
ZIP_PATH = DIST_ROOT / f"{APP_FOLDER_NAME}.zip"
ISS_PATH = ROOT / "tools" / "installer.iss"

_ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
    Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
]

# LGPL 빌드 (NVENC/QSV/AMF HW 인코더 포함, libx264/x265 등 GPL 컴포넌트 제외)
# 본 앱은 MIT 라이선스이므로 GPL 컴포넌트를 번들하지 않도록 LGPL 빌드를 사용.
#
# [무결성 / 재현성]
# 'latest' 롤링 태그는 매 빌드마다 내용이 바뀌어(=같은 URL인데 바이트가 달라짐)
# 빌드가 재현되지 않고, 중간자 공격/손상 탐지도 불가능하다. 그래서:
#   1) 다운로드할 릴리스를 날짜 태그로 고정한다(FFMPEG_RELEASE_TAG).
#      BtbN/FFmpeg-Builds 는 'autobuild-YYYY-MM-DD-HH-MM' 형식의 불변 태그를 제공.
#      Releases 페이지에서 원하는 빌드의 태그를 골라 아래 상수에 넣으면 된다.
#   2) 받은 zip의 SHA256을 알려진 해시와 비교한다(FFMPEG_SHA256).
#      해시를 모르면 비워 두면 검증을 건너뛰되 경고를 출력한다.
#
# ── 해시 채우는 법 ───────────────────────────────────────────────
#   a) 한 번 그냥 빌드해서 받은 zip의 해시를 확인:
#        certutil -hashfile <받은zip경로> SHA256        (PowerShell/cmd)
#      또는 이 스크립트가 다운로드 직후 출력하는 "downloaded sha256: ..." 줄을 본다.
#   b) 그 값(64자리 16진수)을 FFMPEG_SHA256 에 붙여넣는다.
#   c) 신뢰성을 더 높이려면 BtbN 릴리스의 *.zip.sha256 자산값과 대조한다.
# ─────────────────────────────────────────────────────────────────
#
# 고정 태그. 'latest' 로 두면 (구버전 호환) 롤링 빌드를 받지만 재현성이 없다.
# 예: "autobuild-2024-12-01-12-31". 비워 두지 말고 실제 태그로 채우는 것을 권장.
FFMPEG_RELEASE_TAG = "latest"

# 위 태그로 받은 zip의 기대 SHA256 (소문자 64hex). 비우면 검증 skip(경고 출력).
# 'latest' 태그를 쓰는 동안에는 내용이 계속 바뀌므로 해시 고정이 사실상 불가능 →
# 재현 가능한 검증을 원하면 반드시 FFMPEG_RELEASE_TAG 를 날짜 태그로 고정할 것.
FFMPEG_SHA256 = ""

FFMPEG_RELEASE_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    f"{FFMPEG_RELEASE_TAG}/ffmpeg-master-latest-win64-lgpl.zip"
)


README_TEMPLATE = """싹싹김치 캡처 - 사용 안내
=========================

[설치 / 실행]
1. 압축을 원하는 위치에 풀어주세요 (예: C:\\Program Files\\싹싹김치 캡처\\).
2. 폴더 안의 "싹싹김치 캡처.exe"를 더블클릭하세요.
3. 처음 실행 시 Windows Defender SmartScreen 경고가 뜰 수 있어요.
   "추가 정보" → "실행" 을 누르면 됩니다 (코드 서명이 안 된 일반 앱은 누구나 이 단계가 있어요).

[사용법]
- 화면 가장자리에 도크가 떠요. 아이콘 클릭으로 캡처.
- 도크 손잡이(점 6개) 우클릭 → 단축키 설정 / 저장 경로 변경 / 정보 / 종료.

[기본 단축키] (왼손 한 손으로 OK)
  Alt+1  부분 캡처
  Alt+2  전체 캡처
  Alt+3  창 캡처
  Alt+4  스크롤 캡처
  Alt+5  색 추출
  Alt+6  거리 측정
  Alt+7  OCR
  Alt+8  화면 녹화 (시작/정지)
  Alt+9  GIF 녹화 (시작/정지)

[캡처 저장 위치]
- 기본: C:\\Users\\<사용자>\\.ssakkimchi\\captures\\
- 도크 우클릭 → "캡처 저장 경로 변경..." 에서 변경 가능.

[트러블슈팅]
- 도크가 안 보임: 트레이 아이콘(우측 하단) 더블클릭, 또는 다시 exe 실행.
- 단축키가 안 먹음: 다른 앱(게임/캡처도구/마우스 유틸)과 충돌일 수 있어요.
   도크 우클릭 → 단축키 설정 → [테스트] 버튼으로 확인 후 다른 키로 변경.
- 부분캡처가 안 됨: 마우스가 있는 모니터 한 화면만 덮어요 (모니터 경계 가로지르는 캡처 불가).
- 녹화가 비정상 종료됨: ffmpeg 문제. 도크 우클릭 → "정보 / 진단..." 에서 정보 확인.
- 진단 정보가 필요해요: 도크 우클릭 → "정보 / 진단..." → [진단 정보 복사] 또는 [로그 폴더 열기]
   로그 위치: C:\\Users\\<사용자>\\.ssakkimchi\\logs\\ssakkimchi.log

[제거]
- 폴더 통째로 삭제. 사용자 데이터는 C:\\Users\\<사용자>\\.ssakkimchi\\ 폴더 (수동 삭제).
- PrtSc 가로채기 기능을 켰었다면 도크 우클릭에서 먼저 "Windows 기본으로 되돌리기"를 누르세요.

문제 생기면 도크 우클릭 → "싹싹김치 캡처 종료" 후 다시 실행해보세요.
"""


def log(msg: str) -> None:
    print(f"[package] {msg}")


def ensure_ffmpeg() -> None:
    """bin/ffmpeg.exe 확보.

    배포물에는 반드시 LGPL 빌드만 포함되어야 한다 (앱이 MIT이므로 GPL 컴포넌트 번들 시
    라이선스 전파 위험). 따라서 시스템 PATH의 ffmpeg는 복사하지 않고,
    오직 BtbN LGPL 빌드만 다운로드해서 사용.

    이미 bin/ffmpeg.exe가 있다면 사용자가 직접 두었거나 이전 다운로드 결과라고 보고 재사용.
    GPL 빌드를 모르고 두었을 수 있으므로 빌드 직전에 라이선스 확인 권장.
    """
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    if FFMPEG_PATH.is_file() and FFMPEG_PATH.stat().st_size > 1_000_000:
        log(f"ffmpeg already at {FFMPEG_PATH}")
        log("  → LGPL 빌드인지 확인하려면: ffmpeg -version | findstr enable-gpl")
        log("  → 'enable-gpl' 옵션이 보이면 GPL 빌드입니다. 삭제 후 다시 실행하면 LGPL 빌드를 새로 받습니다.")
        return

    log(f"downloading ffmpeg LGPL build (~80MB)...")
    log(f"  release tag: {FFMPEG_RELEASE_TAG}")
    log(f"  source: {FFMPEG_RELEASE_URL}")
    if FFMPEG_RELEASE_TAG == "latest":
        log("  ⚠ 경고: 'latest' 롤링 태그 사용 중 — 재현 불가/해시 고정 불가.")
        log("    재현 가능한 빌드를 원하면 package.py 의 FFMPEG_RELEASE_TAG 를")
        log("    날짜 태그(autobuild-YYYY-MM-DD-HH-MM)로 고정하세요.")
    with urllib.request.urlopen(FFMPEG_RELEASE_URL, timeout=180) as resp:
        data = resp.read()
    log(f"downloaded {len(data)/1024/1024:.1f} MB")

    actual_sha = hashlib.sha256(data).hexdigest()
    log(f"downloaded sha256: {actual_sha}")
    expected = (FFMPEG_SHA256 or "").strip().lower()
    if expected:
        if actual_sha != expected:
            raise RuntimeError(
                "ffmpeg zip SHA256 불일치 — 손상/변조 의심으로 중단.\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual_sha}\n"
                "  의도된 빌드 교체라면 package.py 의 FFMPEG_SHA256 을 갱신하세요."
            )
        log("  ✓ SHA256 검증 통과")
    else:
        log("  ⚠ FFMPEG_SHA256 미설정 — 무결성 검증 건너뜀.")
        log("    위 'downloaded sha256' 값을 package.py 의 FFMPEG_SHA256 에 넣으면")
        log("    다음 빌드부터 자동 검증됩니다.")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        ff_member = next(
            (n for n in zf.namelist() if n.endswith("/bin/ffmpeg.exe")), None
        )
        if ff_member is None:
            raise RuntimeError("ffmpeg.exe not found inside release zip")
        with zf.open(ff_member) as src, open(FFMPEG_PATH, "wb") as dst:
            shutil.copyfileobj(src, dst)
    log(f"extracted LGPL build to {FFMPEG_PATH}")


def run_pyinstaller() -> None:
    log("running pyinstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm", "--clean"]
    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run(
        cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, creationflags=creation,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        raise RuntimeError(f"pyinstaller failed (rc={proc.returncode})")
    log("pyinstaller done")


def write_readme() -> None:
    if not APP_FOLDER.is_dir():
        raise RuntimeError(f"build folder missing: {APP_FOLDER}")
    README_PATH.write_text(README_TEMPLATE, encoding="utf-8")
    log(f"wrote {README_PATH.name}")


def _find_iscc() -> Optional[Path]:
    for c in _ISCC_CANDIDATES:
        if c.is_file():
            return c
    on_path = shutil.which("iscc")
    if on_path:
        return Path(on_path)
    return None


def build_installer() -> Optional[Path]:
    """Inno Setup으로 단일 파일 인스톨러 빌드. 없으면 안내만 하고 skip."""
    iscc = _find_iscc()
    if iscc is None:
        log("Inno Setup 없음 — 인스톨러 skip.")
        log("  설치: winget install JRSoftware.InnoSetup  (5MB, ~30초)")
        log("  또는: https://jrsoftware.org/isdl.php")
        return None
    log(f"compiling installer with {iscc.name}...")
    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run(
        [str(iscc), "/Q", str(ISS_PATH)],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, creationflags=creation,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        log(f"ISCC failed (rc={proc.returncode}) — 인스톨러 skip.")
        return None
    # 옛 버전 exe가 dist에 남아 있을 수 있으므로 '가장 최근 것'을 집는다
    setups = sorted(
        DIST_ROOT.glob("Setup_SsakKimchiCapture_*.exe"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    setup = setups[0] if setups else None
    if setup is None:
        log("Setup_*.exe 못 찾음.")
        return None
    size_mb = setup.stat().st_size / 1024 / 1024
    log(f"installer ready: {setup} ({size_mb:.1f} MB)")
    return setup


def zip_bundle() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    log(f"zipping → {ZIP_PATH.name} (이거 좀 걸려요)...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(APP_FOLDER):
            for f in files:
                full = Path(root) / f
                arc = Path(APP_FOLDER_NAME) / full.relative_to(APP_FOLDER)
                zf.write(full, str(arc))
    size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
    log(f"zip ready: {ZIP_PATH} ({size_mb:.1f} MB)")


def main() -> int:
    try:
        ensure_ffmpeg()
        run_pyinstaller()
        write_readme()
        zip_bundle()
        installer = build_installer()
    except Exception as exc:
        log(f"FAILED: {exc}")
        return 1
    log("=== 배포 패키지 준비 끝 ===")
    if installer is not None:
        log(f"  → 인스톨러(추천, 더블클릭 한 번 설치): {installer}")
    log(f"  → ZIP(수동 압축 풀기 방식): {ZIP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
