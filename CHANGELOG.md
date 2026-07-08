# 싹싹김치 캡처 — 변경 이력

## v1.0.4 — 2026-07-08

> v1.0.3은 별도 배포 없이 v1.0.4에 합쳐 배포. (DEVELOPMENT_PLAN.md Phase 2)

### 개선
- **부분 캡처/OCR: 프리즈 프레임 방식으로 전환** — 오버레이를 여는 순간 화면을
  얼려 그 위에서 선택·크롭. 결과물에 딤/선택 테두리가 섞일 수 있던
  컴포지터 타이밍 레이스가 원천 제거되고, 드래그 중 화면이 변해도
  "열었을 때 본 그대로" 캡처된다. (녹화/GIF/스크롤 영역 선택은 라이브 유지)
- **색 추출·거리 측정 오버레이를 커서가 있는 모니터 1개만 덮도록 변경** —
  부분 캡처와 동일한 방식. 가상 데스크톱 전체를 덮으면 Qt6가 듀얼모니터에서
  마우스 이벤트를 못 받는 이슈(2차 실측) 회피. 색 샘플링 좌표도 coords 기반으로.
- **스크롤 캡처 이어붙이기를 워커 스레드로 이동** — 프레임이 많을 때
  수 초간 UI가 얼던 문제 해소. "이어붙이는 중…" 진행 토스트 추가.
- **OCR 결과 확인 창 추가** — 인식 텍스트를 눈으로 검수·수정 후 다시 복사
  가능 (기존 자동 클립보드 복사는 유지, 항상-위 modeless 창).

## v1.0.3 — 2026-07-08 (미배포, v1.0.4에 포함)

### 버그 수정 (정확성 핫픽스, DEVELOPMENT_PLAN.md Phase 1)
- **창 캡처: DPI 배율(125~150%) 모니터에서 좌표 이중 변환 수정** —
  DWM/Win32 창 rect는 이미 물리 픽셀인데 dpr을 또 곱해 캡처 영역이 어긋나던 문제.
  히트테스트·하이라이트·grab 전부 새 좌표 헬퍼(`ssakkimchi/coords.py`) 기반으로 교체.
- **SW 인코더 폴백(mpeg4)이 번들 ffmpeg에서 아예 실패하던 문제** —
  `-vtag xvid`를 최신 ffmpeg가 거부 ("Tag xvid incompatible with mp4v").
  HW 인코더(NVENC/QSV/AMF) 없는 PC에서는 녹화가 전멸하던 잠재 버그. 태그 제거.
- 전체 캡처가 도크가 있는 모니터 대신 **커서가 있는 모니터**를 찍도록 수정.
- 캡처 프리뷰의 "폴더 열기"가 일부 환경에서 파일 선택 없이 폴더만 열리던 문제
  (`explorer /select,` 인자 분리) — 공용 `shell_utils.reveal_in_explorer`로 통일.
- 화면 grab 실패(잠금 화면 등) 시 None이 흘러 TypeError 나던 경로 가드.
- settings.json 저장을 원자적(tmp+replace)으로 — 저장 중 크래시 시 파손 방지.

### 개선
- **SW 인코더 폴백 업그레이드**: mpeg4 → `h264_mf`(Windows Media Foundation) →
  `libopenh264` → mpeg4 순. HW 인코더 없는 PC의 녹화 화질·호환성 대폭 개선.
  (셋 다 번들 LGPL ffmpeg에 포함, 실녹화 검증 완료)
- **녹화 시작 직후(2초 내) ffmpeg 사망 시 다음 인코더로 자동 재시도** —
  HW 인코더 오탐지·MF 초기화 불안정 환경에서도 녹화가 성사되도록.
- 전역 단축키 등록 실패가 무음이던 것을 로그 + 토스트로 안내.
  잘못된 조합 1개 때문에 전체 단축키가 죽지 않도록 조합별 검증 후 등록.

## v1.0.2 — 2026-06-24

