# 싹싹김치 캡처 — 프로젝트 가이드 (Claude Code용)

## 📌 메모리 규칙 (가장 중요)
**이 프로젝트의 모든 진행 상황 / 결정 사항 / 재개 정보는 항상 이 `CLAUDE.md` 파일에 누적 저장하세요.**

- `C:\Users\<user>\.claude\projects\...\memory\` 같은 auto-memory 시스템은 **사용하지 마세요.** PC 이동 시 안 따라감.
- 새 작업이 끝나면 아래 "현재 상태" + "작업 이력"에 한 줄 추가하고, 비-자명한 결정이 있으면 "비-자명한 결정 사항"에도 추가.
- 이 파일은 git에 커밋되어야 어느 PC에서 clone해도 그대로 작동. ⚠️ 현재 `.gitignore`에 `CLAUDE.md`가 들어 있어 **커밋이 안 됨** — 이 메모리 규칙대로 쓰려면 `.gitignore`에서 `CLAUDE.md` 줄을 빼야 함(미결정).

---

## 프로젝트 개요
Windows PySide6 기반 캡처 + 녹화 + GIF + OCR + 색 추출 + 거리 측정 통합 도구.
도크 UI, Alt+1~9 한 손 단축키, ffmpeg 내장 + 하드웨어 인코딩(NVENC/QSV/AMF) 자동 선택.

**브랜드**: "싹싹김치" 패밀리의 캡처 도구 (`싹싹김치 캡처`). 내부 패키지/식별자는 `ssakkimchi`.
자매 제품 **OFFCUT STUDIO**(프리미어 컷편집 가속기)는 종료 광고에서 그대로 홍보 — 별개 브랜드라 유지.

**포지셔닝**: Mac Shottr/ScreenFloat 감성을 Windows에. 디자이너/프론트엔드용. ShareX 자동업로드/클라우드는 의도적으로 안 함.

**도크 구조**: 사진(부분/창/전체/스크롤) / 영상(GIF/녹화) / 도구(색상/측정/OCR) 3그룹.

---

## 빌드
```powershell
# 더블클릭 또는
package.bat
```
- 자동 흐름: ffmpeg 확보(BtbN LGPL 빌드 download) → PyInstaller → README.txt → ZIP → Inno Setup ISCC
- 산출물: `dist/Setup_SsakKimchiCapture_X.X.X.exe` (~86MB) + `dist/싹싹김치 캡처.zip` (~125MB)
- 요구: Python 3.11+, PyInstaller, (선택) Inno Setup 6 (`winget install JRSoftware.InnoSetup`)
- Inno Setup 위치: `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` (winget 설치 시)

---

## 핵심 파일
- `main.py` — 엔트리 (logging + single instance + SsakKimchiApp)
- `ssakkimchi/app.py` — 오케스트레이션. `quit()`에서 `_show_exit_ad()` hook
- `ssakkimchi/recording.py` — RecordingController + GIF 2-pass + Job Object
- `ssakkimchi/exit_ad.py` — 종료 광고 다이얼로그(OFFCUT STUDIO 홍보). **`STUDIO_URL` (line 27)** = 광고 클릭 시 이동할 홈페이지
- `ssakkimchi/region_capture.py` — 단일 모니터 overlay (Qt6 듀얼모니터 이슈 회피용)
- `ssakkimchi/hotkeys.py` + `ssakkimchi/hotkey_dialog.py` — pynput 기반 + 충돌 테스트 버튼
- `ssakkimchi/win_job.py` — Windows Job Object (좀비 ffmpeg 방지)
- `ssakkimchi/logging_setup.py` — 5MB×3 rotate (`~/.ssakkimchi/logs/ssakkimchi.log`)
- `ssakkimchi/version.py` — VERSION 상수 (배포 시 수정)
- `build.spec` / `tools/installer.iss` / `tools/package.py` — 빌드 파이프라인
- `assets/` — `exit_ad.png` 들어갈 곳 (현재 비어있음 → 텍스트 fallback)

---

## 비-자명한 결정 사항 (실수 방지)
- **자매 제품 OFFCUT STUDIO + `https://offcut.app`(STUDIO_URL)은 리브랜딩 대상 아님.** 종료 광고는 별개 브랜드인 OFFCUT STUDIO를 홍보하므로 그대로 둠. 캡처 앱 본체만 싹싹김치.
- **부분캡처 overlay는 마우스 있는 화면 1개만 덮음.** 가상 데스크톱 전체 덮으면 Qt6가 mouse event 못 받음 (BenQ 듀얼모니터 환경에서 실측).
- **`Signal(Path, ...)`은 안 됨 → `Signal(object, ...)` 써야 함.** Qt는 Path 타입 모름.
- **`recording.stop()`은 데몬 스레드에서 `proc.wait()` 호출.** 동기 호출하면 UI 326ms 블록 (0.5ms로 600× 개선).
- **모든 ffmpeg Popen은 반드시 `win_job.assign_pid()` 호출.** 안 하면 부모 강제종료 시 좀비 ffmpeg 남음.
- **한글 경로 ffmpeg ANSI 이슈 회피**: 작업은 `%TEMP%/ssakkimchi_recording`에서, 끝나면 `shutil.move`로 최종 경로 이동.
- **단일 `RegionCaptureOverlay` 인스턴스 공유.** region/scroll/ocr/record/gif 5모드가 disconnect/connect 재연결로 같은 overlay 사용. `warnings.catch_warnings()`로 disconnect RuntimeWarning 억제.
- **인코더 우선순위**: `h264_nvenc > h264_qsv > h264_amf > mpeg4`(SW 폴백). LGPL 빌드라 libx264(GPL) 미사용.
- **PyInstaller 번들 시 `sys._MEIPASS`** 안에 `bin/ffmpeg.exe` + `assets/` 들어감. 개발 환경에선 프로젝트 루트 기준으로 찾도록 fallback 처리됨.
- **single_instance** 타임아웃: 200ms → 800ms × 3회 retry (시스템 부하 시 false negative 방지).

