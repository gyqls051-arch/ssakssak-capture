[종료 팝업 배너 넣는 법]

앱을 끌 때 뜨는 팝업 배너입니다. 두 가지 방법 중 편한 걸로 세팅하세요.

■ 방법 1) 이미지 배너 (가장 쉬움)
이 폴더(assets/)에 아래 이름 중 하나로 이미지를 넣으면 종료 시 그 이미지가 배너로 뜹니다:
- exit_ad.png   (권장)
- exit_ad.jpg
- exit_ad.webp

권장 사이즈:
- 가로 1040px (×2 레티나용), 세로 자유 — 다이얼로그 가로 520px에 맞게 자동 축소.
- 권장 비율: 16:9 (520×292) 또는 16:10 (520×325).

이미지를 넣은 뒤 package.bat 를 다시 실행하면 새 빌드/인스톨러에 반영됩니다.
이미지가 없으면 텍스트 그라데이션 카드가 fallback 으로 표시됩니다.

■ 방법 2) 문구/링크/표시여부 바꾸기
ssakkimchi/exit_ad.py 맨 위 "★배너 설정★" 블록만 고치면 됩니다 (코드 지식 불필요):
- BANNER_ENABLED  : False 로 두면 종료 팝업을 아예 안 띄움
- BANNER_IMAGE    : 배너 이미지 파일명 (기본 exit_ad.png)
- BANNER_URL      : 배너/버튼 클릭 시 열 주소. ""(빈값)이면 클릭/버튼 없는 단순 안내 배너
- BANNER_TITLE / BANNER_SUBTITLE / BANNER_DESC : 텍스트 카드 문구 (이미지 없을 때)
- BANNER_BUTTON   : 방문 버튼 문구
- BANNER_ACCENT   : 버튼/포인트 색 (예 "#4f46e5")

※ 현재 기본값은 자매 제품 OFFCUT STUDIO 홍보 배너입니다 (URL: https://offcut.app).
   싹싹김치 자체 배너로 바꾸려면 위 BANNER_* 값을 수정하거나 exit_ad.png 를 교체하세요.

※ 커밋 주의: .gitignore 가 exit_ad.png/.jpg/.webp 를 제외합니다(개인 광고 자산).
   배너 이미지를 repo에 같이 올리려면 .gitignore 에서 해당 줄을 빼세요.
