#!/usr/bin/env bash
# 덱을 굽는다.
#   ./build.sh            output/ 의 HTML 을 찾아서 굽는다
#   ./build.sh "<타이틀>_<학생이름>"   그 덱만 굽는다
#
# 폴더 구실
#   design/     디자인 원본. deck.css, layout.css, present.js, presenter.js, mydesign.md, template.html
#   output/     덱 원본과 배포물. 덱 이름은 <타이틀>_<학생이름> 이다
#   materials/  근거 자료와 원본 미디어. 배포물에 들어가지 않는다
#
# 이 스크립트는 design/ 의 디자인 파일을 output/ 으로 내려보내고 PDF 를 굽는다.
# output/ 안의 HTML 과 imgs/ 는 건드리지 않는다.
set -euo pipefail
cd "$(dirname "$0")"

DECK=${1:-}
if [ -z "$DECK" ]; then
  # 덱 후보는 output/ 바로 아래 HTML 하나다. 여럿이면 이름을 인자로 받는다
  mapfile -t found < <(find output -maxdepth 1 -name '*.html' -printf '%f\n' 2>/dev/null | sort)
  case ${#found[@]} in
    0) echo "output/ 에 덱 HTML 이 없다. 클로드에 \"컨텐츠 제작\" 을 먼저 지시한다" >&2; exit 1 ;;
    1) DECK=${found[0]%.html} ;;
    *) echo "output/ 에 덱이 여럿이다. 이름을 인자로 준다: ${found[*]%.html}" >&2; exit 1 ;;
  esac
fi
[ -f "output/$DECK.html" ] || { echo "output/$DECK.html 이 없다" >&2; exit 1; }

# 1) 디자인 파일을 덱 옆으로 내려보낸다. design/ 이 유일한 원본이다
cp design/deck.css design/layout.css design/present.js design/presenter.js output/
# 로고는 deck.css 의 --lab-logo 가 참조하는 이름으로 둔다. 이미 있으면 그대로 쓴다
[ -f output/suvlab_logo.png ] || cp design/assets/lab_logo.png output/suvlab_logo.png

# 2) PDF - 슬라이드 하나가 한 쪽이 된다 (1440x810pt)
#    --virtual-time-budget 은 KaTeX 와 웹폰트를 기다리는 시간이다. 수식이 비면 늘린다
( cd output && google-chrome --headless=new --disable-gpu --no-sandbox \
    --no-pdf-header-footer --virtual-time-budget=30000 \
    --print-to-pdf="$DECK.pdf" "$DECK.html" >/dev/null 2>&1 )
echo "output/$DECK.pdf  $(pdfinfo "output/$DECK.pdf" | awk '/^Pages/{print $2}')p"

# 3) 덱이 참조하지 않는 파일이 output/imgs 에 남아 있는지 알려 준다
for f in output/imgs/*; do
  [ -e "$f" ] || continue
  name=$(basename "$f")
  grep -q "imgs/$name" "output/$DECK.html" || echo "  미참조: imgs/$name"
done

echo "output/"
find output -type f | sort | sed 's/^/  /'
