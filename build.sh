#!/usr/bin/env bash
# 덱을 굽는다.
#   ./build.sh            build/ 의 덱 HTML 을 찾아서 굽는다
#   ./build.sh "<타이틀>_<학생이름>"   그 덱만 굽는다
#
# 결과물
#   output/<덱>.html  배포물. CSS, JS, 그림, 동영상, 폰트, 수식 SVG 를 모두 담은 단일 HTML.
#                     이 파일 하나만 받으면 오프라인에서도 열린다
#   output/<덱>.pdf   슬라이드 하나가 한 쪽. output/ 에는 이 두 파일만 둔다
#
# 폴더 구실
#   design/     디자인 원본. deck.css, layout.css, present.js, presenter.js, mydesign.md, template.html
#   build/      덱 원본(편집 대상)과 중간 파일. 덱 HTML, imgs/, 디자인 사본
#   output/     배포물. 단일 HTML 과 PDF 두 파일뿐이다. 덱 이름은 <타이틀>_<학생이름> 이다
#   materials/  근거 자료와 원본 미디어. 배포물에 들어가지 않는다
#
# 이 스크립트는 design/ 의 디자인 파일을 build/ 로 내려보내고, 단일 HTML 과 PDF 를 굽는다.
# build/ 안의 덱 HTML 과 imgs/ 는 건드리지 않는다.
set -euo pipefail
cd "$(dirname "$0")"

# 예전 구조는 덱 원본을 output/ 에 두었다. 한 번만 build/ 로 옮기고 이전 배포물은 버린다
if [ ! -d build ] && [ -d output ]; then
  echo "output/ 의 덱 원본을 build/ 로 옮긴다"
  mv output build
  rm -f build/*.standalone.html build/*.pdf
fi

DECK=${1:-}
if [ -z "$DECK" ]; then
  # 덱 후보는 build/ 바로 아래 HTML 하나다. 여럿이면 이름을 인자로 받는다
  mapfile -t found < <(find build -maxdepth 1 -name '*.html' -printf '%f\n' 2>/dev/null | sort)
  case ${#found[@]} in
    0) echo "build/ 에 덱 HTML 이 없다. 클로드에 \"컨텐츠 제작\" 을 먼저 지시한다" >&2; exit 1 ;;
    1) DECK=${found[0]%.html} ;;
    *) echo "build/ 에 덱이 여럿이다. 이름을 인자로 준다: ${found[*]%.html}" >&2; exit 1 ;;
  esac
fi
[ -f "build/$DECK.html" ] || { echo "build/$DECK.html 이 없다" >&2; exit 1; }

# 1) 디자인 파일을 덱 옆으로 내려보낸다. design/ 이 유일한 원본이다
cp design/deck.css design/layout.css design/present.js design/presenter.js build/
# 로고는 deck.css 의 --lab-logo 가 참조하는 이름으로 둔다. 이미 있으면 그대로 쓴다
[ -f build/suvlab_logo.png ] || cp design/assets/lab_logo.png build/suvlab_logo.png

# 2) 배포용 단일 HTML - 외부 파일 없이 열리도록 모든 자원을 넣는다. 원격 자원은 지금 내려받는다
#    수식(data-tex)은 latex + dvisvgm 으로 SVG 그림이 된다. KaTeX 없이 보인다
# output/ 에는 배포물 두 파일만 둔다. 이전 빌드나 다른 덱의 파일은 지운다
rm -rf output && mkdir -p output
python3 bundle.py "build/$DECK.html" "output/$DECK.html"

# 3) PDF - 단일 HTML 을 인쇄한다. 슬라이드 하나가 한 쪽이 된다 (1440x810pt)
#    --virtual-time-budget 은 그림과 웹폰트를 기다리는 시간이다
( cd output && google-chrome --headless=new --disable-gpu --no-sandbox \
    --no-pdf-header-footer --virtual-time-budget=30000 \
    --print-to-pdf="$DECK.pdf" "$DECK.html" >/dev/null 2>&1 )
echo "output/$DECK.pdf  $(pdfinfo "output/$DECK.pdf" | awk '/^Pages/{print $2}')p"

# 4) 덱이 참조하지 않는 파일이 build/imgs 에 남아 있는지 알려 준다
for f in build/imgs/*; do
  [ -e "$f" ] || continue
  name=$(basename "$f")
  grep -q "imgs/$name" "build/$DECK.html" || echo "  미참조: imgs/$name"
done

echo "output/"
find output -type f | sort | sed 's/^/  /'
