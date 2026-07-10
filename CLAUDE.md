# 싹싹김치 캡처 — 프로젝트 가이드 (Claude Code용)

## 📌 메모리 규칙 (가장 중요)
**이 프로젝트의 모든 진행 상황 / 결정 사항 / 재개 정보는 항상 이 `CLAUDE.md` 파일에 누적 저장하세요.**

- `C:\Users\<user>\.claude\projects\...\memory\` 같은 auto-memory 시스템은 **사용하지 마세요.** PC 이동 시 안 따라감.
- 새 작업이 끝나면 아래 "현재 상태" + "작업 이력"에 한 줄 추가하고, 비-자명한 결정이 있으면 "비-자명한 결정 사항"에도 추가.
- 이 파일은 git에 커밋되어야 어느 PC에서 clone해도 그대로 작동. ✅ 2026-07-09: `.gitignore`의 `CLAUDE.md` 줄 제거 완료(원래 추적 중이라 커밋도 잘 되고 있었음) — 미결정 사항 해소.

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
- `ssakkimchi/exit_ad.py` — 종료 팝업 배너 다이얼로그. 맨 위 **★배너 설정★ 블록**(`BANNER_ENABLED`/`BANNER_IMAGE`/`BANNER_URL`/`BANNER_TITLE`/`BANNER_SUBTITLE`/`BANNER_DESC`/`BANNER_BUTTON`/`BANNER_ACCENT`)만 고치면 배너 교체 가능. 이미지(assets/exit_ad.png) 우선, 없으면 텍스트 카드. 기본값=OFFCUT STUDIO 홍보(자매 제품). `app.py._show_exit_ad`가 `BANNER_ENABLED` 확인 후 표시. (`STUDIO_URL`은 `BANNER_URL` 하위호환 별칭)
- `ssakkimchi/region_capture.py` — 단일 모니터 overlay (Qt6 듀얼모니터 이슈 회피용)
- `ssakkimchi/coords.py` — 물리↔논리 좌표 변환 헬퍼 (Win32/DWM/mss=물리, Qt=논리). 모니터 매칭은 원점 정렬+크기 검증 위상 방식
- `ssakkimchi/shell_utils.py` — `reveal_in_explorer()` (explorer `/select,` 공용 헬퍼)
- `ssakkimchi/hotkeys.py` + `ssakkimchi/hotkey_dialog.py` — pynput 기반 + 충돌 테스트 버튼
- `DEVELOPMENT_PLAN.md` — **개발 계획 & 작업 지시서** (Phase 1~4 + 백로그, 작업 ID 단위 지시/완료기준/검증 포함). 다음 작업 재개 시 이 문서부터 볼 것
- `ssakkimchi/win_job.py` — Windows Job Object (좀비 ffmpeg 방지)
- `ssakkimchi/logging_setup.py` — 5MB×3 rotate (`~/.ssakkimchi/logs/ssakkimchi.log`)
- `ssakkimchi/version.py` — VERSION 상수 (배포 시 수정)
- `build.spec` / `tools/installer.iss` / `tools/package.py` — 빌드 파이프라인
- `assets/` — `exit_ad.png` 들어갈 곳 (현재 비어있음 → 텍스트 fallback)

---

## 비-자명한 결정 사항 (실수 방지)
- **Windows 전용으로 확정 (2026-07-09, 사용자 결정).** macOS 포팅 안 함 — 코어가 winreg/Win32/DWM/gdigrab 의존이라 맥에선 임포트조차 실패하고, 맥엔 Shottr 등 기존 강자가 있어 배포 가치도 없음. 맥이 필요해지면 이 repo와 무관하게 Swift/ScreenCaptureKit 네이티브 앱을 새로 만들기로 함. **이 repo에서 크로스플랫폼 추상화 작업 금지.**
- **자매 제품 OFFCUT STUDIO + `https://offcut.app`(STUDIO_URL)은 리브랜딩 대상 아님.** 종료 광고는 별개 브랜드인 OFFCUT STUDIO를 홍보하므로 그대로 둠. 캡처 앱 본체만 싹싹김치.
- **부분캡처 overlay는 마우스 있는 화면 1개만 덮음.** 가상 데스크톱 전체 덮으면 Qt6가 mouse event 못 받음 (BenQ 듀얼모니터 환경에서 실측).
- **`Signal(Path, ...)`은 안 됨 → `Signal(object, ...)` 써야 함.** Qt는 Path 타입 모름.
- **`recording.stop()`은 데몬 스레드에서 `proc.wait()` 호출.** 동기 호출하면 UI 326ms 블록 (0.5ms로 600× 개선).
- **모든 ffmpeg Popen은 반드시 `win_job.assign_pid()` 호출.** 안 하면 부모 강제종료 시 좀비 ffmpeg 남음.
- **한글 경로 ffmpeg ANSI 이슈 회피**: 작업은 `%TEMP%/ssakkimchi_recording`에서, 끝나면 `shutil.move`로 최종 경로 이동.
- **단일 `RegionCaptureOverlay` 인스턴스 공유.** region/scroll/ocr/record/gif 5모드가 disconnect/connect 재연결로 같은 overlay 사용. `warnings.catch_warnings()`로 disconnect RuntimeWarning 억제.
- **인코더 우선순위**: `h264_nvenc > h264_qsv > h264_amf > h264_mf > libopenh264 > mpeg4`. LGPL 빌드라 libx264(GPL) 미사용. 시작 2초 내 ffmpeg 사망 시 다음 후보로 자동 재시도(`recording._on_tick`).
- **mpeg4 인자에 `-vtag xvid` 금지** — 최신 번들 ffmpeg가 MP4 컨테이너에서 거부해 녹화가 아예 실패 ("Tag xvid incompatible with mp4v", 2026-07 실측). v1.0.2까지는 이 잠재 버그 때문에 HW 인코더 없는 PC에서 녹화 전멸이었음.
- **좌표계: Win32/DWM/mss는 물리 픽셀, Qt는 논리 픽셀.** 변환은 반드시 `coords.py` 헬퍼로. `논리×dpr` 직접 계산은 배율 다른 보조 모니터에서 틀림. **Qt6 `QScreen.name()`은 GDI 장치명(`\\.\DISPLAY1`)이 아니라 모델명("BenQ GW2480 (1)")을 반환**(실측) → 이름 매칭 불가, coords.py는 원점 정렬+크기 검증 위상 매칭 사용.
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

