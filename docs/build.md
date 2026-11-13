# 빌드와 배포

"컨텐츠 제작" 에서 클로드가 `build.sh` 를 실행한다. 덱 HTML 또는 `design/` 을 직접
수정한 경우에만 사용자가 실행한다.

```bash
./build.sh                                             # build/ 의 덱 HTML 을 대상으로 한다
./build.sh EKFBasedStateEstimationForIndoorUAV_홍길동   # 덱이 여럿인 경우 이름을 지정한다
```

## 폴더 구조

| 폴더 | 내용 |
|---|---|
| `design/` | 디자인 원본. `deck.css`, `layout.css`, `present.js`, `presenter.js`, `editor-host.js`, `mydesign.md`, `template.html` |
| `materials/` | 근거 자료와 원본 미디어. 배포물에 들어가지 않는다 |
| `build/` | 덱 원본(편집 대상)과 중간 파일. 덱 HTML, `imgs/`, 디자인 사본, 로고 |
| `output/` | 배포물. 단일 HTML 과 PDF 두 파일만 둔다 |

`build.sh` 는 실행할 때마다 `output/` 을 비우고 다시 만든다. 지난 빌드 뒤에 `에디터` 로 수정된
배포 HTML 이 있으면 지우기 전에 `build/edited-<시각>/` 에 백업한다. 예전 구조처럼 덱 원본이
`output/` 에 있으면 처음 한 번 `build/` 로 옮긴다.

## 빌드 단계

1. `design/` 의 CSS, JS, 로고를 `build/` 로 복사한다. `design/` 이 유일한 원본이다
2. `bundle.py` 가 `build/<덱>.html` 을 단일 HTML `output/<덱>.html` 로 묶는다
3. 헤드리스 Chrome 이 단일 HTML 을 인쇄하여 `output/<덱>.pdf` 를 만든다 (1440x810pt)
4. `build/imgs/` 에 덱이 참조하지 않는 파일이 있으면 알려 준다

## 단일 HTML

`bundle.py` 는 Python 표준 라이브러리만 사용한다. 다음을 모두 HTML 안에 넣는다.

- CSS, `present.js`, 발표자 창 `presenter.js`
- 편집기 `editor/app` 과 `editor-host.js`. `에디터` 버튼이 서버 없이 이 편집기를 연다. `editor/` 서브모듈이 없으면 버튼 없이 빌드한다
- 그림, 동영상, poster, 로고 (base64)
- Google Fonts. 덱에 쓰인 글자가 속한 subset 만 넣는다
- 수식 그림 (아래)

원격 자원은 빌드할 때 내려받으므로 빌드 시에만 네트워크가 필요하다. 넣지 못한 자원이
있으면 목록을 출력하고 실패로 끝난다. 동영상은 base64 로 들어가므로 파일 크기가 원본보다
약 1.33 배 커진다.

## 수식

덱 HTML 에는 수식을 TeX 로 작성한다.

```html
<span class="eq-form" data-tex="K_{k} = P_{k}^{-}H^{\top}\left(H P_{k}^{-} H^{\top} + R_{k}\right)^{-1}"></span>
```

빌드할 때 `latex` 와 `dvisvgm --no-fonts` 가 각 수식을 글리프가 경로로 바뀐 SVG 그림으로
만든다. 배포 HTML 과 PDF 를 보는 쪽에는 LaTeX, KaTeX, 수식 폰트가 필요 없다. 그림의
바탕은 투명하고, 색은 덱의 `--ink` 를 따른다. 원본 TeX 는 `data-tex-src` 와 `alt` 에
남는다.

조판에 실패한 수식이 있으면 그 수식만 KaTeX 로 남기고 빌드는 실패로 끝난다. 수식 안에는
ASCII 만 넣고, KaTeX 전용 명령을 쓰지 않는다.

## 필요 도구

| 도구 | 용도 |
|---|---|
| `google-chrome` | HTML 을 PDF 로 인쇄 |
| `pdfinfo` (poppler-utils) | 쪽수 확인 |
| `python3` | `bundle.py`, 슬라이드 편집기 |
| `latex`, `dvisvgm` (TeX Live) | 수식을 SVG 로 변환 |
| `ffmpeg` | 동영상 변환과 poster 추출. 동영상을 사용할 때만 필요 |
