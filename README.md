# 싹싹김치 캡처 (Ssak Kimchi Capture)

Windows용 가벼운 화면 캡처 + 녹화 + GIF + OCR + 색 추출 + 거리 측정 도구.
**도크 하나**로 끝나는 직관적인 UX, **Alt+1~9 한 손 단축키**, **하드웨어 가속 녹화**.

> 📦 GitHub 리포 만드는 중. 아래 링크가 `gyqls051/ssakssak-capture` 형태로 남아있는 곳은 곧 채워질 예정.

## 다운로드

[**최신 인스톨러 다운로드 →**](https://github.com/gyqls051/ssakssak-capture/releases/latest)

`Setup_SsakKimchiCapture_X.X.X.exe` 한 개만 다운로드 → 더블클릭 → 다음 → 설치. 끝.

> ⚠️ **Windows에서 "보호함" 경고가 뜨면?**
> 코드 서명 인증서를 붙이지 않은 무료 배포라 처음에는 SmartScreen이 "Windows에서 PC 보호함" 다이얼로그를 띄울 수 있어요.
> **"추가 정보" → "실행"** 을 누르면 정상 설치돼요. 신뢰가 가지 않는다면 [소스에서 직접 빌드](#3-소스에서-직접)하는 방법도 안내해두었어요.

## 기능

| 그룹 | 기능 | 단축키 |
|---|---|---|
| 📸 사진 | 부분 캡처 | `Alt+1` |
|  | 전체 캡처 | `Alt+2` |
|  | 창 캡처 | `Alt+3` |
|  | 스크롤 캡처 | `Alt+4` |
| 🛠 도구 | 색 추출 | `Alt+5` |
|  | 거리 측정 | `Alt+6` |
|  | OCR (텍스트 추출) | `Alt+7` |
| 🎥 영상 | 화면 녹화 (MP4) | `Alt+8` |
|  | GIF 녹화 | `Alt+9` |

### 캡처
- 부분/전체/창/스크롤 캡처 4종 모두 클립보드 + 파일 저장
- 듀얼 모니터 지원 (마우스가 있는 모니터 자동 인식)

### 녹화
- ffmpeg 내장 (별도 설치 불필요, LGPL 빌드)
- **자동 하드웨어 인코딩**: NVENC (NVIDIA) / QSV (Intel) / AMF (AMD)
- 하드웨어 인코더가 없으면 mpeg4 SW fallback (호환성 우선)
- 1080p30 ≈ 390 kbps (NVENC 기준), frame drop 0
- 정지 시 UI 0.5ms 블록 (비동기 인코딩)
- 좀비 프로세스 방지 (Windows Job Object)

### GIF
- 2-pass palettegen 고품질 (720p 12fps lanczos)
- 12초 → 1.76초 인코딩

### 기타
- 트레이 아이콘 / 도크 자동 숨김 / PrtSc 가로채기 옵션
- 단축키 [충돌 테스트] / [기본값 초기화]
- 로그 시스템 (`~/.ssakkimchi/logs/ssakkimchi.log`) + 진단 정보 복사

## 설치

### 1. 인스톨러 (추천)
[Releases](https://github.com/gyqls051/ssakssak-capture/releases/latest) 에서 `Setup_SsakKimchiCapture_X.X.X.exe` 다운로드 → 더블클릭.

### 2. 포터블 ZIP
[Releases](https://github.com/gyqls051/ssakssak-capture/releases/latest) 에서 `싹싹김치 캡처.zip` → 압축 풀고 `싹싹김치 캡처.exe` 실행.

### 3. 소스에서 직접
```powershell
git clone https://github.com/gyqls051/ssakssak-capture.git
cd ssakssak-capture
pip install -r requirements.txt
python main.py
```

## 빌드

```powershell
package.bat
```

자동으로:
1. `bin/ffmpeg.exe` 확보 (BtbN LGPL 빌드 자동 다운로드, 또는 기존 파일 사용)
2. PyInstaller 빌드
3. `dist/싹싹김치 캡처.zip` 생성
4. Inno Setup 있으면 `dist/Setup_SsakKimchiCapture_X.X.X.exe` 인스톨러도 생성

요구사항: Python 3.11+, PyInstaller, (선택) Inno Setup 6.

> ⚠️ 시스템 PATH에 GPL 빌드 ffmpeg를 깔아두셨다면 `bin/ffmpeg.exe`를 한 번 비우고 빌드하세요.
> `package.py`가 `bin/`이 비어 있을 때만 BtbN LGPL 빌드를 새로 다운받습니다.

## 시스템 요구사항
- Windows 10 / 11
- 64-bit
- ~200MB 디스크 (ffmpeg 포함)

## 트러블슈팅
- **단축키 충돌**: 도크 우클릭 → 단축키 설정 → [테스트] 버튼
- **녹화 실패**: 도크 우클릭 → 정보/진단 에서 ffmpeg/인코더 확인
- **로그 위치**: `C:\Users\<사용자>\.ssakkimchi\logs\ssakkimchi.log`
- **SmartScreen "PC 보호함" 다이얼로그**: "추가 정보" → "실행" (위 [다운로드](#다운로드) 섹션 참고)

## 라이선스
이 앱(소스 코드)은 **MIT** — 자세한 내용은 [LICENSE](LICENSE) 참고.

번들된 ffmpeg 및 의존성 라이선스는 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) 참고.
주요 의존성 중 일부(ffmpeg, PySide6, pynput)는 LGPL로 배포되며, 본 앱은 동적 링크/별도 프로세스 호출 방식으로만 사용해 MIT 라이선스를 유지합니다.

## 기여 / 버그 제보
- 버그 제보: [Issues](https://github.com/gyqls051/ssakssak-capture/issues/new/choose)
- 진단 정보를 첨부해주시면 더 빠르게 잡을 수 있어요 (도크 우클릭 → 정보 / 진단 → [진단 정보 복사])

## 변경 이력
[CHANGELOG.md](CHANGELOG.md)
