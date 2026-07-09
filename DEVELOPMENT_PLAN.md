# 싹싹김치 캡처 — 개발 계획 & 작업 지시서

작성: 2026-07-06 (전체 코드 리뷰 세션. 6,400줄 / 36모듈 전수 검토 + 번들 ffmpeg 인코더 실측 기반)
기준 커밋: `343786b` (main)

## 0. 이 문서 사용법

- **실행 단위는 "작업 ID" (W-1, F-2, P-3 …)** 이다. 각 항목은 `근거(현재 코드) → 수정 지시 → 완료 기준 → 검증` 구조라서, 새 Claude Code 세션에서 이 문서만 열고 해당 ID를 지목하면 바로 작업 가능하다.
- 작업이 끝나면 이 문서의 체크박스를 채우고, 프로젝트 규칙대로 **`CLAUDE.md`의 "현재 상태" + "작업 이력"에 한 줄 추가**한다.
- Phase 순서는 의존 관계를 반영한 것: **W-1(좌표 헬퍼)이 W-2, F-1, F-2, P-3의 토대**이므로 반드시 먼저.
- 각 Phase = 릴리즈 1개. Phase 완료 시 `ssakkimchi/version.py` bump → `CHANGELOG.md` → `package.bat` → 릴리즈 재첨부(§8 체크리스트).

## 1. 점검 결과 요약 (2026-07-06 리뷰)

| ID | 항목 | 심각도 | Phase |
|---|---|---|---|
| W-2 | 창 캡처: DPI 배율 모니터에서 좌표 이중 변환 (125~150% 노트북에서 캡처 어긋남) | **P0 버그** | 1 |
| W-3 | 전체 캡처가 커서가 아닌 "도크가 있는 모니터"를 캡처 | P1 버그 | 1 |
| W-4 | SW 인코더 폴백이 mpeg4 (번들 ffmpeg에 h264_mf·libopenh264 있는데 미사용) | P1 개선 | 1 |
| W-5 | 프리뷰 카드의 explorer `/select,` 인자 분리 (파일 선택 안 될 수 있음) | P2 버그 | 1 |
| W-6 | mss grab 실패 시 None이 `_deliver_capture`까지 흘러 TypeError | P2 버그 | 1 |
| W-7 | settings.json 저장이 비원자적 (크래시 시 파손) | P2 버그 | 1 |
| W-8 | 핫키 리스너 시작 실패가 무음 (단축키 전멸해도 사용자 모름) | P2 버그 | 1 |
| F-1 | 오버레이 hide() 직후 grab — 컴포지터 레이스 (흰 테두리/딤 유입 가능) → 프리즈 프레임 | P1 개선 | 2 |
| F-2 | 색 추출·거리 측정·창 캡처 오버레이가 가상 데스크톱 전체를 덮음 (직접 발견한 Qt6 듀얼모니터 이슈 미적용) | P1 검증+수정 | 2 |
| F-3 | 스크롤 캡처 스티칭이 UI 스레드 동기 실행 (수 초 프리즈 가능) | P1 개선 | 2 |
| F-4 | OCR 결과를 눈으로 확인/수정할 UI 없음 (토스트+클립보드뿐) | P2 개선 | 2 |
| P-1 | 핀(화면에 캡처 고정) — ScreenFloat 핵심 기능 부재 | 기능 | 3 |
| P-2 | 지연 캡처 (3/5/10초) | 기능 | 3 |
| P-3 | 마지막 영역 반복 캡처 | 기능 | 3 |
| P-4 | Windows 시작 시 자동 실행 토글 | 기능 | 3 |
| A-1 | 캡처 후 주석(annotation) 에디터 | 대형 기능 | 4 |
| B-* | RapidOCR / 업데이트 체크 / ddagrab / 오디오 / 히스토리 / 포맷 옵션 / 테스트 | 백로그 | — |

**리뷰 총평**: 아키텍처·수명관리(Job Object, atexit PrtSc 복원, OCR 워커 detach, 비동기 ffmpeg stop)는 견고. 문제는 대부분 **DPI/멀티모니터 좌표계**에 몰려 있고, 이는 "친구 PC 첫 설치 테스트"(배율 125~150% 노트북일 확률 높음)에서 바로 드러날 항목이라 Phase 1이 배포 전 필수다.

---

## 2. 로드맵

```
Phase 1  v1.0.3  정확성 핫픽스        W-1 ~ W-8   ✅ 코드 완료 (2026-07-08)
Phase 2  v1.0.4  캡처 파이프라인 견고화  F-1 ~ F-4   ✅ 코드 완료 (2026-07-08) — v1.0.3+1.0.4 합본으로 빌드/실기테스트/릴리즈 남음
Phase 3  v1.1.0  차별화 기능          P-1 ~ P-4   (2~3일)
Phase 4  v1.2.0  주석 에디터          A-1         (3~5일, 별도 설계)
백로그    —       B-1 ~ B-7           수시
```

의존 관계: `W-1 → {W-2, F-1, F-2, P-3}` / `F-1 → F-2(부분)` / 나머지는 독립.

---

## 3. Phase 1 — 정확성 핫픽스 (v1.0.3)