### 브랜딩 / 공개 배포
- **"오프컷 캡쳐" → "싹싹김치 캡처" 전면 리브랜딩** (`캡쳐`→`캡처` 표준 맞춤법으로 통일).
- 내부 패키지 `offcut`→`ssakkimchi`, 데이터 폴더 `~/.offcut`→`~/.ssakkimchi`, 클래스 `OffcutApp`→`SsakKimchiApp`, 설치파일 `Setup_SsakKimchiCapture_*.exe`.
- **GitHub 공개 배포**: [gyqls051-arch/ssakssak-capture](https://github.com/gyqls051-arch/ssakssak-capture) (Public) — 인스톨러 + 포터블 ZIP 릴리즈.
- 자매 제품 **OFFCUT STUDIO** 종료 광고는 별개 브랜드라 그대로 유지 (`offcut.app`).

### 라이선스 / 배포
- **번들 ffmpeg를 LGPL 빌드로 전환** (BtbN ffmpeg-master-latest-win64-lgpl)
  본 앱은 MIT 라이선스이며, 이전 GPL 빌드 번들 시 라이선스 전파 우려가 있어 LGPL 빌드로 통일.
  HW 인코더(NVENC/QSV/AMF) 모두 LGPL 빌드에 포함되어 있어 녹화 품질·성능에는 영향 없음.
- 인코더 SW fallback을 `libx264`(GPL) → `mpeg4`(FFmpeg 내장)로 변경.
  하드웨어 인코더가 없는 환경에서 화질이 H.264 대비 약간 낮아지지만 호환성은 동일.
- `THIRD_PARTY_LICENSES.md` 추가 — 번들된 모든 의존성 라이선스 명시.
- README에 Windows SmartScreen "보호함" 다이얼로그 대처법 추가.
- `.github/ISSUE_TEMPLATE/` 추가 — 버그 제보·기능 요청 템플릿.

### 빌드 스크립트
- `tools/package.py`: ffmpeg 자동 다운로드 URL을 BtbN LGPL 빌드로 변경.
- 시스템 PATH의 ffmpeg가 GPL 빌드일 수 있어, PATH 복사 로직을 제거하고
  명시적으로 LGPL 빌드만 사용하도록 단순화.

## v1.0.1 — 2026-05-17

### 신규 기능
- 종료 시 OFFCUT STUDIO 광고 다이얼로그 (assets/exit_ad.png 자동 인식, 없으면 텍스트 카드 fallback)
- GitHub Releases 무료 배포 준비 (LICENSE, README, .gitignore)

## v1.0.0 — 2026-05-17

### 신규 기능
- 화면 녹화 (MP4, NVENC/QSV/AMF 자동 하드웨어 인코더)
- GIF 녹화 (2-pass palettegen, 720p 12fps lanczos)
- 녹화 중 ● REC pill 위젯 (영역 회피 자동 배치)
- 사진/영상/도구 3그룹 도크 구조
- PrtSc 키 가로채기 옵션 (도크 우클릭 메뉴 토글)
- 단축키 [테스트] 버튼 (충돌 자가 진단)
- 단축키 [기본값으로 초기화] 버튼
- 도크 우클릭 → 정보/진단 메뉴 (버전 + ffmpeg/PySide6 정보 + 로그 폴더 열기)
- 로그 파일 시스템 (`~/.ssakkimchi/logs/ssakkimchi.log`, 5MB×3 rotate)
- uncaught exception/Qt 메시지 자동 로깅
- 배포 패키징 한 방 스크립트 (`package.bat`)

### 버그 수정
- 부분캡처 `_compute_virtual_geom` NameError (어느 순간부터 안 됨)
- 듀얼 모니터에서 가상 데스크톱 overlay가 mouse event 못 받는 Qt6 이슈 → 마우스 있는 화면 1개만 덮도록
- `Signal(Path, str)` Qt 타입 미인식 → `Signal(object, str)`
- 시스템 부하 시 중복 인스턴스 가능 → timeout 200ms→800ms ×3회 retry
- 녹화 stop이 UI 326ms 블록 → 데몬 스레드 비동기화로 0.5ms (600× 개선)
- 부모 프로세스 강제 종료 시 ffmpeg 좀비 → Windows Job Object로 0
- 녹화 영역 영상에 도크 박힘 → 녹화 중 도크 hide 유지
- GIF 변환 cancel 시 subprocess 살아남음 → worker가 Popen handle 저장 + kill

### 개선
- 기본 단축키 `Ctrl+Shift+숫자` → `Alt+숫자` (한 손)
- 캡처 후 폴더 자동 열기 (이미지: 폴더 열기 버튼, 영상: explorer /select)
- 한글 경로에서 ffmpeg 못 다루는 문제 → 임시 영문 폴더 작업 후 이동
- 임시 파일 자동 청소 (앱 시작 시 + 작업 종료 후)
- ffmpeg 캐시가 stale일 때 (파일 삭제됨) 자동 재탐색
- stderr=DEVNULL로 장시간 녹화 시 파이프 풀 데드락 방지
- 5개 RegionCaptureOverlay 인스턴스 → 1개 공유로 통합 (메모리 절감)

### 측정 (사용자 PC, NVENC)
- 1080p30 녹화: ~390 kbps (조용한 화면), 30fps 일정, frame drop 0
- stop latency: 326ms (UI 블록 0.5ms)
- GIF 변환: 3s→0.65s, 6s→0.99s, 12s→1.76s
