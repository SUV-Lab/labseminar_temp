# SUVLab 랩세미나 발표자료 양식

발표 내용을 `contents.md` 에 문장 단위로 작성하면, 클로드가 `design/mydesign.md` 규격에
맞추어 슬라이드 원고와 검토 의견을 작성하고, 배포용 HTML 과 PDF 를 생성한다.

## 주요 기능

- 1920x1080 (16:9) 아트보드. 슬라이드 한 장이 PDF 한 쪽이다
- 원거리 가독성을 위한 서체와 24px 하한, 그림, 수식, 표의 격자 정렬
- **단일 HTML 배포**: CSS, JS, 그림, 동영상, 폰트를 모두 담은 HTML 파일 하나로 오프라인 발표
- **수식 SVG**: TeX 로 작성한 수식을 빌드할 때 SVG 그림으로 변환한다. 보는 쪽에 LaTeX 가 필요 없다
- **전체 화면 발표**: `F` 로 시작, 동영상 자동 재생, 마우스 커서가 레이저 포인터로 바뀐다
- **발표자 노트** (`N`): 현재 장 실시간 미리보기, 다음 장, 대본, 타이머, Q&A, 외부 화면 자동 배치
- **레이저 포인터 공유**: 청중 화면의 마우스 위치가 노트 창에 보이고, 노트 창 미리보기에서 가리킨 위치가 청중 화면에 표시된다
- **동영상 원격 제어**: 노트 창 미리보기의 `재생` / `일시정지` 버튼으로 청중 화면의 동영상을 조작한다
- **덱 안의 에디터**: 배포 HTML 의 `에디터` 버튼으로 서버 없이 글, 순서, 배치, 그림을 고치고 그 파일에 저장한다

## 빠른 시작

```bash
./create.sh          # contents.md, materials/, build/imgs/ 생성
```

1. `contents.md` 에 발표 내용을 작성한다. 원본 그림과 동영상은 `materials/` 에 둔다
2. 클로드에 **"컨텐츠 제작"** 을 지시한다
3. `review.md` 의 지적 사항을 `contents.md` 에 반영하고 2 를 반복한다
4. `output/<타이틀>_<학생이름>.html` 을 브라우저에서 열고 `F` 를 누른다. 고칠 곳은 덱 안의 `에디터` 로 고친다

| 경로 | 내용 |
|---|---|
| `output/<타이틀>_<학생이름>.html` | 배포용 단일 HTML. 이 파일 하나만 옮겨 발표한다 |
| `output/<타이틀>_<학생이름>.pdf` | PDF |
| `build/` | 덱 원본(편집 대상)과 중간 파일 |
| `slide.md`, `review.md` | 슬라이드 원고, 검토 의견 |

![표지 예시](instruction/example/imgs/example-01.png)

## 설치

```bash
git clone --recurse-submodules https://github.com/SUV-Lab/labseminar_temp.git
cd labseminar_temp
sudo apt install poppler-utils ffmpeg texlive-latex-base dvisvgm
```

Google Chrome 과 Python 3 가 필요하다. 이미 복제한 경우 `git submodule update --init` 으로
편집기 서브모듈을 받는다.

## 문서

| 문서 | 내용 |
|---|---|
| [docs/usage.md](docs/usage.md) | 작성부터 제작까지의 단계, `contents.md` 와 `slide.md` 표기, 편집기, 예제 |
| [docs/presenting.md](docs/presenting.md) | 단축키, 레이저 포인터, 발표자 노트, Q&A, 외부 화면 연결 |
| [docs/build.md](docs/build.md) | `build.sh`, 폴더 구조, 단일 HTML, 수식 SVG, 필요 도구 |
| [design/README.md](design/README.md) | 슬라이드 종류와 배치 규칙 |
| [instruction.md](instruction.md) | 클로드 작업 지시 |
| [tests/README.md](tests/README.md) | 브라우저 검증 실행 |
