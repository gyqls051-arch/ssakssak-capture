# HANDOFF — 싹싹김치 캡처

> 작업 인계 문서. 마지막 갱신: 2026-06-24
> 프로젝트 전체 가이드는 [CLAUDE.md](CLAUDE.md) 참고. 이 문서는 "지금 상태 + 다음 할 일"만.

## 한 줄 요약
오프컷 → **싹싹김치** 리브랜딩 완료, GitHub 공개 배포(**v1.0.2**)까지 끝남.
종료 팝업 배너는 **설정 한 블록만 바꾸면 되는 상태로 세팅**됨.
👉 **다음 할 일: 배너 이미지 + 링크 넣고 재빌드/재릴리즈** (사용자가 이미지·링크 제공 예정).

---

## ✅ 완료된 것
- **리브랜딩**: 오프컷 캡쳐 → 싹싹김치 캡처. 패키지 `offcut`→`ssakkimchi`, 데이터 `~/.offcut`→`~/.ssakkimchi`, 클래스 `OffcutApp`→`SsakKimchiApp`.
- **GitHub repo (Public)**: https://github.com/gyqls051-arch/ssakssak-capture
- **Release v1.0.2**: https://github.com/gyqls051-arch/ssakssak-capture/releases/tag/v1.0.2
  - 설치파일: `Setup_SsakKimchiCapture_1.0.2.exe` (85.6MB)
  - 포터블: `SsakKimchiCapture_1.0.2_portable.zip` (125MB)
- **종료 팝업 배너 설정화**: `ssakkimchi/exit_ad.py` 맨 위 **★배너 설정★** 블록으로 분리. 동작 검증 완료(오프스크린 스모크 테스트). 현재 기본값은 자매 제품 OFFCUT STUDIO 홍보.

---

## ⏭️ 다음 할 일 — 종료 배너 (사용자가 이미지+링크 줄 예정)

이미지/링크를 받으면 이 순서로 진행:

1. **이미지**: 받은 이미지를 `assets/exit_ad.png` 로 저장 (가로 1040px 권장, 16:9 또는 16:10).
   - repo에 이미지도 같이 올리려면 → `.gitignore` 에서 `assets/exit_ad.png` 줄 삭제 후 `git add`.
2. **링크**: `ssakkimchi/exit_ad.py` 맨 위에서 `BANNER_URL = "<받은 링크>"`.
   - 싹싹김치 자체 배너로 갈 거면 `BANNER_TITLE / BANNER_SUBTITLE / BANNER_DESC / BANNER_BUTTON / BANNER_ACCENT` 도 수정 (텍스트 카드 fallback용).
   - 배너 끄려면 `BANNER_ENABLED = False`. 클릭/버튼 없는 단순 배너는 `BANNER_URL = ""`.
3. **재빌드**: `package.bat` → `dist/Setup_SsakKimchiCapture_X.X.X.exe` + `dist/싹싹김치 캡처.zip`.
4. **재릴리즈**:
   - 같은 버전이면: `gh release upload v1.0.2 <새 exe> --clobber` (에셋 교체).
   - 버전 올리면: `ssakkimchi/version.py` `VERSION` + `CHANGELOG.md` 갱신 → `gh release create vX.Y.Z ...`.

배너 설정 위치/사용법 상세는 [assets/README.txt](assets/README.txt) 참고.

---

## 🛠️ 빌드 / 배포 환경 메모 (이 PC 기준)
- Python 3.11+, **PyInstaller 6.20**, **PySide6 6.11** (설치됨).
- **Inno Setup**: `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` (winget으로 설치됨). 없으면 `winget install JRSoftware.InnoSetup`.
- `bin/ffmpeg.exe` (130MB, **LGPL 빌드**) 이미 있음 → 빌드 시 재다운로드 안 함.
- 빌드 한 방: `package.bat` (= `python tools/package.py`). PyInstaller→ZIP→Inno 순. 빌드 오래 걸리니 백그라운드 권장.

## 🔑 git / GitHub 인증 메모
- `origin` = `https://github.com/gyqls051-arch/ssakssak-capture.git`
- 커밋 작성자(이 repo 한정): `user.name=gyqls051-arch`, `user.email=284581949+gyqls051-arch@users.noreply.github.com`
- ⚠️ 로컬 gh keyring 활성 계정은 **`rlagyqls051-create`** (gyqls051-arch 아님). gyqls051-arch repo 작업은 **`GH_TOKEN` 환경변수에 gyqls051-arch PAT**를 넣고 실행해야 함.
- push는 토큰 inline URL 방식 사용: `git remote set-url origin https://x-access-token:<TOKEN>@github.com/...; git push; (원복)`.
- **PAT 권한**: repo 생성 = `Administration: write`, push/release = `Contents: write` 둘 다 필요(fine-grained).
- 옛 OFFCUT 히스토리: 로컬 브랜치 `backup-offcut-history` 에 보존 (원격엔 없음, 깨끗한 단일 커밋으로 시작).

## 🔒 보안
- 릴리즈 작업에 쓴 **개인 액세스 토큰(PAT)은 사용 후 폐기(revoke)** 권장. (GitHub → Settings → Developer settings → Personal access tokens)

---

## 📍 핵심 위치
| 무엇 | 어디 |
|---|---|
| 배너 설정 | `ssakkimchi/exit_ad.py` 맨 위 ★배너 설정★ |
| 배너 안내 | `assets/README.txt` |
| 버전 상수 | `ssakkimchi/version.py` |
| 빌드 파이프라인 | `build.spec` / `tools/installer.iss` / `tools/package.py` |
| 프로젝트 전체 가이드 | `CLAUDE.md` |