> **✅ 2026-07-08 W-1~W-8 전부 구현 + 검증 완료.** 남은 것: `package.bat` 빌드 → §8 테스트 매트릭스(특히 150% 배율) → 릴리즈.
> 구현 중 계획과 달라진 점 2가지:
> ① **QScreen.name() 매칭 불가** — Qt6는 GDI 장치명(`\\.\DISPLAY1`)이 아니라 모델명("BenQ GW2480 (1)")을 반환(실측). coords.py는 이름 매칭 대신 **원점 정렬 순서 + 크기 검증(논리×dpr==물리)** 위상 매칭으로 구현. 검증 실패 시 논리×dpr 폴백.
> ② **기존 mpeg4 폴백이 원래부터 죽어 있었음** — `-vtag xvid`를 번들 ffmpeg(최신 BtbN)가 거부해 녹화 자체가 실패("Tag xvid incompatible with mp4v"). v1.0.2의 잠재 버그. 태그 제거로 수정, 실녹화 검증 완료.

### ☑ W-1. 좌표 변환 헬퍼 모듈 `ssakkimchi/coords.py` 신설 (토대 작업)

**배경**: Qt6는 Per-Monitor DPI Aware v2로 실행된다. 따라서
- Win32 API(`GetWindowRect`, `DwmGetWindowAttribute EXTENDED_FRAME_BOUNDS`, `GetCursorPos`, `EnumDisplayMonitors`)는 **물리 픽셀**을 반환하고,
- Qt(`QScreen.geometry()`, `event.globalPosition()`)는 **논리 픽셀**이다.
- mss는 **물리 픽셀**을 받는다.

