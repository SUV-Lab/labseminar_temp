# 사용 방법

발표 내용을 `contents.md` 에 작성하고 클로드에 "컨텐츠 제작" 을 지시하면 원고, 검토 의견,
덱 HTML, PDF 가 생성된다. 이 문서는 각 단계의 상세 규칙을 다룬다.

| 단계 | 수행 내용 | 주체 | 산출물 |
|---|---|---|---|
| 1 | `./create.sh` | 사용자 | `contents.md`, `materials/`, `build/imgs/` |
| 2 | `contents.md` 에 발표 내용을 작성 | 사용자 | `contents.md` |
| 3 | 클로드에 **"컨텐츠 제작"** 지시 | 클로드 | `slide.md`, `review.md`, 덱 HTML, PDF |
| 4 | `review.md` 의 지적 사항을 `contents.md` 에 반영한 뒤 3 단계를 재수행 | 사용자 | 보완된 산출물 |
| 5 | `output/` 의 HTML 을 브라우저에서 열고 `F` 입력 | 사용자 | 전체 화면 발표 |

원고 작성, 덱 HTML 생성, `build.sh` 실행은 3 단계에서 클로드가 일괄 수행한다. 4 단계는
지적 사항이 남지 않을 때까지 반복한다.

## 1. 작업 폴더 생성

```bash
./create.sh
```

`contents.md`, `materials/`, `build/imgs/` 를 생성한다. `contents.md` 가 이미 존재하면
덮어쓰지 않는다.

## 2. contents.md 작성

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
| `구분 슬라이드: 필요` | 해당 장 앞에 파트 구분 슬라이드를 삽입한다 |

원본 자료는 `materials/` 에 배치한다. 덱에 포함되는 변환본은 클로드가 `build/imgs/` 에
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
- 수식은 표준 LaTeX(amsmath, amssymb, bm)로 조판되는 명령만 사용한다

## 3. 컨텐츠 제작

클로드에 **"컨텐츠 제작"** 을 지시한다.

| 산출물 | 내용 |
|---|---|
| `slide.md` | 발표자료 원고. 수식, 표, 그림, 동영상을 포함한 마크다운 |
| `review.md` | 발표 내용의 부족한 부분, 논리적 결함, 보완 사항 |
| `build/<타이틀>_<학생이름>.html` | 덱 원본(편집 대상). `build/imgs/` 와 디자인 사본을 참조한다 |
| `output/<타이틀>_<학생이름>.html` | 배포용 단일 HTML. 이 파일 하나로 오프라인 발표가 가능하다 |
| `output/<타이틀>_<학생이름>.pdf` | PDF. 슬라이드 한 장이 한 쪽이다 |

배포물 이름은 `contents.md` 표지의 `- 주제:` 줄을 타이틀로, `- 발표:` 줄의 마지막
낱말을 학생 이름으로 사용한다. 타이틀에서 공백과 특수기호를 제거하고 각 낱말의 첫
글자를 대문자로 유지한다.

```python
import re
words = re.split(r'[^0-9A-Za-z가-힣]+', title)
slug = ''.join(w[:1].upper() + w[1:] for w in words if w)
```

빌드 과정과 폴더 구조는 [build.md](build.md) 에 있다.

## 4. 검토와 보완

`review.md` 는 근거 없는 수치, 누락된 전제, 검증되지 않은 주장, 논리적 결함, 구조와
분량 문제를 근거 위치와 함께 지적한 문서이다.

1. `review.md` 의 지적 사항을 확인한다
2. 보완할 내용을 `contents.md` 에 직접 반영한다. `slide.md` 를 고치지 않는다
3. 클로드에 **"컨텐츠 제작"** 을 다시 지시한다. 모든 산출물이 다시 생성된다

## 5. 슬라이드 편집 - 선택

생성된 덱의 글, 배치, 순서를 직접 수정할 경우 편집기를 사용한다. 덱 HTML 을 그 자리에서
고친다.

```bash
./editor.sh                  # build/ 의 덱을 모두 연다
./editor.sh build/x.html     # 덱 하나만 연다
./editor.sh --port 8899      # 포트 지정. --no-open 은 브라우저를 열지 않는다
```

`editor/` 서브모듈이 없으면 먼저 내려받는다. 포트는 8770 부터 비어 있는 번호를 자동으로
고른다.

| 작업 | 방법 |
|---|---|
| 글 수정 | 슬라이드에서 해당 글을 눌러 그 자리에서 입력한다. `Esc` 로 빠져나온다 |
| 슬라이드 순서 변경 | 왼쪽 썸네일을 끌어 옮긴다. `Alt+↑` `Alt+↓` 도 같다 |
| 슬라이드 추가 | 목록 아래 `+ 새 슬라이드` |
| 슬라이드 삭제 | 썸네일을 고르고 `Del`. `Ctrl+Z` 로 되돌린다 |
| 본문 배치 변경 | 도구막대의 배치 버튼에서 등분을 고른다 |
| 그림 교체 | 그림을 끌어다 놓으면 `build/imgs/` 에 저장된다 |
| 저장 | `Ctrl+S`. `자동 저장` 을 켜면 마지막 수정 1.2 초 뒤에 기록된다 |

수정 결과는 덱 HTML 에만 반영된다. 편집 후 "컨텐츠 제작" 을 다시 지시하면 수정 내용이
덮어써지므로, 발표 직전의 미세 조정에만 사용한다. 편집 후에는 `./build.sh` 로 배포물을
다시 생성한다. 편집기의 상세 사용법은 [editor/README.md](../editor/README.md) 에 있다.

## slide.md 표기

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

## 예제

견본 한 벌이 `instruction/example/` 에 있다. `contents.md`, 그것으로 생성한 `slide.md`
및 `review.md` 로 구성된다.

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

| | |
|---|---|
| ![글과 그림](../instruction/example/imgs/example-04.png) | ![수식 슬라이드](../instruction/example/imgs/example-07.png) |
| 글과 그림 | 수식. 번호는 오른쪽 끝에 정렬한다 |
| ![표와 그래프](../instruction/example/imgs/example-10.png) | ![동영상 슬라이드](../instruction/example/imgs/example-11.png) |
| 표와 그래프 | 동영상. PDF 에는 poster 가 수록된다 |

슬라이드 종류와 배치 규칙의 전문은 [design/README.md](../design/README.md) 와
[design/mydesign.md](../design/mydesign.md) 에 있다.