---

## 기본 단축키 (`ssakkimchi/actions.py`)
| 키 | 액션 |
|---|---|
| `Alt+1` | 부분 캡처 |
| `Alt+2` | 전체 캡처 |
| `Alt+3` | 창 캡처 |
| `Alt+4` | 스크롤 캡처 |
| `Alt+5` | 색 추출 |
| `Alt+6` | 거리 측정 |
| `Alt+7` | OCR |
| `Alt+8` | 화면 녹화 (시작/정지) |
| `Alt+9` | GIF 녹화 (시작/정지) |

---

## 사용자 데이터 위치
- 캡처 저장: `~/.ssakkimchi/captures/` (도크 우클릭에서 변경 가능)
- 설정: `~/.ssakkimchi/settings.json`
- 로그: `~/.ssakkimchi/logs/ssakkimchi.log` (5MB × 3 rotate)
- 작업 임시: `%TEMP%/ssakkimchi_recording/` (한글 경로 회피용)

---

## ⏸ 현재 상태 (2026-06-24 기준)

**완료**:
- 싹싹김치 리브랜딩 (7차) — 코드/빌드/문서/GitHub 링크 전면 교체, 내부 패키지 `offcut`→`ssakkimchi` 마이그레이션 없이 변경
- v1.0.2 인프라 (LGPL ffmpeg, THIRD_PARTY_LICENSES, 이슈 템플릿)
- 종료 광고 다이얼로그 (이미지 자동 인식, 없으면 텍스트 fallback) — OFFCUT STUDIO 홍보 유지
- `.gitignore` / `LICENSE` (MIT) / `README.md` / `CHANGELOG.md`

**GitHub repo**: https://github.com/gyqls051-arch/ssakssak-capture (Public) — push 완료, 릴리즈 v1.0.2 게시됨.
**다운로드**: https://github.com/gyqls051-arch/ssakssak-capture/releases/download/v1.0.2/Setup_SsakKimchiCapture_1.0.2.exe

---

