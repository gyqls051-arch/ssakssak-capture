# HANDOFF — 싹싹김치 캡처

> 작업 인계 문서. 마지막 갱신: 2026-07-09
> 프로젝트 전체 가이드는 [CLAUDE.md](CLAUDE.md), 작업 지시서는 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) 참고. 이 문서는 "지금 상태 + 다음 할 일"만.

## 한 줄 요약
**v1.0.4 코드 완료·커밋됨 (배포는 아직 v1.0.2).** DPI/멀티모니터 버그 수정 + 인코더 폴백 업그레이드 + 프리즈 프레임 캡처 등 (계획서 Phase 1+2).
**Windows 전용으로 확정** — macOS 작업 금지 (CLAUDE.md 비-자명 결정).
👉 **다음 할 일: ① 빌드 → 실기 테스트 → 릴리즈 v1.0.4, ② 종료 배너 이미지(사용자 제공 대기)**

---

## ✅ 완료된 것 (누적)

- **배포됨 (v1.0.2)**: GitHub Public repo + 릴리즈. https://github.com/gyqls051-arch/ssakssak-capture
- **v1.0.4 코드 (2026-07-08, 커밋됨·미배포)** — 상세는 [CHANGELOG.md](CHANGELOG.md)와 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) Phase 1·2 노트:
  - 창 캡처 DPI 이중 변환 수정 (125~150% 배율 모니터에서 어긋나던 P0 버그) — 신규 `ssakkimchi/coords.py`
  - **mpeg4 폴백의 `-vtag xvid` 제거** — v1.0.2는 HW 인코더 없는 PC에서 녹화가 아예 실패하던 잠재 버그였음
  - SW 인코더 폴백 `h264_mf → libopenh264 → mpeg4` + 시작 2초 내 사망 시 자동 재시도
  - 부분 캡처/OCR 프리즈 프레임 (딤/테두리 유입 레이스 제거), 색/거리 오버레이 단일 모니터화
  - 스크롤 스티칭 워커 스레드화 (UI 프리즈 해소), OCR 결과 확인 창, 전체 캡처=커서 모니터 등
- **종료 팝업 배너 설정화**: `ssakkimchi/exit_ad.py` 맨 위 ★배너 설정★ 블록. 기본값 = OFFCUT STUDIO 홍보.

---

## ⏭️ 다음 할 일 1 — v1.0.4 빌드·테스트·릴리즈

1. **빌드**: `package.bat` → `dist/Setup_SsakKimchiCapture_1.0.4.exe` + 포터블 ZIP. (오래 걸림 — 백그라운드 권장)
2. **실기 테스트** (DEVELOPMENT_PLAN.md §8 매트릭스). 꼭 볼 것:
   - Windows 배율을 **150%로 바꿔서** 창 캡처 정확성 (이번 수정의 핵심 검증 — 끝나면 배율 원복)
   - 듀얼모니터에서 **창 캡처** 마우스 이벤트 (유일하게 가상 데스크톱 오버레이 유지한 기능 — 문제 시 계획서 F-2 지시 3)
   - 부분 캡처 결과 가장자리에 흰 1px/딤 없는지, HW 인코더 임시 차단 후 h264_mf 녹화
3. **릴리즈**: `gh release create v1.0.4 <exe> <zip> --title ... --notes-file` (CHANGELOG 발췌). 인증은 아래 "git / GitHub 인증 메모".

## ⏭️ 다음 할 일 2 — 종료 배너 (사용자가 이미지+링크 줄 예정)

1. **이미지**: 받은 이미지를 `assets/exit_ad.png` 로 저장 (가로 1040px 권장, 16:9 또는 16:10).
   - repo에 이미지도 같이 올리려면 → `.gitignore` 에서 `assets/exit_ad.png` 줄 삭제 후 `git add`.
2. **링크**: `ssakkimchi/exit_ad.py` 맨 위에서 `BANNER_URL = "<받은 링크>"`.
   - 싹싹김치 자체 배너로 갈 거면 `BANNER_TITLE / BANNER_SUBTITLE / BANNER_DESC / BANNER_BUTTON / BANNER_ACCENT` 도 수정.
   - 배너 끄려면 `BANNER_ENABLED = False`. 클릭/버튼 없는 단순 배너는 `BANNER_URL = ""`.
3. 재빌드 → 릴리즈 재첨부(`gh release upload vX.Y.Z <exe> --clobber`). 상세는 [assets/README.txt](assets/README.txt).

## 📌 확정된 방향 (뒤집지 말 것)

- **Windows 전용.** macOS 포팅/크로스플랫폼 추상화 금지 — 맥은 필요 시 Swift/ScreenCaptureKit로 별도 앱 (이 repo 무관). 근거: 코어가 winreg/Win32/DWM/gdigrab 의존 + 맥엔 Shottr 등 기존 강자.
- 이후 기능 개발은 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) Phase 3(핀/지연 캡처/영역 반복/자동 실행) → Phase 4(주석 에디터) 순.

---

## 🛠️ 빌드 / 배포 환경 메모 (이 PC 기준)
- Python 3.11+, **PyInstaller 6.20**, **PySide6 6.11** (설치됨).
- **Inno Setup**: `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` (winget으로 설치됨). 없으면 `winget install JRSoftware.InnoSetup`.
- `bin/ffmpeg.exe` (130MB, **LGPL 빌드**) 이미 있음 → 빌드 시 재다운로드 안 함. (h264_mf/libopenh264 포함 — 2026-07 실측)
- 빌드 한 방: `package.bat` (= `python tools/package.py`). PyInstaller→ZIP→Inno 순.

## 🔑 git / GitHub 인증 메모
- `origin` = `https://github.com/gyqls051-arch/ssakssak-capture.git`
- 커밋 작성자(이 repo 한정): `user.name=gyqls051-arch`, `user.email=284581949+gyqls051-arch@users.noreply.github.com`
- ✅ 2026-07-09 확인: gh keyring에 **gyqls051-arch가 활성 계정**으로 로그인돼 있음(repo 스코프) → **`git push` / `gh release` 그냥 됨**, PAT 불필요.
  (rlagyqls051-create도 keyring에 있으나 비활성. 활성 계정이 바뀌어 있으면 `gh auth switch -u gyqls051-arch`.)
- 옛 OFFCUT 히스토리: 로컬 브랜치 `backup-offcut-history` 에 보존 (원격엔 없음).

## 🔒 보안
- 릴리즈 작업에 쓴 **개인 액세스 토큰(PAT)은 사용 후 폐기(revoke)** 권장.

---

## 📍 핵심 위치
| 무엇 | 어디 |
|---|---|
| 작업 지시서 (다음 작업은 여기부터) | `DEVELOPMENT_PLAN.md` |
| 배너 설정 | `ssakkimchi/exit_ad.py` 맨 위 ★배너 설정★ |
| 좌표 변환 (DPI/멀티모니터) | `ssakkimchi/coords.py` |
| 인코더 선택/폴백 | `ssakkimchi/ffmpeg_runtime.py` |
| 버전 상수 | `ssakkimchi/version.py` |
| 빌드 파이프라인 | `build.spec` / `tools/installer.iss` / `tools/package.py` |
| 프로젝트 전체 가이드 | `CLAUDE.md` |
