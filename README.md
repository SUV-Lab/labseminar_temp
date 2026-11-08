# SUVLab 랩세미나 발표자료 양식

발표 내용을 `contents.md` 에 문장 단위로 작성하면, 클로드가 `design/mydesign.md` 규격에
맞추어 슬라이드 원고 `slide.md` 와 검토 의견 `review.md` 를 작성하고 덱 HTML 과 PDF 를
생성한다.

- 아트보드 1920x1080 (16:9). 슬라이드 한 장이 PDF 한 쪽에 대응한다
- 난독증 친화 서체와 24px 하한으로 원거리 가독성을 확보한다
- 격자 배치로 그림, 수식, 표의 정렬을 일정하게 유지한다
- 브라우저에서 전체 화면 발표가 가능하며 동영상을 슬라이드에 포함할 수 있다
- `N`으로 발표자 노트 창을 열어 대본·미리보기·타이머를 보며 슬라이드를 조작할 수 있다
- 수식은 KaTeX 로 조판하고 번호는 오른쪽 끝에 정렬한다

---

## HOW TO USE

| 단계 | 수행 내용 | 주체 | 산출물 |
|---|---|---|---|
| 1 | `./create.sh` | 사용자 | `contents.md`, `materials/`, `output/imgs/` |
| 2 | `contents.md` 에 발표 내용을 작성 | 사용자 | `contents.md` |
| 3 | 클로드에 **"컨텐츠 제작"** 지시 | 클로드 | `slide.md`, `review.md`, 덱 HTML, PDF |
| 4 | `review.md` 를 확인하고 지적 사항을 `contents.md` 에 반영한 뒤 3 단계를 재수행 | 사용자 | 보완된 `contents.md` 와 재생성된 산출물 |
| 5 | 덱 HTML 을 브라우저에서 열고 `F` 입력 | 사용자 | 전체 화면 발표 |

사용자가 직접 수행하는 단계는 1, 2, 4, 5 이다. 원고 작성, 덱 HTML 생성, `build.sh`
실행에 의한 PDF 생성은 3 단계에서 클로드가 일괄 수행한다. 4 단계는 지적 사항이 남지
않을 때까지 반복한다.

### 발표자 노트

덱 HTML의 각 `.slide` 안에 `<aside class="speaker-notes" hidden>`으로 대본을 넣는다.
`N` 또는 **발표자 노트** 버튼으로 별도 창을 연다. 슬라이드를 넘기면 대본도 바뀐다.
노트 창은 왼쪽에 현재 장, 오른쪽에 다음 장과 대본을 둔다. **대본 중심** 버튼으로 대본 칸을 넓힌다.
현재 장에서는 청중 화면의 캔버스 애니메이션과 동영상 재생을 함께 볼 수 있다. 다음 장은 정지 미리보기로 표시된다.
공유 프레임 API에 연결한 스크립트 애니메이션은 발표자 창에 포커스를 둔 채 재생·제어할 수 있다.
노트는 청중 화면과 PDF에 표시되지 않는다.

발표자 창의 **Q&A** 탭에서는 현재 슬라이드를 위에 계속 보면서, 아래의 넓은 목록에서
질문을 분류별로 훑어볼 수 있다. 질문을 고르면
답변을 읽고, **질문 목록**으로 돌아와 다른 질문을 찾는다. 검색·분류·현재 장 필터를 함께
사용할 수 있으며, 질문 선택은 청중 슬라이드를 바꾸지 않는다. `Q`로 대본과 Q&A를 전환한다.
질문·답변은 HTML의 숨겨진 템플릿에 넣어 오프라인으로 사용한다.