## 사용자 미완료 작업 (배포 전)
1. `assets/exit_ad.png` — 1040×585 (16:9) **OFFCUT STUDIO** 광고 이미지 (자매 제품, 싹싹김치 아님)
2. `ssakkimchi/exit_ad.py:27` `STUDIO_URL` — OFFCUT STUDIO 홈페이지 URL (기본값 `https://offcut.app`)
3. (선택) `assets/app.ico` — 다층 ICO. 추가 시 `build.spec`의 `EXE(icon=)` + `installer.iss`의 `SetupIconFile=` 양쪽에 경로 지정
4. (선택) README.md용 스크린샷 (도크 / 부분캡처 / ●REC pill)
5. ~~GitHub repo 생성 + push~~ ✅ 완료 (gyqls051-arch/ssakssak-capture, Public, 단일 커밋 `f39a3f2`)
6. ~~Releases + 설치파일 첨부~~ ✅ 완료 (v1.0.2, exe+포터블 ZIP)
7. ~~리브랜딩 후 재빌드~~ ✅ 완료. (단, `dist/`의 옛 `Setup_OffcutCapture_1.0.0/1.0.1.exe`는 수동 삭제 권장)

**테스트 미완료**:
- 본인 PC에서 리브랜딩 빌드 동작 확인 (트레이 툴팁/메뉴/종료 광고/`~/.ssakkimchi` 데이터 경로)
- 친구 PC에서 첫 설치 사이클 (SmartScreen → 설치 → 단축키 → 광고 → 제거)

---

## 작업 이력
- **1차** (2026-05-15): 부분캡처 NameError 픽스
- **2차** (2026-05-16): 듀얼모니터 Qt6 mouse event 이슈 → 단일 화면 overlay. 영상/GIF 녹화 추가 (NVENC 자동 + ●REC pill + Job Object 좀비 방지)
- **3차** (2026-05-16): 단축키 Ctrl+Shift→Alt 변경, 테스트/초기화 버튼, PrtSc 가로채기 옵션 메뉴
- **4차** (2026-05-17): 로그 시스템 + 진단 다이얼로그 + CHANGELOG + 버전 인프라
- **5차** (2026-05-17): Inno Setup 인스톨러 (v1.0.0, Setup_*.exe 86.4MB)
- **6차** (2026-05-17~18): v1.0.1 — 종료 광고 다이얼로그 + GitHub 배포 준비 (LICENSE/README/.gitignore/git init)
- **7차** (2026-06-24): **싹싹김치 리브랜딩** — `오프컷 캡쳐/OFFCUT`→`싹싹김치 캡처`(캡쳐→캡처 표준 맞춤법 통일), 패키지 `offcut/`→`ssakkimchi/`, 데이터 `~/.offcut`→`~/.ssakkimchi`, 클래스 `OffcutApp`→`SsakKimchiApp`, 단일인스턴스 키·`SSAKKIMCHI_DEBUG`·`ssakkimchi.log`·`ssakkimchi_recording`·exe `Setup_SsakKimchiCapture`까지 전면 교체. GitHub `rlagyqls051-create/OFFCUT_Capture`→`gyqls051-arch/ssakssak-capture`. 자매 제품 **OFFCUT STUDIO** + `offcut.app`은 의도적으로 보존. `.bat` 실행 파일 2개도 rename. 마이그레이션 코드 없음(기존 `~/.offcut` 데이터는 새 경로에서 안 읽힘).
- **8차** (2026-06-24): **GitHub 공개 배포** — `gyqls051-arch/ssakssak-capture` Public repo 생성. 옛 OFFCUT 커밋 3개 제외하고 orphan 단일 커밋(`f39a3f2`, 작성자 gyqls051-arch noreply)으로 push, 옛 히스토리는 로컬 `backup-offcut-history`에 백업. Inno Setup(winget) 설치 후 `package.bat` 빌드 → `Setup_SsakKimchiCapture_1.0.2.exe`(85.6MB)+포터블 ZIP(125MB) → 릴리즈 **v1.0.2** 생성·첨부. 리브랜딩 당시 `gyqls051`로 잘못 적힌 README/문서/installer URL을 `gyqls051-arch`로 교정. (토큰 fine-grained PAT: repo 생성엔 Administration, push엔 Contents:write 권한 둘 다 필요했음.)

---

## 측정된 성능 (BenQ 1920×1080 ×2, NVENC)
- 1080p30 녹화: ~390 kbps (조용한 화면), 30fps 일정, frame drop 0
- stop latency: 326ms → UI 블록 0.5ms (비동기화)
- GIF 변환: 3s→0.65s, 6s→0.99s, 12s→1.76s
- 좀비 ffmpeg: Job Object 적용 후 0개 (적용 전 1개)