현재 코드는 "논리 × dpr = 물리"로 일괄 가정하는데([capture_core.py:19-25](ssakkimchi/capture_core.py#L19-L25)), 이 등식은 **해당 모니터의 물리 원점과 논리 원점이 dpr 배율 관계일 때만** 성립한다(단일 모니터·주 모니터에선 참, 배율 다른 보조 모니터에선 거짓). 정확한 변환에는 모니터별 물리 원점이 필요하다.

**지시**:
1. 새 파일 `ssakkimchi/coords.py` 생성. Win32 `EnumDisplayMonitors` + `GetMonitorInfoW`(MONITORINFOEXW)로 `[(szDevice, 물리 QRect)]`를 얻고, `QScreen.name()`(예: `\\.\DISPLAY1`)과 szDevice를 매칭해 QScreen↔물리 rect 쌍을 만든다. 비-Windows/매칭 실패 시 기존 `논리×dpr` 방식으로 폴백.
2. 공개 API (모두 폴백 내장):
   ```python
   def screen_physical_geometry(screen: QScreen) -> QRect          # 해당 스크린의 물리 rect
   def logical_to_physical(point_or_rect, screen: QScreen)          # 논리→물리
   def physical_to_logical(point_or_rect) -> ...                    # 물리→논리 (포함 모니터 자동 탐색)
   def cursor_physical_pos() -> QPoint                              # GetCursorPos (물리)
   ```
   변환식(모니터 M, 스크린 S 매칭 시): `물리 = M.origin + (논리 - S.geometry().topLeft()) × S.dpr`, 역변환은 그 반대.
3. 모니터 목록은 호출 시마다 열거해도 되지만(캡처 빈도 낮음), 간단히 0.5~1초 TTL 캐시를 둬도 좋다. 디스플레이 구성 변경(WM_DISPLAYCHANGE)을 따로 처리하지 않아도 되는 이유가 캐시 TTL이다.
4. `win_job.py`처럼 모듈 최상단 docstring에 전제(PMv2)를 명기.

**완료 기준**: 단일 모니터 100%에서 기존 결과와 동일. 배율 150% 모니터에서 `screen_physical_geometry(primaryScreen)` == 실제 해상도(예: 1920×1080, 논리 1280×720일 때).
**검증**: `python -c`로 QApplication 띄우고 각 스크린의 논리/물리 rect 출력 → 디스플레이 설정과 대조. (개발 PC가 100%뿐이면 Windows 설정에서 임시로 150% 변경해 확인 — 테스트 후 복원.)

### ☑ W-2. 창 캡처 DPI 이중 변환 수정 (P0)

**근거**:
- [window_capture.py:267](ssakkimchi/window_capture.py#L267) — DWM에서 받은 **물리** rect에 `region_dict(rect, dpr)`로 dpr을 또 곱함 → 배율≠100% 모니터에서 캡처 영역이 크고 어긋남.
- [window_capture.py:155-157](ssakkimchi/window_capture.py#L155-L157), [159-164](ssakkimchi/window_capture.py#L159-L164) — Qt **논리** 좌표(`event.globalPosition()`)를 물리 좌표인 DWM rect와 직접 비교(히트테스트) → 같은 조건에서 엉뚱한 창 선택.
- [window_capture.py:134-147](ssakkimchi/window_capture.py#L134-L147) — `set_target`이 물리 rect를 논리 오버레이 좌표에 그대로 그림 → 하이라이트 위치 어긋남.

**지시** (W-1 완료 후):
1. **grab**: `_handle_click`에서 `grab_qimage({"left": l, "top": t, "width": w, "height": h})` — **dpr 곱하지 말 것**. DWM rect는 이미 물리.
2. **히트테스트**: `_update_target_under`/`_handle_click`에 넘기는 좌표를 `coords.cursor_physical_pos()`로 교체(마우스 이벤트는 트리거로만 쓰고 좌표는 Win32에서 읽음). `_window_at_excluding`은 물리 좌표 비교이므로 그대로 두면 정합.
3. **하이라이트**: `set_target`에서 물리 rect → `coords.physical_to_logical()` → 오버레이 로컬 좌표(`- virtual_geom.topLeft()`) 순으로 변환 후 그리기.
4. 캡처 결과 QImage에 `setDevicePixelRatio`는 걸지 않는다(저장 PNG는 물리 픽셀 그대로가 맞음 — 현행 유지).

**완료 기준**: 150% 배율 모니터에서 ① 하이라이트가 창 테두리에 정확히 붙고 ② 저장 PNG 크기 = 창의 물리 픽셀 크기, 내용 어긋남 없음. 100% 모니터에서 기존과 동일.
**검증**: 배율 150%로 바꾼 뒤 메모장 창 캡처 → PNG를 열어 창 경계 확인. 듀얼 모니터면 양쪽 각각.

### ☑ W-3. 전체 캡처 대상 = 커서가 있는 모니터

**근거**: [app.py:390-395](ssakkimchi/app.py#L390-L395)가 `self._dock.screen()` 기준. 도크를 오른쪽 모니터에 두고 왼쪽에서 작업하면 엉뚱한 화면이 찍힌다. 부분 캡처는 이미 커서 기준([region_capture.py:17-25](ssakkimchi/region_capture.py#L17-L25)).

**지시**: `start_full_capture`에서 `screen = QGuiApplication.screenAt(QCursor.pos()) or self._dock.screen() or QGuiApplication.primaryScreen()`으로 교체. `capture_screen_image`는 그대로.
단, 내부의 `grab_rect(geom, dpr)`([full_capture.py:7-12](ssakkimchi/full_capture.py#L7-L12))도 W-1의 `coords.screen_physical_geometry(screen)`을 쓰도록 바꾸면 혼합 DPI에서 정확해진다 (권장, 5분 작업).

**완료 기준**: 듀얼 모니터에서 커서를 둔 쪽이 찍힘.

### ☑ W-4. SW 인코더 폴백 교체: mpeg4 → h264_mf / libopenh264
> 완료 노트: h264_mf(22KB/2s)·libopenh264(22KB/2s)·mpeg4(48KB/2s) 실녹화 rc=0 확인.
> 자동 재시도는 `RecordingController._launch()` 분리 + `_on_tick`에서 elapsed<2s 사망 시 다음 후보로 구현.
> 추가 발견: 기존 mpeg4 인자의 `-vtag xvid`가 번들 ffmpeg에서 거부되어 제거(§Phase 1 헤더 노트 ②).

**근거**: 번들 `bin/ffmpeg.exe`(BtbN LGPL) 인코더 목록 실측 결과 **`h264_mf`(Windows Media Foundation)와 `libopenh264` 둘 다 포함**되어 있음을 확인함(2026-07-06). 현재 HW 인코더 없는 PC는 MPEG-4 Part 2로 폴백([ffmpeg_runtime.py:30](ssakkimchi/ffmpeg_runtime.py#L30), [149-157](ssakkimchi/ffmpeg_runtime.py#L149-L157)) — 화질·웹 업로드 호환성 모두 H.264보다 나쁘다.

**지시**:
1. [ffmpeg_runtime.py:30](ssakkimchi/ffmpeg_runtime.py#L30) 우선순위를 다음으로:
   ```python
   _ENCODER_PREFERENCE = ("h264_nvenc", "h264_qsv", "h264_amf", "h264_mf", "libopenh264", "mpeg4")
   ```
   - `h264_mf`를 libopenh264보다 앞에 두는 이유: OS 제공 인코더라 특허 라이선스 논점이 없고(OpenH264는 직접 컴파일 바이너리라 Cisco 무상 라이선스 범위 밖) 품질도 무난. 단 일부 환경에서 MF 인코더 초기화가 불안정하다는 보고가 있으니 **테스트에서 h264_mf 녹화가 실패하면 순서를 뒤집는다** (아래 3번 참고).
2. [ffmpeg_runtime.py:123-157](ssakkimchi/ffmpeg_runtime.py#L123-L157) `encoder_args`에 분기 추가:
   ```python
   if encoder == "h264_mf":
       return ["-c:v", "h264_mf", "-b:v", "6M", "-pix_fmt", "yuv420p"]
   if encoder == "libopenh264":
       return ["-c:v", "libopenh264", "-b:v", "5M", "-maxrate", "7M", "-pix_fmt", "yuv420p"]
   ```
3. **런타임 안전망(중요)**: 녹화 시작 후 ffmpeg가 2초 안에 죽으면(현재 `_on_tick`이 감지, [recording.py:297-306](ssakkimchi/recording.py#L297-L306)) 지금은 그냥 실패 토스트다. `RecordingController.start()`에 "선택 인코더로 Popen 후 첫 tick에서 사망 감지 시 → 다음 우선순위 인코더로 1회 자동 재시도" 로직을 넣거나, 최소한 실패 메시지에 인코더 이름을 포함해 진단 가능하게 한다. (자동 재시도 권장 — HW 인코더 오탐지 케이스까지 커버됨.)
4. 잔재 정리: [recording.py:242](ssakkimchi/recording.py#L242) `or "libx264"` → `or "mpeg4"`, [recording.py:8](ssakkimchi/recording.py#L8) docstring의 "libx264" 문구 수정 (LGPL 정책과 불일치하는 표기).

**완료 기준**: `_ENCODER_PREFERENCE`에서 HW 3종을 임시 제거하고 녹화 → h264_mf로 mp4 생성·재생 확인, libopenh264도 동일 확인 후 원복.
**검증**: 위 임시 테스트 + 진단 다이얼로그(정보/진단)에서 encoder 표기 확인.

### ☑ W-5. explorer `/select` 인자 통일 (신규 `ssakkimchi/shell_utils.py`)

**근거**: [capture_preview.py:201](ssakkimchi/capture_preview.py#L201) `["explorer", "/select,", str(path)]` — 콤마와 경로가 분리되면 파일 선택이 안 되고 폴더만 열리는 환경이 있다. [app.py:614-616](ssakkimchi/app.py#L614-L616)은 올바른 결합형.

**지시**: app.py의 `_reveal_in_explorer`를 재사용하도록 통일. 방법: `_reveal_in_explorer`를 `capture_storage.py`나 새 `shell_utils.py`로 옮겨 `reveal_in_explorer(path)` 함수로 만들고, app.py와 capture_preview.py 둘 다 그걸 호출 (`CREATE_NO_WINDOW` 플래그 포함).

### ☑ W-6. grab 실패(None) 가드

**근거**: `grab_rect`/`grab_qimage`는 실패 시 None 반환([capture_core.py:28-49](ssakkimchi/capture_core.py#L28-L49)). `capture_screen_image`가 None을 그대로 반환하면 `_deliver_capture`의 `clipboard.setImage(None)`에서 TypeError([app.py:385-388](ssakkimchi/app.py#L385-L388)). 잠금 화면·보안 데스크톱 전환 직후 등에서 발생 가능.

**지시**: `_deliver_capture` 진입부에 `if image is None or image.isNull(): Toast.show_text("캡처 실패"); return` 가드 1개 추가 (모든 경로가 이 함수를 지나므로 여기 한 곳이면 충분).

### ☑ W-7. settings.json 원자적 저장

**근거**: [settings.py:18-21](ssakkimchi/settings.py#L18-L21)은 `write_text` 직접 — 쓰는 도중 크래시하면 파손. [storage.py:44-49](ssakkimchi/storage.py#L44-L49)는 이미 tmp+`replace` 원자적.

**지시**: `_save`를 storage.py와 같은 패턴(`.json.tmp`에 쓰고 `tmp.replace(path)`)으로 교체.

### ☑ W-8. 핫키 리스너 실패 피드백

**근거**: [hotkeys.py:194-198](ssakkimchi/hotkeys.py#L194-L198) — `GlobalHotKeys` 시작 실패 시 `except Exception: self._listener = None`로 무음 처리. 단축키가 전부 죽어도 사용자·로그 모두 흔적이 없다.

**지시**:
1. `HotkeyManager.start()`가 성공 여부 `bool`을 반환하게 하고, 실패 시 `log.exception(...)` 기록 (`logging_setup.get_logger("hotkeys")`).
2. [app.py:129-132](ssakkimchi/app.py#L129-L132) `start()`와 [app.py:238-248](ssakkimchi/app.py#L238-L248) `open_hotkey_dialog` 저장 경로에서 반환값이 False면 `Toast.show_text("전역 단축키 등록 실패 — 도크/트레이로 이용 가능", 3000)`.
3. 잘못된 조합 문자열 1개 때문에 전체가 죽지 않도록: 조합별로 try — pynput `GlobalHotKeys`는 파싱을 생성자에서 일괄 하므로, 생성 실패 시 조합을 하나씩 검증(`_pkb.HotKey.parse(combo)`)해 나쁜 것만 빼고 재시도하는 로직 추가.

**Phase 1 릴리즈**: `version.py` → 1.0.3, CHANGELOG 갱신, §8 체크리스트 수행.

---

## 4. Phase 2 — 캡처 파이프라인 견고화 (v1.0.4)

> **✅ 2026-07-08 F-1~F-4 코드 완료 + 오프스크린 스모크 통과.** 구현 노트:
> - F-1: frozen 모드에서 선택 영역 바깥 4조각만 딤(픽스맵 부분 재드로우의 DPR 좌표 모호성 회피). hide 시 프레임 해제. grab 실패 시 라이브 모드 자연 폴백.
> - F-2: 색 추출·거리 측정은 단일 모니터로 전환 완료(`capture_core.active_screen_info()` 공용화). **창 캡처는 가상 데스크톱 유지** — 화면 넘나드는 선택이 필요해서. 듀얼모니터에서 창 캡처 마우스 이벤트 정상 여부는 사용자 실기 테스트로 확인할 것(문제 시 모니터당 오버레이 방식, §F-2 지시 3).
> - 알려진 한계(신규 백로그 B-8): 녹화/GIF/스크롤의 `region_selected(논리 rect, dpr)` 계약은 유지 — 배율 다른 **보조** 모니터에서 녹화 영역이 어긋날 수 있음(주 모니터/100%는 정확). 수정하려면 물리 rect 계약으로 바꾸고 REC pill 배치 좌표도 같이 손봐야 함.

### ☑ F-1. 프리즈 프레임 오버레이 (부분 캡처 / OCR)

**배경**: [region_capture.py:90-107](ssakkimchi/region_capture.py#L90-L107)는 `hide()` 직후 같은 핸들러에서 mss grab. DWM 합성 제거는 비동기라 ① 딤(검정 90α)이나 ② 선택 테두리 흰 1px(위/왼쪽 변은 `drawRect` 특성상 grab 영역 **안쪽**에 그려짐)이 결과물에 낄 수 있는 레이스가 있다. 또 라이브 화면을 나중에 찍으므로 드래그 중 콘텐츠가 바뀌면 의도와 다른 프레임이 찍힌다. 업계 표준(Snipping Tool, Shottr, Flameshot)은 **오버레이를 열 때 화면을 얼려서 그 이미지 위에서 선택·크롭**한다.

**지시**:
1. `RegionCaptureOverlay.begin()`에 `freeze: bool = True` 파라미터 추가.
   - freeze=True (region/ocr 모드): `coords.screen_physical_geometry(활성 스크린)`으로 mss grab → `self._frozen: QImage`(물리 크기) 보관.
   - freeze=False (record/gif/scroll 모드): 현행 라이브 방식 유지. **이 모드들은 오버레이가 픽셀을 grab하지 않으므로(rect만 emit) 레이스 자체가 없다** — 라이브 화면을 보며 영역을 잡는 UX가 더 좋으니 유지.
2. `paintEvent` (frozen일 때):
   ```python
   pm = self._frozen_pixmap  # QPixmap.fromImage(frozen); pm.setDevicePixelRatio(self._dpr) 를 begin에서 1회
   painter.drawPixmap(0, 0, pm)                    # 배경 = 얼린 화면
   painter.fillRect(self.rect(), QColor(0, 0, 0, 90))  # 딤
   # 선택 영역: CompositionMode_Clear 대신, 얼린 픽스맵의 해당 부분을 딤 없이 다시 그림
   painter.drawPixmap(sel_rect, pm, physical_subrect(sel_rect))
   ```
   `WA_TranslucentBackground`의 투명 구멍 트릭은 frozen 모드에선 불필요해진다.
3. `mouseReleaseEvent`: grab 대신 `self._frozen.copy(logical_to_physical_local(sel_rect))`로 크롭해 `captured` emit. **hide 타이밍과 무관해져 레이스 소멸.**
4. [app.py:325-352](ssakkimchi/app.py#L325-L352) `_begin_shared_overlay`에서 모드별 freeze 값 전달.
5. 부수 효과: freeze grab도 W-1 좌표 헬퍼를 쓰므로 혼합 DPI에서 부분 캡처가 정확해진다.

**완료 기준**: 부분 캡처 결과 가장자리에 흰 1px/딤 없음(확대해 픽셀 검사). 동영상 재생 중 드래그하면 "드래그 시작 시점" 프레임이 찍힘. record/gif/scroll 동작 불변.

### ☑ F-2. 오버레이 멀티모니터 전략 통일 (색/거리 완료, 창 캡처는 실기 확인 대기)

**배경**: CLAUDE.md에 "가상 데스크톱 전체를 덮으면 Qt6가 마우스 이벤트를 못 받음(BenQ 듀얼 실측)"이라 기록하고 region_capture만 단일 모니터로 고쳤는데, [color_picker.py:56,69](ssakkimchi/color_picker.py#L56), [distance_overlay.py:28,35](ssakkimchi/distance_overlay.py#L28), [window_capture.py:114,118](ssakkimchi/window_capture.py#L114)는 여전히 `virtual_desktop_geometry()`. 같은 조건에서 이 3개는 동일 증상이 재현될 수 있다.

**지시** (검증 → 수정 순서):
1. **먼저 듀얼 모니터에서 실측**: 색 추출/거리 측정/창 캡처가 양쪽 모니터에서 마우스 이벤트를 정상 수신하는지. 정상이면 이 항목은 "확인됨" 메모만 남기고 종료해도 된다(과거 이슈가 특정 조건이었을 가능성).
2. 재현되면: 색 추출·거리 측정은 **커서가 있는 모니터 1개만 덮도록** 변경 (region_capture의 `_active_screen_geometry()`를 `capture_core.py`로 승격해 공유). 두 기능 모두 점 기반이라 단일 화면으로 UX 손실이 거의 없다. 색 추출의 `_sample`([color_picker.py:117-157](ssakkimchi/color_picker.py#L117-L157))은 W-1 헬퍼로 물리 좌표 변환하도록 같이 정리.
3. 창 캡처는 화면을 넘나들며 창을 고르는 기능이라 단일 화면 제한이 아프다. 재현 시 **모니터당 오버레이 1개씩 띄우는 방식**(Flameshot 방식: QScreen마다 _HighlightOverlay 인스턴스, 시그널은 세션이 취합)으로 전환. 재현 안 되면 현행 유지.

**완료 기준**: 듀얼 모니터 양쪽에서 3개 기능 모두 정상 동작 확인 기록.

### ☑ F-3. 스크롤 캡처 스티칭 워커 스레드화

**배경**: [scroll_capture.py:101-114](ssakkimchi/scroll_capture.py#L101-L114) `stop()`이 UI 스레드에서 `_stitch_frames` 동기 실행. 프레임 수십 장 × 겹침 탐색(numpy 반복, [163-215](ssakkimchi/scroll_capture.py#L163-L215))이면 수 초 프리즈 가능.

**지시**:
1. `_StitchWorker(QThread)` 신설: 프레임 리스트를 받아 `run()`에서 `_stitch_frames` + `_pil_to_qimage` 수행(QImage는 비GUI 스레드 생성 안전; QPixmap만 금지), `done(QImage)` / `failed()` emit.
2. `stop()`: teardown 후 프레임<2면 기존대로 cancelled, 아니면 `Toast.show_text("이어붙이는 중…")` 후 워커 시작. 워커 완료 시 finished emit. recording.py의 `_GifConvertWorker` 패턴([recording.py:114-200](ssakkimchi/recording.py#L114-L200))을 그대로 따라 하면 된다 (`finished.connect(deleteLater)`, cancel 협조 포함).
3. `app.quit()` 경로에서 스크롤 컨트롤러가 스티칭 중이면 워커 cancel (기존 `_scroll_controller.cancel()` 확장).

**완료 기준**: 긴 페이지(프레임 30장+) 스크롤 캡처 중지 시 도크/토스트가 즉시 반응(프리즈 없음).

### ☑ F-4. OCR 결과 다이얼로그 (신규 `ssakkimchi/ocr_result_dialog.py`)

**배경**: [app.py:524-530](ssakkimchi/app.py#L524-L530) — 결과가 클립보드+토스트로만 감. 인식 오류를 눈으로 검수·부분 복사할 수 없다.

**지시**:
1. 새 파일 `ssakkimchi/ocr_result_dialog.py`: QDialog(프레임 있음, 크기 ~520×380), `QPlainTextEdit`(편집 가능, 결과 텍스트), 하단 버튼 [전체 복사] [닫기]. 스타일은 hotkey_dialog.py의 COLORS/FONT_FAMILY 패턴 재사용.
2. `_on_ocr_done`: 기존 자동 클립보드 복사는 유지하고, 그 위에 다이얼로그 표시. 빈 결과면 기존 토스트만.
3. 다이얼로그는 modeless(`show()`)로 — 화면과 대조하며 수정하는 용도이므로.

**Phase 2 릴리즈**: v1.0.4.

---

## 5. Phase 3 — 차별화 기능 (v1.1.0)

### ☐ P-1. 핀 — 캡처를 화면에 고정 (최우선 기능)

**배경**: ScreenFloat 감성을 표방하는데 그 핵심 기능이 없다. 캡처를 항상-위 플로팅 이미지로 띄워 참고하면서 작업하는 기능. 구현 난도 대비 체감 효과가 가장 크다.

**지시**:
1. 새 파일 `ssakkimchi/pin_window.py` — `PinWindow(QWidget)`:
   - 플래그: `FramelessWindowHint | WindowStaysOnTopHint | Tool` (기존 오버레이들과 동일 패턴).
   - `show_image(image: QImage, source_path: Path | None)`: 픽스맵 보관. `pixmap.setDevicePixelRatio(dpr)`로 초기 표시 크기 = 캡처의 논리 크기. 커서 근처 or 화면 중앙에 표시.
   - **드래그 이동**: mousePress에서 오프셋 저장 → mouseMove로 move (dock.py의 `DockHandle` 패턴 재사용, [dock.py:114-138](ssakkimchi/dock.py#L114-L138)).
   - **휠 줌**: 배율 0.25~4.0, 스텝 ×1.1, `SmoothTransformation` 스케일 후 `setFixedSize`. 창 크기만 바꾸고 원본은 보존.
   - **우클릭 메뉴**: 복사 / 다른 이름으로 저장… / 불투명도(100·85·70·50%) / 원본 크기(1:1) / 닫기. 메뉴 스타일 = `Dock._menu_stylesheet()` 재사용.
   - **더블클릭 or Esc**: 닫기. 테두리: 1px `border_solid` + 그림자(있으면 좋고).
2. 통합:
   - `CapturePreview`에 핀 버튼 추가([capture_preview.py:113-140](ssakkimchi/capture_preview.py#L113-L140) top_row에 아이콘 버튼 1개) → `pin_requested(QImage, object)` 시그널 → app.py가 `PinWindow` 생성.
   - app.py는 `self._pins: list[PinWindow]` 유지, 핀 닫힘 시 리스트에서 제거, `quit()`에서 전부 close.
   - `icons.py`에 "pin" 글리프 추가 (기존 아이콘 렌더 방식 확인 후 동일 포맷).
3. (선택) 도크 아이템 추가는 도크가 이미 13칸이라 보류 — 프리뷰 버튼 + 백로그의 히스토리 패널에서 진입.

**완료 기준**: 캡처 → 프리뷰에서 📌 → 플로팅 이미지 생성, 드래그/줌/불투명도/복사/저장/닫기 동작. 핀 여러 개 동시 유지. 앱 종료 시 전부 정리.

### ☐ P-2. 지연 캡처 (3/5/10초)

**지시**:
1. app.py에 `_delayed_capture(seconds: int, action: str)`: 1초 간격 QTimer로 `Toast.show_text(f"{n}초 후 캡처…", 900)` 카운트다운 → 0에서 `start_full_capture()` 또는 `start_region_capture()` 호출.
2. 진입점: 도크 핸들 우클릭 메뉴([dock.py:765-810](ssakkimchi/dock.py#L765-L810))에 "지연 캡처" 서브메뉴 — "3초 후 전체 캡처 / 5초 / 10초". 시그널 `delayed_capture_requested(int)` 추가 → app 연결.
3. 카운트다운 중 재요청 방지 플래그 1개.

### ☐ P-3. 마지막 영역 반복 캡처

**배경**: 같은 영역을 반복해서 찍는 워크플로(디자인 QA, 문서화)의 대표 파워 기능. Shottr·ShareX 모두 있음.

**지시**:
1. `RegionCaptureOverlay`는 region 모드에서도 `region_selected(QRect, dpr)`를 emit 중([region_capture.py:103](ssakkimchi/region_capture.py#L103))이나 app이 안 받고 있다. `_begin_shared_overlay`의 region 분기에서 `region_selected`도 연결해 `self._last_region: tuple[QRect, float] | None`에 저장 (스크린 물리 rect는 W-1 헬퍼로 변환해 보관하는 게 정확).
2. `actions.py`에 `ActionSpec("region_repeat", "부분 캡처 반복", "<alt>+0")` 추가 — Alt+0은 현재 미사용. (기존 사용자 settings.json에는 `_current_hotkey_bindings`의 setdefault 로직이 자동 병합해줌, [app.py:207-218](ssakkimchi/app.py#L207-L218) 확인 완료.)
3. 핸들러: 저장된 영역 없으면 `Toast("저장된 영역 없음 — 먼저 부분 캡처 1회")`. 있으면 오버레이 없이 즉시 물리 rect grab → `_deliver_capture(kind="region")`. 도크 숨김/복원 불필요(오버레이가 안 뜨므로), 단 도크가 영역과 겹치면 도크가 찍히니 `_hide_dock_for_capture()` + 120ms 딜레이 후 grab.

### ☐ P-4. Windows 시작 시 자동 실행 토글

**지시**:
1. `system_integration.py`에 추가 (기존 PrtSc 레지스트리 코드 스타일 준수):
   ```python
   _RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
   _RUN_VALUE = "SsakKimchiCapture"
   def get_autostart_enabled() -> bool      # 값 존재 여부
   def set_autostart(enabled: bool) -> bool # SetValueEx(f'"{sys.executable}"') / DeleteValue
   ```
2. **frozen일 때만 노출**: `getattr(sys, "frozen", False)`가 아니면(개발 환경 python.exe가 등록되는 사고 방지) 메뉴 자체를 숨김.
3. 도크 핸들 메뉴에 체크 표시 항목 "Windows 시작 시 자동 실행" (`act.setCheckable(True)` + 현재 상태 반영).
4. 설치 경로 이동/제거 후 잔재 대비: 앱 시작 시 등록된 경로 ≠ 현재 exe면 자동 갱신 (조용히).

**Phase 3 릴리즈**: v1.1.0. README 기능 목록/스크린샷 갱신 포함.

---

## 6. Phase 4 — 주석(Annotation) 에디터 (v1.2.0, 대형)

**포지셔닝상 1순위 기대 기능이지만 규모가 커서(800~1,200줄 예상) 별도 Phase.** 착수 전 이 스펙으로 세부 설계 세션 1회 권장.

**MVP 스코프**:
- 진입: 캡처 프리뷰에 "편집" 버튼 → 에디터 창(QGraphicsView + 배경 QGraphicsPixmapItem).
- 도구 7종: 사각형 / 타원 / 화살표 / 직선 / 자유곡선 / 텍스트 / **모자이크**(영역 다운스케일→업스케일 패치 — 개인정보 가림, 디자이너·개발자 스크린샷 공유의 필수).
- 색상 6종 프리셋 + 선 굵기 3단 + `QUndoStack` 기반 undo/redo (Ctrl+Z/Y).
- 출력: 클립보드 복사 / 저장(원본 덮지 않고 `_edited` 접미사) / 핀으로 띄우기(P-1 연계).
- **비스코프(v1.2에서 안 함)**: 크롭, 스포이트, 단계 번호 스탬프, 흐림(blur는 모자이크로 갈음), 이모지.

**구현 힌트**: 각 주석 = QGraphicsItem 서브클래스(선택/이동/삭제 가능하게 `ItemIsMovable|ItemIsSelectable`). 화살표는 QPainterPath로 머리 그리기. 모자이크는 확정 시점에 배경 픽스맵에서 해당 영역 copy→scaled(1/12)→scaled(원크기, FastTransformation)→QGraphicsPixmapItem. 내보내기는 `scene.render(QPainter(QImage))`. 툴바 스타일은 dock 토큰 재사용.

---

## 7. 백로그 (우선순위 낮음 / 스코프 판단 필요)

| ID | 항목 | 메모 |
|---|---|---|
| B-1 | **RapidOCR 옵션** | Windows OCR의 한글 인식률 한계 보완. rapidocr_onnxruntime(Apache-2.0) + 한국어 모델 ~15MB, onnxruntime CPU ~40MB → 인스톨러 +50MB라 **기본 번들 반대**. ffmpeg처럼 "정밀 OCR 다운로드" 온디맨드 방식 설계 필요. `ocr_engine.py`에 엔진 추상화(현 winsdk = 기본) 후 진행. |
| B-2 | **업데이트 확인** | 주 1회 백그라운드 스레드에서 GitHub `releases/latest` API(타임아웃 3s) → 신버전이면 도크 메뉴에 "새 버전 다운로드…" 항목 표시 + 토스트 1회. 마지막 확인 시각은 settings.json. 실패는 무음. |
| B-3 | **ddagrab 백엔드** | Desktop Duplication 기반, gdigrab보다 CPU↓·프레임 안정↑, LGPL 포함. 현재 30fps drop 0이라 급하지 않음. 도입 시 crop은 `ddagrab=output_idx:...` + crop 필터. |
| B-4 | **녹화 오디오** | 마이크는 dshow로 가능, 시스템 소리는 LGPL ffmpeg 단독으론 불가(가상 장치 필요). 마이크만 opt-in으로 넣을지 스코프 결정 필요. GIF/무음 데모 포지셔닝이면 안 해도 됨. |
| B-5 | **캡처 히스토리 패널** | 팔레트 패널 패턴으로 최근 캡처 썸네일 12개 + 클릭=클립보드, 우클릭=핀/폴더. captures_dir 글롭 기반이면 상태 저장 불필요. |
| B-6 | **포맷/파일명 옵션** | JPEG(품질 85) 선택, 파일명 패턴. settings.json 확장 + 도크 메뉴. |
| B-7 | **테스트 + CI** | pytest 대상(전부 순수 로직이라 Qt 불필요하거나 offscreen 가능): `hotkeys.qt_to_pynput/pynput_to_qt` 왕복, `_parse_combo_to_keyset`, `storage.load_data` 병합/파손 복구, `RecordRegion.from_qrect` 짝수 보정, `paths.is_safe_user_path`, scroll `_find_vertical_overlap`(합성 이미지). GitHub Actions `windows-latest` + `QT_QPA_PLATFORM=offscreen`. W-1 이후엔 coords 폴백 경로도. |
| B-8 | **녹화/GIF/스크롤 영역의 혼합 DPI 정확화** | `region_selected(논리 rect, dpr)` 계약을 물리 rect로 전환. 소비자 3곳(`RecordRegion.from_qrect`, `ScrollCaptureController._mss_region`, REC pill 배치 `app._record_region_rect`)을 coords 기반으로 함께 수정해야 함. 현재는 배율 다른 **보조** 모니터에서만 어긋남(주 모니터/100% 배율은 정확). |

---

## 8. 테스트 매트릭스 & 릴리즈 체크리스트

### 테스트 매트릭스 (Phase 1·2 완료 시 필수 1회)

| 환경 | 부분 | 전체 | 창 | 스크롤 | 색 | 거리 | OCR | 녹화 | GIF |
|---|---|---|---|---|---|---|---|---|---|
| 단일 모니터 100% | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 단일 모니터 **150%** | ☐ | ☐ | **☐★** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 듀얼 100%+100% (BenQ) | ☐ | ☐ | ☐ | ☐ | **☐★** | **☐★** | ☐ | ☐ | ☐ |
| 듀얼 100%+150% (가능하면) | ☐ | ☐ | ☐ | — | ☐ | — | — | ☐ | — |

★ = 이번 리뷰에서 문제 가능성이 지목된 조합. 150% 테스트는 Windows 설정 → 디스플레이 → 배율 변경으로 개발 PC에서 재현 가능(테스트 후 복원).

추가 확인: HW 인코더 차단 상태에서 h264_mf/libopenh264 녹화(§W-4), 한글 경로 저장 폴더에서 녹화/GIF(기존 workspace 이동 로직 회귀 확인), PrtSc 가로채기 on→비정상 종료(작업관리자 강제 종료)→재시작 시 레지스트리 복원.

### 릴리즈 절차 (매 Phase)

1. 버전 bump — **2곳**: `ssakkimchi/version.py` VERSION **+ `tools/installer.iss` `MyAppVersion`** (⚠ iss는 하드코딩이라 빼먹으면 옛 버전 이름의 인스톨러가 나옴 — 2026-07-09 실제로 걸렸던 함정)
2. `CHANGELOG.md` 항목 추가
3. `package.bat` → `dist/Setup_SsakKimchiCapture_X.X.X.exe` + ZIP
4. 설치 → 스모크(도크/단축키/캡처 1회/녹화 1회/종료 배너/제거)
5. `gh release create vX.X.X` (또는 기존 릴리즈에 `--clobber` 재첨부) — repo `gyqls051-arch/ssakssak-capture`
6. `CLAUDE.md` "현재 상태"/"작업 이력" 갱신 + 이 문서 체크박스 갱신 → 커밋

### 작업 공통 규칙

- **Windows 전용 (2026-07-09 확정).** macOS/리눅스 지원 작업·크로스플랫폼 추상화 금지. 맥은 필요 시 별도 네이티브 앱(이 repo 무관).
- 커밋은 작업 ID 단위: `fix(W-2): 창 캡처 DPI 이중 변환 제거` 식.
- **자매 제품 OFFCUT STUDIO / offcut.app / 종료 배너 기본값은 건드리지 않는다** (CLAUDE.md 비-자명 결정 사항).
- 새 모듈은 기존 컨벤션 준수: 시그널 기반, `get_logger("모듈명")`, 토큰(`tokens.py`) 재사용, 모든 ffmpeg Popen에 `win_job.assign_pid()`.
- 이 문서와 어긋나는 사실을 발견하면(예: F-2 검증 결과 정상) 문서를 고치고 CLAUDE.md에 한 줄 남긴다.
