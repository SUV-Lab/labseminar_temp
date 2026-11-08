# 발표자 노트 브라우저 검사

Python 3 표준 라이브러리, Chrome/Chromium, `pdftotext`(Poppler)가 필요하다.
별도 Node 패키지나 Python 패키지는 설치하지 않는다.

```bash
python3 tests/test_presenter.py
# 화면과 PDF 증거를 보관할 때
python3 tests/test_presenter.py --output /tmp/suvlab-presenter-test
# Chromium 실행 파일을 지정할 때
CHROME_BIN=chromium python3 tests/test_presenter.py
# 실제 창 포커스 전환까지 확인할 때 (데스크톱 필요, 테스트 창만 열고 닫음)
python3 tests/test_presenter.py --headed --output /tmp/suvlab-presenter-headed
# 노트 창만 조작할 때의 애니메이션 진행 검사 (데스크톱 필요)
python3 tests/test_presenter_clock.py --output /tmp/suvlab-presenter-clock
# 동영상의 표지·재생 프레임이 청중 화면과 같은지 확인
python3 tests/test_video_poster.py --output /tmp/suvlab-video-poster
# 외부 화면 자동 배치와 실패 시 수동 전환 검사 (최신 Chrome/Chromium)
python3 tests/test_presenter_displays.py --output /tmp/suvlab-presenter-displays
# 발표자 전용 Q&A 검색·선택·비공개 표시 검사
python3 tests/test_presenter_qa.py --output /tmp/suvlab-presenter-qa
# Q&A 목록·답변에서도 현재 슬라이드와 움직이는 캔버스가 보이는지 확인
python3 tests/test_presenter_qa_preview.py --output /tmp/suvlab-presenter-qa-preview
# 많은 질문을 훑는 전체 목록·분류·답변 전환 검사
python3 tests/test_presenter_qa_browse.py --output /tmp/suvlab-presenter-qa-browse
```

새 임시 브라우저 프로필에서 오프라인 `file://` 덱을 연다. 로컬 파일 접근·동일 출처
정책을 완화하는 플래그는 사용하지 않는다. 사용 중인 브라우저나 Claude 세션에는
연결하지 않는다.

기본 headless 모드에서는 두 창이 모두 포커스를 가진 것으로 보고되어 `blur` 이벤트를
명시적으로 보내 처리기를 확인한다. `--headed`는 실제 창을 전환하고 원본의 포커스가
해제된 것까지 확인한다. 보고서의 `focusEvidence`에 검사 방식이 기록된다.

`test_presenter_clock.py`는 실제 청중 창을 최소화하고 발표자 노트 창에 포커스를 둔다.
노트에서 장을 넘긴 뒤 `P`를 눌러 원본의 기본 프레임 호출이 중단된 상태에서도
공유 애니메이션 시계와 미리보기가 계속 진행하는지 검사한다. 일시정지·초기화,
콜백 취소, 두 창 사이의 시계 전환과 재생 속도, 노트 닫기·재열기도 확인한다.
백그라운드 제한을 해제하는 플래그나 가짜 visibility/blur 이벤트는 쓰지 않는다.
이 검사는 창 포커스를 사용하므로 다른 headed 테스트와 동시에 실행하지 않는다.

`test_video_poster.py`는 브라우저 안에서 테스트 영상을 만들어 재생 전 표지,
재생·일시정지·0초 초기화, 리소스 재로드 상태를 실제 화면 픽셀로 비교한다.
별도 영상 파일이나 인코더 설치는 필요하지 않다.

`test_presenter_displays.py`는 Chrome의 가상 화면(`Emulation.addScreen`)을 추가하고
실제 화면 선택·전체 화면·팝업 API로 두 창의 배치를 확인한다. 시작 버튼에는 실제
마우스 입력을 보내고, 상태 조회에는 `userGesture: false`를 사용하므로 검사 코드가
사용자 활성화를 임의로 부여하지 않는다. 권한은 테스트 브라우저에서 사전 허용한다.
발표자 창 재사용, 장 이동·재생 제어, 설정 창 재열기도 확인한다.

지원하지 않는 브라우저, 권한 거부, 단일 화면, 팝업 차단, 잘못된 화면 배치,
전체 화면 취소·실패 등은 명시적인 API 모의 객체로 검사한다. 화면 선택 해제,
늦은 권한 응답, 키보드 조작, 인쇄 시 설정 창 숨김도 포함한다. 이 검사는
**가상 화면과 모의 실패 조건의 증거**이며, 실제 HDMI·프로젝터나 Windows/macOS
화면 전환을 검증한 결과가 아니다. 가상 화면 CDP 명령을 제공하는 최신
Chrome/Chromium이 필요하다.

`test_presenter_qa.py`는 일반 발표 연습 문구로 만든 임시 덱에서 Q&A를 검사한다.
한글·영어 검색, 현재 장 필터, 선택한 답변 유지, 대본 스크롤 복원, 글씨 크기,
작은 창 배치와 카드가 없는 경우를 확인한다. 검색 입력과 질문 목록 조작이 청중
슬라이드나 재생 상태를 바꾸지 않는지도 검사한다. Q&A 원문이 청중 화면·두 미리보기·
인쇄 PDF에 나타나지 않고, HTML처럼 생긴 답변도 실행되지 않는 일반 텍스트로 표시되는지
확인한다. 결과 스크린샷은 `--output` 폴더에 보관한다.

`test_presenter_qa_browse.py`는 일반 발표 연습용 질문 46개를 사용한다. Q&A를 열었을 때
질문 목록이 작업 영역을 넓게 사용하고, 읽을 수 있는 크기로 많은 질문이 동시에 보이는지
실제 화면 좌표로 검사한다. 분류·검색·현재 장 필터의 조합, 질문 선택 후 답변 보기,
목록으로 돌아왔을 때 스크롤 복원, 작은 창의 답변 전체 폭, Esc의 답변→목록→대본
전환을 확인한다. 목록·분류·검색을 조작할 때 청중 슬라이드나 재생 상태가 바뀌지
않는지도 확인하며, 분류 이름은 HTML처럼 보이더라도 일반 텍스트로 표시해야 한다.

검사 범위는 발표자 보기 배치(현재·다음·대본 위치, 대본 중심/슬라이드 중심 전환),
양방향 이동, 단축키, 빈 노트, 긴 대본의 스크롤 유지, 글씨 크기, 타이머,
작은 창 배치, 팝업 재사용·닫기·재열기, 원본 새로고침·닫기 후 연결 해제,
커스텀 애니메이션과 실제 `video` 재생·초기화, 현재 미리보기의 픽셀 동기화,
숫자·입력값·동적으로 바뀐 캔버스 반영, 다음 장의 정지 상태, 노트 미리보기 제외,
화면 캡처에서 캔버스·동영상이 실제 보이는지, 미리보기 CSP의 스크립트 차단,
PDF 노트 숨김, 팝업 차단 처리다. 화면 확장 배치와 프로젝터 하드웨어는 실제 환경에서
확인해야 한다.

실제 덱의 발표자 화면은 같은 조건으로 캡처해 눈으로 확인한다. 장 번호는 1부터 센다.
폭 900px 이하에서는 대본 중심 배치만 저장한다.

```bash
python3 tests/capture_presenter_views.py --deck output/덱.html --output /tmp/presenter-views \
  --slides 1,13,28 --sizes 1280x850,800x700
```
