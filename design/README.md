# Slide Deck Design

HTML 로 발표자료를 만들고 PDF 로 뽑는 슬라이드 디자인이다.
아트보드는 1920x1080 (16:9) 이고, 슬라이드 하나가 PDF 한 쪽이 된다.

- 난독증 친화 서체와 24px 하한으로 뒤에서도 읽히는 글자 크기를 강제한다
- 배치를 격자로 고정해 그림, 수식, 표의 열과 오가 저절로 맞는다
- 브라우저에서 그대로 전체 화면 발표가 되고, 동영상도 슬라이드에 넣을 수 있다
- 수식은 KaTeX 로 그리고, 번호는 오른쪽 끝에 붙는다

![표지](imgs/01_cover.png)

---

## 시작하기

### 1. 파일 복사

새 발표자료 폴더에 다음을 복사한다.

```
deck.css        디자인 구현. 색, 글꼴, 슬라이드 종류, 본문 요소
layout.css      본문 배치 규칙. deck.css 다음에 읽힌다
present.js      전체 화면 발표와 동영상 지원
presenter.js    N 키로 여는 별도 발표자 노트 화면
template.html   빈 덱 뼈대. 이 파일을 고쳐 쓴다
```

로고도 함께 둔다. 파일 이름은 `deck.css` 가 참조하는 이름 그대로 쓴다.

```
suvlab_logo.png   표지 왼쪽 위 200px, 본문 오른쪽 위 높이 112px  (--lab-logo)
```

표지와 본문이 같은 로고를 쓴다. `assets/lab_logo.png` 를 그 이름으로 바꿔 쓰거나,
`deck.css` 위쪽의 `--lab-logo` 값을 자기 파일 이름으로 고친다.

### 2. 내용 작성

`template.html` 의 `<section class="slide">` 를 늘리고 줄여 쓴다.
덱은 **표지 · 목차 · 파트 구분 · 본문 · 결론** 으로 구성한다.

### 3. PDF 만들기

```bash
google-chrome --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=30000 --print-to-pdf=deck.pdf deck.html
```

`--virtual-time-budget` 은 KaTeX 와 웹폰트가 다 실릴 때까지 기다리는 시간이다.
수식이 빈 칸으로 나오면 이 값을 늘린다.

---

## 발표하기

브라우저로 HTML 을 열고 `F` 키를 누르거나 오른쪽 아래 **전체 화면** 버튼을 누른다.

| 키 | 동작 |
|---|---|
| `F` | 전체 화면 시작. 보고 있던 슬라이드부터 |
| `N` | 발표자 노트 창 열기 / 이미 열린 창으로 이동 |
| `Q` | 발표자 창에서 대본 / Q&A 전환 (입력 중에는 글자 입력) |
| 스페이스 · `→` · `↓` · PageDown · Enter | 다음 장 |
| `←` · `↑` · PageUp · Backspace | 이전 장 |
| Home · End | 처음 · 마지막 |
| `B` | 화면 잠깐 끄기 |
| `P` / `R` | 현재 장의 동영상 재생·정지 / 처음으로 초기화 |
| Esc | 종료 |

슬라이드를 눌러도 다음 장으로 넘어간다. 링크, 버튼, 동영상 재생 막대는 예외다.

### 발표자 노트

각 슬라이드의 안에 대본을 작성한다. `hidden`을 함께 쓰면 스크립트와 스타일이
아직 로드되지 않은 순간에도 대본이 슬라이드에 나타나지 않는다.

```html
<section class="slide" data-label="Results">
  <!-- 제목, 그림 등 청중에게 보이는 내용 -->
  <aside class="speaker-notes" hidden>
    <p>The left table shows the results.</p>
    <p><strong>[영상 재생 후 다음 문장]</strong></p>
    <p>We will now look at the next example.</p>
  </aside>
</section>
```

문단, 줄바꿈, 강조, 목록, 코드 서식이 지원된다. 노트의 실행 스크립트·이벤트 속성은
발표자 화면으로 복사하지 않는다. 노트가 없는 장에는 빈 상태 안내가 나온다.

1. HDMI를 연결하고 두 모니터를 **확장 모드**로 설정한다. Windows는 `Win + P` → **확장**,
   macOS는 시스템 설정 → 디스플레이에서 미러링을 해제한다.