## ⏸ 현재 상태 (2026-07-08 기준)

**진행 중**: `DEVELOPMENT_PLAN.md` 기반 개선 작업.
- **Phase 1+2 완료 → v1.0.4 빌드·릴리즈 게시 완료 (2026-07-10).** 남은 것: 실기 테스트 2건(150% 배율 창 캡처, 듀얼모니터 창 캡처 마우스 이벤트 — HANDOFF.md), 종료 배너(사용자 제공 대기).
- Phase 3(핀/지연캡처/영역반복/자동실행), Phase 4(주석 에디터)는 미착수 — 지시서는 DEVELOPMENT_PLAN.md에 완비. 혼합 DPI 녹화 영역 한계는 백로그 B-8.

**완료**:
- 싹싹김치 리브랜딩 (7차) — 코드/빌드/문서/GitHub 링크 전면 교체, 내부 패키지 `offcut`→`ssakkimchi` 마이그레이션 없이 변경
- v1.0.2 인프라 (LGPL ffmpeg, THIRD_PARTY_LICENSES, 이슈 템플릿)
- 종료 광고 다이얼로그 (이미지 자동 인식, 없으면 텍스트 fallback) — OFFCUT STUDIO 홍보 유지
- `.gitignore` / `LICENSE` (MIT) / `README.md` / `CHANGELOG.md`
- **종료 팝업 배너 설정화 (9차)** — `exit_ad.py` 맨 위 ★배너 설정★ 블록(이미지/링크/문구/표시여부/색). 동작 검증 완료, 기본값은 OFFCUT STUDIO 유지. 실제 배너 이미지/링크는 사용자가 나중에 제공 예정 → [[HANDOFF.md]]

**GitHub repo**: https://github.com/gyqls051-arch/ssakssak-capture (Public) — 최신 릴리즈 **v1.0.4** (2026-07-10 게시).
**다운로드**: https://github.com/gyqls051-arch/ssakssak-capture/releases/download/v1.0.4/Setup_SsakKimchiCapture_1.0.4.exe

---