프로젝터와 노트북을 **확장 모드**로 연결한 뒤 **화면 설정**에서 청중 화면과 발표자
화면을 고르고 **발표 시작**을 누른다. 지원되는 Chrome/Edge에서는 화면 관리 권한을
받아 슬라이드를 외부 화면에 전체 화면으로 표시하고 노트 창을 다른 화면에 배치한다.
운영체제의 복제 → 확장 전환은 직접 해야 한다(Windows: `Win + P` → 확장).
자동 배치가 안 되면 기존처럼 `N`으로 노트 창을 열어 직접 옮기고 슬라이드 창에서 `F`를 누른다.

- [바로 열어보는 예제](examples/presenter-notes.html)
- [작성법·단축키·기존 덱 적용](design/README.md#발표자-노트)
- [브라우저 검증 실행](tests/README.md)

### 1. 작업 폴더 생성

```bash
./create.sh
```

`contents.md`, `materials/`, `output/imgs/` 를 생성한다. `contents.md` 가 이미 존재하면
덮어쓰지 않는다.

### 2. contents.md 작성

사용자가 직접 작성하는 유일한 내용 파일이다. 발표에서 설명할 내용을 그대로 기술한다.
클로드에 대한 지시문을 기술하는 파일이 아니다.

- 올바른 예: `IMU 단독 적분은 바이어스가 누적되어 수십 초 안에 발산한다`
- 잘못된 예: `IMU 의 한계를 한 문장으로 적는다`

| 표기 | 의미 |
|---|---|
| `#` | 덱 제목. 영문으로 작성한다 |
| `## Cover` | 표지. 구분, 파트, 주제, 발표자를 기술한다 |
| `##` | 장. 슬라이드 키커가 된다. 영문으로 작성하면 CSS 가 대문자로 변환한다 |
| `###` | 슬라이드 하나. 제목도 영문으로 작성한다 |
| `- ` | 문단 하나를 압축한 한 문장 |
| `구분 슬라이드: 필요` | 해당 장 앞에 파트 구분 슬라이드를 삽입한다. 장 이름만 배치하며 머리말, 푸터, 번호를 두지 않는다 |

원본 자료는 `materials/` 에 배치한다. 덱에 포함되는 변환본은 클로드가 `output/imgs/` 에
생성한다.

| 종류 | 표기 |
|---|---|
| 그림 | `그림: materials/파일명.png - English alt label` |
| 동영상 | `동영상: materials/파일명.mp4 - poster: materials/파일명_poster.jpg` |
| 표 | `표:` 다음 줄부터 마크다운 표를 작성한다. 머리행은 영문으로 작성한다 |
| 수식 | `수식:` 다음 줄부터 `$$` 로 감싸 작성하고, 기호 설명을 불릿으로 잇는다 |

- 구어체를 사용하지 않는다. 형식을 갖춘 개조식으로 작성한다
- 제목은 영문으로 작성한다
- 수식 내부에는 ASCII 만 사용한다. 한글과 `·` `×` `→` `≤` 등의 비-ASCII 기호는 수식 밖에 기술한다

### 3. 컨텐츠 제작

클로드에 **"컨텐츠 제작"** 을 지시한다. 클로드는 다음 네 가지를 생성한다.

| 산출물 | 내용 |
|---|---|
| `slide.md` | 발표자료 원고. 수식, 표, 그림, 동영상을 포함한 마크다운 |
| `review.md` | 발표 내용의 부족한 부분, 논리적 결함, 보완 사항 |
| `output/<타이틀>_<학생이름>.html` | `design/` 규격의 덱 HTML |
| `output/<타이틀>_<학생이름>.pdf` | `build.sh` 실행으로 생성한 PDF |

배포물 이름은 `contents.md` 표지의 `- 주제:` 줄을 타이틀로, `- 발표:` 줄의 마지막
낱말을 학생 이름으로 사용하여 `<타이틀>_<학생이름>` 으로 결정한다. 타이틀에서 공백과
특수기호를 제거하고 낱말 경계는 각 낱말의 첫 글자를 대문자로 유지한다.

```python
import re
words = re.split(r'[^0-9A-Za-z가-힣]+', title)
slug = ''.join(w[:1].upper() + w[1:] for w in words if w)
```

### 4. 검토와 보완

`review.md` 를 먼저 확인한다. 클로드가 근거 없는 수치, 누락된 전제, 검증되지 않은
주장, 논리적 결함, 구조와 분량 문제를 근거 위치와 함께 지적한 문서이다.

1. `review.md` 의 지적 사항을 확인한다
2. 보완할 내용을 `contents.md` 에 직접 반영한다. `slide.md` 를 고치지 않는다
3. 클로드에 **"컨텐츠 제작"** 을 다시 지시한다. `slide.md`, `review.md`, 덱 HTML, PDF 가 모두 다시 생성된다

지적 사항이 남지 않을 때까지 위 과정을 반복한다.

### 5. 슬라이드 편집 - 선택

생성된 덱의 글, 배치, 순서를 직접 수정할 경우 편집기를 사용한다. 마크다운을 거치지
않고 덱 HTML 을 그 자리에서 고친다.

```bash
./editor.sh                  # output/ 의 덱을 모두 연다
./editor.sh output/x.html    # 덱 하나만 연다
./editor.sh --port 8899      # 포트 지정. --no-open 은 브라우저를 열지 않는다
```

`editor/` 서브모듈이 없으면 `editor.sh` 가 먼저 내려받는다. 포트는 8770 부터 비어 있는
번호를 자동으로 고르므로 편집기를 둘 이상 띄워도 충돌하지 않는다. 실행하면 브라우저가
해당 주소로 열린다. 왼쪽에 슬라이드 목록, 오른쪽에 선택한 슬라이드가
표시된다.

| 작업 | 방법 |
|---|---|
| 글 수정 | 슬라이드에서 해당 글을 눌러 그 자리에서 입력한다. `Esc` 로 빠져나온다 |
| 슬라이드 순서 변경 | 왼쪽 썸네일을 끌어 옮긴다. `Alt+↑` `Alt+↓` 도 같다. 번호와 진행 막대는 자동으로 다시 매겨진다 |
| 슬라이드 추가 | 목록 아래 `+ 새 슬라이드`. 앞 슬라이드의 배치와 꼬리말을 유지한 빈 장이 들어간다 |
| 슬라이드 삭제 | 썸네일을 고르고 `Del`. `Ctrl+Z` 로 되돌린다 |
| 본문 배치 변경 | 도구막대의 배치 버튼에서 등분을 고른다. 빈 칸에는 `글목록` `그림` `표` `코드` 를 넣는다 |
| 그림 교체 | 그림을 끌어다 놓으면 덱 폴더의 `imgs/` 에 저장되고 상대 경로로 삽입된다 |
| 저장 | `Ctrl+S`. `자동 저장` 을 켜면 마지막 수정 1.2 초 뒤에 기록된다 |

수정 결과는 덱 HTML 에만 반영된다. `contents.md` 와 `slide.md` 는 변경되지 않으므로,
편집 후 "컨텐츠 제작" 을 다시 지시하면 수정 내용이 덮어써진다. 발표 직전의 미세 조정에
사용하고, 내용 변경은 `contents.md` 에서 수행한다. 편집 후에는 `./build.sh` 로 PDF 를
다시 생성한다.

편집기의 상세 사용법은 [editor/README.md](editor/README.md) 에 있다.

### 6. PDF 재생성 - 선택

3 단계에서 클로드가 이미 실행한다. 덱 HTML 또는 `design/` 을 직접 수정한 경우에만
사용자가 실행한다.

```bash
./build.sh                                             # output/ 의 덱 HTML 을 대상으로 한다
./build.sh EKFBasedStateEstimationForIndoorUAV_홍길동   # 덱이 여럿인 경우 이름을 지정한다
```

### 7. 발표

`output/<타이틀>_<학생이름>.html` 을 브라우저에서 열고 `F` 를 입력한다.

| 키 | 동작 |
|---|---|
| `F` | 전체 화면 시작. 현재 슬라이드부터 진행한다 |
| 스페이스 · `→` · `↓` · PageDown · Enter | 다음 장 |
| `←` · `↑` · PageUp · Backspace | 이전 장 |
| Home · End | 처음 · 마지막 |
| `B` | 화면 일시 소등 |
| Esc | 종료 |

### slide.md 표기

클로드가 작성하는 파일이며, 사용자가 읽고 수정할 수 있도록 마크다운으로 유지한다.

```markdown
## 01. Slide Title In English

키커: Section Name

- **말머리** — 설명

리드
: 슬라이드 한 줄 요약

경고 카드 · 카드 제목
: 반드시 기억해야 할 한 문장이 있을 때만 사용한다

| Header | Header |
|---|---|
| 항목 | 내용 |

$$
y = a x^2 + b x + c \tag{1}
$$

- `a, b, c` 계수
- `x` 입력
- `y` 출력

![English label](imgs/example.png)
```

- 표의 머리행은 영문으로 작성한다
- 수식 번호는 `\tag{n}` 으로 부여하고 기호 설명을 바로 아래에 한 줄씩 기술한다
- 동영상에는 `poster` 를 반드시 지정한다. PDF 에는 해당 정지 화면이 수록된다

---

## EXAMPLE

견본 한 벌이 `instruction/example/` 에 있다. `contents.md`, 그것으로 생성한 `slide.md`
및 `review.md` 로 구성된다. 아래는 그 견본을 실제로 빌드하여 생성한 13쪽 덱이다.

입력한 `contents.md` 의 일부는 다음과 같다.

```markdown
# EKF-Based State Estimation for Indoor UAV

## Cover

- 구분: Lab Seminar
- 파트: Indoor Autonomous Flight
- 주제: EKF-Based State Estimation for Indoor UAV
- 발표: 충북대학교 지능로봇공학과 홍길동

## Introduction

구분 슬라이드: 필요

### Motivation

- 실내 비행 로봇은 GNSS 신호가 차단되어 외부 위치 기준 없이 자기 위치를 추정해야 한다
- IMU 단독 적분은 가속도계 바이어스가 시간의 제곱으로 누적되어 수십 초 안에 발산한다

그림: materials/sensor_limits.png - IMU drift versus LiDAR update rate
```

생성 결과는 다음과 같다.

![표지](instruction/example/imgs/example-01.png)

| | |
|---|---|
| ![글과 그림](instruction/example/imgs/example-04.png) | ![수식 슬라이드](instruction/example/imgs/example-07.png) |
| 글과 그림 | 수식. 번호는 오른쪽 끝에 정렬한다 |
| ![표와 그래프](instruction/example/imgs/example-10.png) | ![동영상 슬라이드](instruction/example/imgs/example-11.png) |
| 표와 그래프 | 동영상. PDF 에는 poster 가 수록된다 |

슬라이드 종류와 배치 규칙의 전문은 [design/README.md](design/README.md) 와
[design/mydesign.md](design/mydesign.md) 에 있다.

---

## HOW TO INSTALL

### 저장소 복제

`editor/` 가 서브모듈이므로 함께 받는다.

```bash
git clone --recurse-submodules https://github.com/SUV-Lab/labseminar_temp.git
cd labseminar_temp
```

이미 복제한 경우에는 다음을 실행한다.

```bash
git submodule update --init
```

### 필요 도구

| 도구 | 용도 | 확인 |
|---|---|---|
| `google-chrome` | HTML 을 PDF 로 인쇄 | `google-chrome --version` |
| `pdfinfo` (poppler-utils) | 쪽수 확인 | `pdfinfo -v` |
| `ffmpeg` | 동영상 변환과 poster 추출. 동영상을 사용할 때만 필요 | `ffmpeg -version` |
| `python3` | 슬라이드 편집기 실행. 편집기를 사용할 때만 필요 | `python3 --version` |

```bash
sudo apt install poppler-utils ffmpeg
```