2. HTML을 Chrome 또는 Edge로 열고 **화면 설정**을 누른다. 화면 관리 권한 요청을 허용한다.
3. **청중 · 슬라이드 전체 화면**과 **발표자 · 노트와 미리보기**에 서로 다른 화면을 선택한다.
   내장 화면은 발표자 화면으로 우선 선택한다.
4. **발표 시작**을 누르면 선택한 청중 화면으로 슬라이드를 전체 화면 표시하고,
   다른 화면에 노트 창을 연다. 기존 노트 창이 있으면 재사용한다.

웹페이지는 운영체제의 **복제 → 확장 전환 자체를 수행할 수 없다**. 복제 상태이거나
외부 화면이 연결되지 않아 독립된 화면이 하나만 감지되면 설정 안내를 표시한다.
설정을 바꾸거나 HDMI를 다시 연결한 뒤 **화면 다시 찾기**를 누른다.
브라우저가 자동 배치를 지원하지 않거나 화면 권한·팝업·전체 화면을 차단한 경우에는
**노트 창 열고 직접 배치**를 사용한다. 노트 창은 노트북에, 슬라이드 창은 프로젝터에
옮긴 뒤 슬라이드 창에서 `F`를 누르면 된다. 기존 `N`으로 바로 노트를 여는 방식도 유지된다.

노트 창의 **화면 설정**은 원본 슬라이드 창으로 설정 화면을 가져온다. 전체 화면 시작은
그 창에서 **발표 시작**을 직접 눌러야 한다. 화면 정보는 메모리에서만 사용하며 저장하거나
전송하지 않는다. 자동 배치는 Window Management API를 지원하는 브라우저와 실행 환경이
필요하며, 지원 여부와 권한은 실행 시 확인한다.

