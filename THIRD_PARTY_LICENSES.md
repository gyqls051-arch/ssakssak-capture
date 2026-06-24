# Third-Party Licenses

싹싹김치 캡처(Ssak Kimchi Capture) 빌드 산출물에는 아래 제3자 소프트웨어가 포함되거나 함께 배포됩니다.
본 앱의 소스 코드는 [MIT 라이선스](LICENSE)이며, 아래 컴포넌트들은 각자의 라이선스 조건에 따릅니다.

---

## 1. Python 런타임 및 표준 라이브러리

- **라이선스**: Python Software Foundation License (PSF-2.0)
- **출처**: https://www.python.org/
- **포함 방식**: PyInstaller가 Python 인터프리터와 표준 라이브러리를 인스톨러에 동적 포함

---

## 2. PySide6 (Qt for Python)

- **라이선스**: LGPLv3 (with Qt 예외 조항)
- **출처**: https://www.qt.io/qt-for-python
- **버전**: ≥ 6.6
- **사용 방식**: PyInstaller가 PySide6 동적 라이브러리(.pyd/.dll)를 번들. 본 앱은 PySide6를 동적으로 import하여 사용 (정적 링크 없음). LGPLv3 의무 사항 준수.
- **사용자 권리**: 본 앱에 번들된 PySide6/Qt 라이브러리를 다른 호환 버전으로 교체할 수 있습니다. 교체 절차는 PyInstaller 빌드 폴더 내 동일 이름의 `.pyd`/`.dll` 파일을 호환 버전으로 덮어쓰기 하시면 됩니다.

---

## 3. mss

- **라이선스**: MIT
- **출처**: https://github.com/BoboTiG/python-mss
- **버전**: ≥ 9.0
- **용도**: 화면 캡처 (스크린샷)

---

## 4. pynput

- **라이선스**: LGPLv3
- **출처**: https://github.com/moses-palmer/pynput
- **버전**: ≥ 1.7
- **용도**: 글로벌 단축키 (Alt+1~9)
- **사용 방식**: 동적 import. 사용자가 호환 버전으로 교체 가능.

---

## 5. Pillow (PIL Fork)

- **라이선스**: MIT-CMU (HPND License)
- **출처**: https://github.com/python-pillow/Pillow
- **버전**: ≥ 10.0
- **용도**: 이미지 처리

---

## 6. NumPy

- **라이선스**: BSD 3-Clause
- **출처**: https://numpy.org/
- **버전**: ≥ 1.24
- **용도**: 픽셀 배열 처리

---

## 7. PyInstaller

- **라이선스**: GPLv2+ (with bootloader 예외 조항 — 빌드 결과물은 영향 받지 않음)
- **출처**: https://pyinstaller.org/
- **버전**: ≥ 6.0
- **포함 방식**: 빌드 도구로만 사용. 사용자에게 배포되는 인스톨러에는 PyInstaller 자체가 포함되지 않으며, 부트로더만 들어갑니다. PyInstaller 부트로더는 명시적 예외 조항(Section 9 of the GPL exception)에 따라 GPL 전파 대상이 아닙니다.

---

## 8. Windows SDK (winsdk)

- **라이선스**: MIT
- **출처**: https://github.com/Microsoft/xlang
- **포함 조건**: `sys_platform == "win32"`
- **용도**: Windows OCR API (Windows.Media.Ocr) 호출

---

## 9. FFmpeg

- **라이선스**: **LGPLv2.1+** (BtbN LGPL build, `ffmpeg-master-latest-win64-lgpl`)
- **출처**: https://github.com/BtbN/FFmpeg-Builds
- **공식 사이트**: https://ffmpeg.org/
- **소스 코드**: https://github.com/FFmpeg/FFmpeg
- **버전**: master-latest (자동 다운로드, 빌드 시점의 최신)
- **사용 방식**:
  - `ffmpeg.exe`는 별도 프로세스로 `subprocess.Popen()`을 통해 호출됩니다.
  - 본 앱과 FFmpeg는 파일 시스템 + 표준 입출력만으로 통신하며, 정적/동적 링크 관계가 아닙니다.
- **사용자 권리**: 번들된 `ffmpeg.exe`를 다른 호환 LGPL 빌드로 교체할 수 있습니다.
  설치 폴더 내 `싹싹김치 캡처/_internal/bin/ffmpeg.exe` (인스톨러 설치 시) 또는 `bin/ffmpeg.exe`를 덮어쓰기 하면 됩니다.
- **포함된 외부 라이브러리 (LGPL 빌드)**:
  - libvpx, libvorbis, libopus, libmp3lame, libwebp, libfreetype, libfribidi, libharfbuzz 등
  - GPL 컴포넌트(libx264, libx265, libxvid, libvidstab 등)는 **포함되지 않음**

---

## 10. Inno Setup (인스톨러 컴파일러)

- **라이선스**: Modified BSD-3 (Inno Setup License)
- **출처**: https://jrsoftware.org/isinfo.php
- **포함 방식**: 빌드 도구로만 사용. 인스톨러 산출물에는 Inno Setup 런타임만 들어가며, 이는 자유롭게 재배포 가능.

---

## LGPL 컴포넌트에 대한 사용자 권리

본 앱은 LGPL 컴포넌트(PySide6, pynput, ffmpeg)를 다음 방식으로 사용합니다:

| 컴포넌트 | 사용 방식 | LGPL 의무 충족 |
|---|---|---|
| PySide6 | 동적 import (`.pyd`/`.dll`) | ✅ 사용자가 호환 버전 교체 가능 |
| pynput | 동적 import | ✅ 사용자가 호환 버전 교체 가능 |
| FFmpeg | 별도 프로세스 (subprocess) | ✅ 사용자가 `ffmpeg.exe` 교체 가능 |

LGPL 라이선스 전문은 각 컴포넌트의 공식 저장소에서 확인 가능합니다:
- LGPLv2.1: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
- LGPLv3: https://www.gnu.org/licenses/lgpl-3.0.html

---

## 라이선스 관련 문의

라이선스 의무 위반으로 보이는 부분이 있으면 [Issues](https://github.com/gyqls051/ssakssak-capture/issues/new)로 알려주세요. 즉시 검토하고 수정하겠습니다.