## 사용자 미완료 작업 (배포 전)
1. **종료 배너 이미지 + 링크** (사용자가 나중에 제공 예정) → `assets/exit_ad.png`(가로 1040px) 저장 + `exit_ad.py`의 `BANNER_URL`(싹싹김치 배너면 `BANNER_TITLE/SUBTITLE/DESC/BUTTON`도) 설정 → `package.bat` 재빌드 → 릴리즈 재첨부(`--clobber`). repo에 이미지 올리려면 `.gitignore`의 `assets/exit_ad.png` 줄 제거. 상세: [[HANDOFF.md]]
2. (참고) 배너 끄려면 `BANNER_ENABLED=False`. 클릭/버튼 없는 단순 배너는 `BANNER_URL=""`.
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
- **9차** (2026-06-24): **종료 팝업 배너 설정화** — `exit_ad.py`를 맨 위 ★배너 설정★ 블록(`BANNER_ENABLED/IMAGE/URL/TITLE/SUBTITLE/DESC/BUTTON/ACCENT`)으로 리팩터. 이미지/문구/링크/색/표시여부를 코드 수정 없이 교체 가능. `app.py._show_exit_ad`가 `BANNER_ENABLED` 확인 후 표시. 버튼 hover/pressed 색은 `_shade()`로 자동 음영. 오프스크린 스모크 테스트 통과. `assets/README.txt`도 새 방식으로 갱신. 실제 배너 이미지/링크는 사용자가 나중에 제공 예정. 작업 인계용 `HANDOFF.md` 추가.
- **10차** (2026-07-06~08): **전체 코드 리뷰 + DEVELOPMENT_PLAN.md + Phase 1 구현(v1.0.3 코드)** — 36모듈 전수 리뷰로 DPI/멀티모니터 좌표계 버그군 발견 → 작업 지시서 `DEVELOPMENT_PLAN.md` 작성(Phase 1~4+백로그). Phase 1 구현: `coords.py` 신설(물리↔논리, 위상 매칭), 창 캡처 DPI 이중 변환 수정, 전체 캡처=커서 모니터, SW 인코더 폴백 `h264_mf`→`libopenh264`→`mpeg4`+시작 2초 내 사망 시 자동 재시도, `shell_utils.reveal_in_explorer` 통일, grab None 가드, settings 원자적 저장, 핫키 실패 로그+토스트. **발견 2건**: ① Qt6 `QScreen.name()`은 모델명 반환이라 GDI 이름 매칭 불가 ② 기존 mpeg4 폴백의 `-vtag xvid`가 번들 ffmpeg에서 거부되어 v1.0.2는 HW 인코더 없는 PC에서 녹화 전멸(제거로 수정). 검증: py_compile 전체, 실모니터 coords 왕복 probe, 인코더 3종 실녹화 rc=0, 오프스크린 앱 조립 스모크 통과.
- **11차** (2026-07-08): **Phase 2 구현(v1.0.4 코드)** — F-1 부분캡처/OCR 프리즈 프레임(begin 시 화면 얼려 크롭 — hide 레이스 원천 제거, 딤은 선택 바깥 4조각 방식, grab 실패 시 라이브 폴백), F-2 색추출·거리측정 단일 모니터화(`capture_core.active_screen_info()` 공용화, 색 샘플링 coords 기반; 창 캡처는 가상 데스크톱 유지—실기 확인 대기), F-3 스크롤 스티칭 `_StitchWorker(QThread)`화+진행 토스트+quit 시 워커 정리, F-4 `ocr_result_dialog.py`(수정 가능 modeless 항상-위, 자동 복사 유지). 버전 1.0.4로 bump(1.0.3은 미배포 합본). 오프스크린 스모크(프리즈 크롭 크기/라이브 모드/스티칭 합성 프레임 300×400/다이얼로그/cancel 중복 호출) 전부 통과.
- **12차** (2026-07-09): **Windows 전용 확정 + 핸드오프 + v1.0.4 커밋** — macOS 포팅 검토 결과 "맥은 별도 네이티브 앱으로" 결정(비-자명 결정 참조). README에 Windows 전용 명시 + 인코더 설명 최신화, `.gitignore`의 `CLAUDE.md` 줄 제거(미결정 해소), `HANDOFF.md`를 v1.0.4 기준으로 전면 갱신. Phase 1+2 산출물 전체 커밋·푸시 (`69c9b96`, `90514c2`, `d3ae213`).
- **13차** (2026-07-09): **v1.0.4 빌드 + 기동 스모크** — ⚠ `tools/installer.iss`의 `MyAppVersion`이 하드코딩이라 버전 bump는 **version.py + installer.iss 2곳** 수정해야 함(실제로 걸림). `package.bat` 빌드 → `Setup_SsakKimchiCapture_1.0.4.exe`(90.8MB) + `SsakKimchiCapture_1.0.4_portable.zip`(131.9MB). 프로즌 빌드 8초 기동 스모크: "v1.0.4 starting → entering event loop" 확인 후 종료. `package.py`의 installer 로그가 옛 exe를 집던 glob 순서 문제도 수정(mtime 최신 우선). 사용자 승인 후 **릴리즈 v1.0.4 게시 완료** (2026-07-10, exe 90.8MB + portable zip 131.9MB 첨부 확인). ⚠ 세션 도중 gh 활성 계정이 rlagyqls051-create로 플립되어 push 403 발생 — `gh auth token --user gyqls051-arch` 인라인 토큰 방식으로 해결(HANDOFF 인증 메모 갱신).

---

## 측정된 성능 (BenQ 1920×1080 ×2, NVENC)
- 1080p30 녹화: ~390 kbps (조용한 화면), 30fps 일정, frame drop 0
- stop latency: 326ms → UI 블록 0.5ms (비동기화)
- GIF 변환: 3s→0.65s, 6s→0.99s, 12s→1.76s
- 좀비 ffmpeg: Job Object 적용 후 0개 (적용 전 1개)