구현은 [Window Management 안내](https://developer.chrome.com/docs/capabilities/web-apis/window-management)와
[전체 화면 + 보조 창 순서](https://github.com/w3c/window-management/blob/main/HOWTO.md)를 따른다.
청중 창의 전체 화면 요청을 먼저 보내고 노트 창을 열어 브라우저의 사용자 동작 제한을 지킨다.
선택 화면으로 이동했는지 확인한 뒤 노트를 표시하며, 복제 모드 자동 전환이나 물리 HDMI 장비
전반의 호환성을 보장하는 기능은 아니다.

노트 창은 슬라이드쇼 발표자 보기와 같은 배치다. 왼쪽에 현재 장, 오른쪽 위에 다음 장의
작은 정지 미리보기, 그 아래에 높은 대본 칸이 있다. 위쪽 막대에 경과 타이머, 대본 글씨
크기(A−/A＋), **대본 중심** 버튼이 있다. **대본 중심**을 누르면 현재·다음 장을 왼쪽에
작게 모으고 대본 칸을 넓힌다. 버튼은 **슬라이드 중심**으로 바뀌고, 다시 누르면 기본
배치로 돌아간다. 폭 900px 이하의 작은 창은 항상 대본 칸을 넓게 쓴다.
슬라이드 창에서 방향키로 넘겨도 노트가 동기화된다. 현재 장은 청중 화면의 캔버스와
동영상 프레임, 단계 표시와 숫자를 계속 반영한다. 재생·일시정지·탐색·초기화 결과도
현재 장에서 확인할 수 있다. 다음 장은 정지 미리보기다.

실제 재생과 소리는 청중 창에서만 실행한다. 발표자 창은 현재 프레임을 복사하며
슬라이드 스크립트나 동영상 플레이어를 추가로 실행하지 않는다. 외부 사이트의 삽입
프레임은 복사하지 않는다. CSS 자체 애니메이션은 미리보기에서 정지하며, 캔버스·동영상과
슬라이드 DOM의 변경 사항을 동기화한다.

노트 창에서 `P`/`R`로 미디어를 조작하고 `B`로 청중 화면을 잠깐 검게 할 수 있다.
입력 칸에서는 입력을 우선한다. 버튼에 포커스가 있으면 스페이스·Enter로 버튼을
누를 수 있고, 방향키·PageUp/PageDown·미디어 단축키는 계속 사용할 수 있다.
이전·다음·재생 등의 조작 버튼을 마우스로 누르거나 장 번호를 확정하면 현재 읽는
대본 또는 답변으로 초점이 돌아온다. 질문 검색과 선택은 청중 슬라이드 이동과 분리된다.
노트 창을 닫아도 발표는 계속된다. 다시 `N`을 누르면 현재 장에서 노트 창을 연다.
노트 창을 새로고침해서 비었다면 슬라이드 창에서 `N`으로 다시 연다.
노트 창에서 청중 창으로 돌아오는 첫 슬라이드 클릭은 초점 복귀로 처리한다. 이후 클릭은
다음 장으로 이동한다. 키보드로 조작하면 즉시 동작한다. 전체 화면 중 `N`으로 새 창을
열 때는 브라우저 전체 화면이 해제될 수 있지만 한 장 보기 상태는 유지된다. 필요한 경우
청중 창에서 다시 `F`를 누른다.
슬라이드 창을 닫거나 새로고침하면 이전 노트 창의 연결은 끊긴다. 다시 `N`으로 연다.

`file://`로 직접 열 수 있으며 별도 서버는 필요하지 않다. 브라우저가 새 창을 막으면
해당 파일/사이트의 팝업을 허용한 뒤 다시 `N`을 누른다. PDF에는 대본과 발표자용
버튼이 포함되지 않는다. 노트 자체는 HTML에 저장되므로 HTML 원본에는 남아 있다.

**기존 덱 적용:** 기존 HTML이 `present.js`를 읽고 있다면 새 `present.js`와
`presenter.js`, `deck.css`를 함께 복사하고 각 장에 노트를 추가하면 된다.
`presenter.js`는 `present.js`와 같은 폴더에 둔다. 자체 애니메이션의 창 전환 중
재생까지 지원하려면 아래 공유 프레임 API도 연결한다. 파일 복사만으로 기존
`requestAnimationFrame`이나 타이머 호출을 자동 변환하지는 않는다.
별도의 `<script src="presenter.js">` 태그는 필요 없다. `build.sh`도 두 JS 파일을
덱 옆에 배포한다. [오프라인 예제](../examples/presenter-notes.html)를 참고한다.

### 발표자 Q&A

발표자 창의 **Q&A** 탭 또는 `Q` 키를 누르면 상단에 현재 슬라이드와 검색·분류 도구,
하단에 넓은 질문 목록이 표시된다. 현재 슬라이드는 질문을 찾거나 답변을 읽는 동안에도
계속 보이며 캔버스와 영상의 재생 상태가 함께 반영된다.
질문을 선택하면 큰 글씨로 답변을 읽는다. 넓은 창에서는 목록과 답변을 나란히 표시하며,
작은 창에서는 답변을 따로 표시한다. **질문 목록**으로 돌아오면 훑던 위치가 복구된다.
한글·영어 질문, 답변, 키워드로 검색할 수 있고, 분류 버튼으로 범위를 좁힐 수 있다.
**현재 장** 필터는 해당 장과 공통 질문을 함께 보여준다.
질문을 선택해도 청중 화면은 이동하지 않으며, 다른 슬라이드로 이동해도 읽던 답변은
유지된다. **대본**으로 돌아오면 대본의 스크롤 위치가 복구된다. A−/A＋는 답변 글씨에도 적용된다.
검색창에 입력 중일 때 `Q`는 글자로 입력된다. `Esc`는 답변에서 질문 목록으로,
질문 목록에서 대본으로 돌아간다. **대본** 탭이나 입력창 밖의 `Q`는 대본으로 바로 돌아간다.

슬라이드 밖에 아래 내용을 추가한다. `<template>` 안의 내용은 로딩 전에도 표시되거나
실행되지 않는다. 카드는 일반 텍스트로 읽으며 HTML·이벤트 속성은 발표자 화면에 실행되지 않는다.

```html
<template class="speaker-qa">
  <article data-qa-card data-category="질문 확인" data-pages="2,3" data-keywords="question repeat 질문 다시">
    <h3 data-qa-question>질문을 다시 듣기</h3>
    <p data-qa-question-en>Could you explain that point?</p>
    <p data-qa-answer>Could you repeat the question, please?</p>
    <p data-qa-note>영어 답변만 읽고, 이 메모는 상황 판단에 사용합니다.</p>
  </article>
</template>
```

`data-pages`는 표지·목차·구분장을 포함한 **실제 화면 번호**이며 쉼표로 구분한다.
슬라이드 밖에서 생략하면 공통 질문이다. 특정 `.slide` 안에 템플릿을 넣고 생략하면
그 장에 자동 연결된다. 질문과 답변은 필수이고 영어 질문·메모·키워드는 선택 항목이다.
`data-category`는 선택적인 분류명이다. 생략하면 **기타**로 묶인다. 분류와 질문은
원문에 처음 나타난 순서대로 표시하므로 자주 찾는 질문을 먼저 배치할 수 있다.
질문이 없거나 검색 결과가 없으면 안내를 표시한다. 창을 다시 열면 수정한 카드가 반영된다.
이 기능은 준비한 카드를 직접 찾아보는 방식이다. 음성 인식이나 자동 답변 생성은 포함하지 않는다.
카드는 청중 화면·슬라이드 미리보기·발표 PDF에서 제외되며, 노트처럼 HTML 원본에는 저장된다.

**사용자 정의 애니메이션:** `suv:media` 이벤트로 `P`/`R` 조작을 받을 수 있다.
이벤트의 `detail.action`은 `toggle` 또는 `reset`, `detail.slide`는 현재 슬라이드다.
직접 처리할 때 `event.preventDefault()`로 기본 video 처리를 막는다.

`requestAnimationFrame` 기반 스크립트 애니메이션(캔버스·SVG·숫자 등)은
`window.requestAnimationFrame` 대신
`SUVPresent.requestAnimationFrame(callback)`으로 다음 프레임을 요청하고,
`SUVPresent.cancelAnimationFrame(id)`로 취소한다. 청중 창이 가려져 브라우저가
그 창의 프레임 갱신을 멈춰도, 보이는 발표자 창이 같은 애니메이션의 갱신을 이어간다.
콜백 시간은 항상 청중 창의 `performance.now()` 기준이며 재생 상태는 원본에만 둔다.

자동 일시정지는 청중 창의 `document.hidden`만으로 판단하지 않는다.
`SUVPresent.playbackVisible()`은 두 발표 창 중 하나라도 보이면 참이다.
`suv:playbackvisibility` 이벤트의 `detail.visible`이 거짓일 때 일시정지하면,
발표자 노트로 포커스를 옮길 때 재생이 멈추지 않는다. 창을 닫거나 가리는 과정의
짧은 전환은 이 이벤트가 정리하므로 별도의 `visibilitychange` 처리와 중복하지 않는다.

```js
document.addEventListener('suv:media', function (event) {
  if (event.detail.slide !== myAnimationSlide) return;
  event.preventDefault();
  if (event.detail.action === 'reset') resetAnimation();
  else toggleAnimation();
});
```

`window.SUVPresent`의 `show(index)`는 0부터 시작하는 장 번호로 이동한다.
`getState()`, `next()`, `prev()`, `openNotes()`, `media(action)`과 `subscribe(fn)`도
사용할 수 있다. `subscribe`의 반환 함수는 연결을 해제한다. 장 전환 시 문서의
`suv:slidechange` 이벤트에는 `detail.index`와 `detail.count`가 전달된다.

---

## 슬라이드 종류

### 표지

번호, 푸터, 부제 문장을 두지 않는다. 주제는 짧은 명사구 하나로 쓴다.

```html
<section class="slide cover" data-label="Cover">
  <span class="course">Lab Seminar</span>
  <span class="kicker">Part Name In English</span>
  <h1 class="display">Deck Title</h1>
  <div class="sun-rule"></div>
  <p class="presenter">소속 발표자</p>
</section>
```

### 목차

`data-label="목차"` 를 그대로 둔다. 이 값에 글자와 줄 간격을 키우는 규칙이 걸려 있다.

![목차](imgs/02_contents.png)

### 파트 구분

장이 바뀌는 자리에 놓는다. **장 이름 하나만** 두고 머리말, 푸터, 번호, 로고를 두지 않는다.
배경은 표지와 같은 `--sky-soft` 라 덱 전체의 배경색이 흰색과 sky-soft 둘로 유지된다.

```html
<section class="slide part" data-label="파트 구분">
  <h2 class="part-name">Section Name In English</h2>
</section>
```

### 본문

`.kicker` 는 그 슬라이드가 속한 묶음 이름이며 **영어**로 쓰고 CSS 가 대문자로 바꾼다.
`.title` 은 슬라이드 제목이다. 진행 막대 폭은 현재 번호 나누기 전체 번호다.

![본문 - 글과 표](imgs/03_body_table.png)

### 결론

마지막은 Conclusion 과 Future Works 로 정리한다.

![결론](imgs/07_conclusion.png)
![향후 연구](imgs/08_future_works.png)

### 번호 매기기

- 표지, 목차, 파트 구분 슬라이드에는 번호를 매기지 않는다
- 실제 내용이 있는 첫 슬라이드가 `01`
- 분모는 번호가 붙는 슬라이드만 센다

---

## 배치

본문은 **글 영역**과 **그림 영역** 둘로 나눈다. 표와 수식은 그림 영역에 들어간다.

![배치 모델](imgs/layouts.svg)

```html
<div class="body" data-layout="right" style="--cols: 2; --split: 44%;">
  <div class="body-text">   ... 불릿, 카드 ... </div>
  <div class="body-media">  ... figure, table, 수식 ... </div>
</div>
```

| 변수 | 뜻 |
|---|---|
| `--split` | 두 영역의 비율. 첫 트랙 크기 |
| `--cols` | 그림 격자의 열 수 |
| `--ctpl` / `--rtpl` | 그림 격자의 열·행 트랙 크기 |
| `--fgap` | 그림 사이 간격 |
| `--trow` | 표의 행 높이 |

- 글과 그림이 좌우로 놓이면 **두 영역의 윗변이 같은 높이**에서 시작한다
- 그림이 여러 장이면 균일 격자로 놓아 오와 열을 맞춘다
- 한쪽을 끝까지 줄여도 내용이 반대편으로 넘치지 않는다

---

## 색

배경색은 흰색과 `--sky-soft` 두 가지만 쓴다. 그라디언트는 쓰지 않는다.

![색 토큰](imgs/palette.svg)

---

## 글자 크기

| 토큰 | 값 | 용도 |
|---|---|---|
| `--type-display` | 124px | 표지 제목 |
| `--type-title` | 76px | 슬라이드 제목 |
| `--type-subtitle` | 46px | 리드 문장 |
| `--type-body` | 36px | 본문 기본 |
| `--type-small` | 29px | 불릿, 설명 |
| `--type-code` | 30px | 코드 |
| `--type-kicker` | 26px | 키커, 푸터 |

**24px 아래로 내려가지 않는다.** 그림 안 글자도 마찬가지다.

---

## 수식

KaTeX 로 그린다. 식은 가운데, 번호는 상자 오른쪽 끝, 기호 설명은 그 아래 한 줄이다.

```html
<span class="eq">
  <span class="eq-row">
    <span class="eq-form" data-tex="y = a x^2 + b x + c"></span>
    <span class="eq-no">(1)</span>
  </span>
  <span class="eq-def"><code>a, b, c</code> 계수 · <code>x</code> 입력 · <code>y</code> 출력</span>
</span>
```

![수식 슬라이드](imgs/04_body_equation.png)

- `.eq.tight` 를 붙이면 식 글자가 25px 로 줄어든다. 그 아래로는 내리지 않는다
- `.eq.span` 은 그림 격자에서 한 줄을 다 쓴다
- 한 칸에 수식을 나란히 두면 `--rtpl: auto` 로 행을 내용 높이에 맞춘다. 윗변과 아랫변이 맞는다

### 수식 안에서 하지 않는 것

- 한글, CJK, `·` `×` `→` `≤` `≥` `∈` 같은 비 ASCII 를 넣지 않는다. 설명은 수식 밖에 쓴다
- 가운뎃점 `·`(U+00B7) 은 에러를 낸다. 곱셈은 `\cdot`, 이름 구분은 `,` 나 `-`
- 부등호와 화살표는 명령어로. `\le` `\ge` `\ne` `\to` `\times` `\in`
- `\*` 는 에러다. `T^{*}` 또는 `T^{\star}` 로 쓴다
- `\text{}` 안에는 ASCII 만 넣는다

편집 후 아래로 검사한다.

```python
import re, unicodedata
s = open('deck.html', encoding='utf-8').read()
for tex in re.findall(r'data-tex="([^"]*)"', s):
    bad = [c for c in tex if ord(c) > 127]
    if bad or '\\*' in tex:
        print(tex, [unicodedata.name(c, '?') for c in bad])
```

---

## 그림

`figure.fig` 안에 넣는다. 상자가 그림에 맞추는 것이 아니라 그림이 상자를 채운다.

```html
<figure class="fig"><span class="frame">
  <img src="imgs/example.png" alt="English label" />
</span></figure>
```

![본문 - 글과 그림](imgs/05_body_figure.png)

### 판형을 배치에 맞춘다

같은 그림도 폭이 절반이면 글자가 절반으로 줄어든다.

| 배치 | 그림 폭 | 알맞은 판형 |
|---|---|---|
| 전체 폭 | 약 1696px | 가로로 긴 도해 |
| 좌우 2열 | 약 828px | 세로로 긴 도해 |

`viewBox` 폭이 `W` 인 SVG 는 `그림 상자 폭 / W` 배로 확대된다. 화면에서 24px 이상으로 보이려면

```
SVG 안 글자 크기 >= 24 * W / 그림 상자 폭
```

**글자를 지워서 크기 문제를 해결하지 않는다. 상자 폭을 늘린다.**

### SVG 안 고정폭 글자

`<img>` 로 불러오는 SVG 는 덱이 불러온 웹폰트를 쓰지 못한다.
`font-family="monospace"` 하나만 적으면 시스템 기본 글꼴로 떨어지고,
그 글꼴이 `--` 를 긴 대시로 바꿔 놓는다. 설치된 글꼴 이름을 직접 적는다.

```svg
<text font-family="'DejaVu Sans Mono','Noto Sans Mono',monospace">--sky</text>
```

### 그림을 직접 그릴 때

- 그림 안 글자는 **영어**로 쓴다
- 그림 안에 제목을 넣지 않는다. 제목은 슬라이드가 갖는다
- 글자를 최소한으로 줄인다. 문장이 아니라 이름표다
- 슬라이드 글에 이미 있는 문장을 그림 안에 다시 적지 않는다
- 화살표 방향은 실제 인과와 같게 그린다

---

## 동영상

`figure.fig` 안에서 `img` 자리에 `video` 를 넣는다. 그림과 같은 상자 규칙을 따른다.

```html
<figure class="fig"><span class="frame">
  <video src="imgs/flight.mp4" poster="imgs/flight_poster.jpg"
         controls playsinline></video>
</span></figure>
```

### 기본값은 무음 자동 재생

**속성을 적지 않아도 소리 없이 자동으로 재생한다.** `present.js` 가 로드 시점에 모든
`video` 를 음소거로 고정하고, 발표 모드에서 슬라이드가 바뀌면 이전 동영상을 멈추고
현재 슬라이드의 동영상을 처음부터 재생한다.

| 기본값 | 이유 |
|---|---|
| 무음 | 발표장에서 소리가 터지는 사고를 막는다. 브라우저도 무음일 때만 자동 재생을 허용한다 |
| 자동 재생 | 발표자가 재생 버튼을 찾는 동안 화면이 멈춰 있지 않게 한다 |

**파일 자체도 `-an` 으로 음성 트랙을 빼서 굽는다.** 재생 쪽 음소거만 믿지 않는다.

| 속성 | 뜻 |
|---|---|
| `poster` | **필수.** PDF 에 찍히는 정지 화면. 없으면 검은 칸이 된다 |
| `controls` | 재생 막대. 눌러도 다음 장으로 넘어가지 않는다 |
| `data-noautoplay` | 자동 재생을 끈다. 발표자가 직접 눌러 시작 |
| `data-sound` | 음소거를 푼다. 소리가 내용의 일부일 때만 쓴다 |

![동영상 슬라이드](imgs/06_video.png)

poster 만들기. 사진 계열은 JPEG 가 PNG 보다 훨씬 작다.

```bash
ffmpeg -i flight.mp4 -vframes 1 flight_poster.jpg
```

화면 녹화본은 그대로 쓰기에 너무 크다. 1920 폭으로 줄여 다시 굽는다.

```bash
ffmpeg -i master.mp4 -vf scale=1920:-2 -c:v libx264 -preset slow -crf 28 \
  -pix_fmt yuv420p -movflags +faststart -an flight.mp4
```

원본은 저장소에 올리지 말고 따로 보관한다. 덱에는 변환본만 넣는다.

동영상은 **HTML 에 끼워 넣지 않고 별도 파일로 둔다.** `imgs/` 에 두고 경로로 참조한다.
base64 로 넣으면 용량이 33% 늘고 탐색이 느려지며 편집과 버전 관리가 어려워진다.

배포할 때는 HTML, CSS, JS, `imgs/` 를 폴더째 함께 보낸다.

---

## 표

```html
<table class="tbl" data-fixed style="--trow: 20px;">
  <colgroup><col style="width: 40%" /><col style="width: 60%" /></colgroup>
  <thead><tr><th>Header</th><th>Header</th></tr></thead>
  <tbody>
    <tr><td>항목</td><td>내용</td></tr>
  </tbody>
</table>
```

- 머리행은 **영어**로 쓴다
- 열 폭은 `<colgroup>` 에 퍼센트로 적고 `data-fixed` 를 붙인다. 자동 배치는 `<col>` 폭을 무시한다
- 행 높이는 `--trow` 로 정한다. 표 전체가 한 값을 공유해 행이 고르게 유지된다
- 내용이 많아 아래가 잘리면 `--trow` 를 줄이고, 그래도 넘치면 표에 `style="font-size: 25px"` 를 준다

---

## 본문 요소

| 클래스 | 설명 |
|---|---|
| `.lead` | 슬라이드 한 줄 요약 |
| `.cols` / `.cols-wide` / `.cols3` | 2열 / 비대칭 2열 / 3열 |
| `.grid4` / `.grid8` | 2x2 카드, 2열 용어 목록 |
| `.card` | 기본 카드. `.soft` 파랑, `.good` 초록, `.warn` 산호 |
| `.ul` | 불릿 목록. `.leaf` `.coral` 로 점 색 변경 |
| `.chip` | 알약 모양 태그 |
| `.tbl` | 표 |
| `pre.code` / `pre.term` | 코드 / 터미널 블록 |
| `figure.fig` | 그림 |

불릿은 `<strong>말머리</strong> — 설명` 형태로 쓴다. 대시는 전각이 아니라 `—` 다.

**카드는 아껴 쓴다.** 슬라이드 아래쪽에 요약 카드를 습관적으로 붙이지 않는다.

---

## 하지 않는 것

- 이모지
- 그라디언트 배경
- 24px 미만 글자. 그림 안 글자를 포함한다
- 색만으로 의미 전달. 경고는 색과 제목과 문구를 같이 쓴다
- 한 덱에 배경색 3가지 이상
- 표지에 부제 문장
- 표지, 목차, 파트 구분 슬라이드에 번호
- 슬라이드에 출처 캡션
- 습관적인 하단 요약 카드
- 그림 안에 슬라이드 글과 같은 문장

---

## 인쇄에서 그림이 푸터를 덮는 문제

크롬은 인쇄 분할 단계에서 `.body` 에 채움 높이를 주지 않는다. 화면에서 약 600px 인
본문 상자가 인쇄에서는 글 높이로 줄고, 그 결과 그림이 원본 비율대로 커지면서 푸터를 덮는다.

부모에서 높이를 내려주는 방식으로는 해결되지 않는다. 인쇄에서 확실히 아는 값은
페이지 높이뿐이므로, `deck.css` 는 인쇄에서만 `.body` 높이를 `63vh` 로 직접 묶는다.
값을 바꿀 때는 전 쪽의 하단 띠를 훑어 침범이 없는지 확인한다.

---

## 파일

```
deck.css        디자인 구현
layout.css      배치 규칙. 배치 관련 규칙은 여기에만 둔다
present.js      전체 화면 발표, 동영상
presenter.js    별도 발표자 노트 화면
template.html   빈 덱 뼈대
mydesign.md     디자인 규격 원문. 왜 그렇게 정했는지가 적혀 있다
assets/         로고 예시
imgs/           이 문서의 그림
```

이 폴더가 `deck.css`, `layout.css`, `present.js`, `presenter.js`, `mydesign.md` 의 유일한 원본이다.
덱 쪽 사본은 빌드가 여기서 내려보낸다. 고칠 때는 이 폴더의 파일을 고친다.

편집기가 만드는 `cde-layout.css` 는 저장할 때마다 다시 쓰이므로 손대지 않는다.
배치 규칙은 `layout.css` 에 둔다. 선택자를 더 구체적으로 쓰면 뒤에 실리는 그 파일보다 이긴다.
