#!/usr/bin/env bash
# 덱 HTML 을 브라우저에서 고친다.
#   ./editor.sh                 build/ 의 덱을 모두 연다
#   ./editor.sh build/x.html    덱 하나만 연다
#   ./editor.sh --port 8899     포트를 지정한다. 기본은 8770 부터 비어 있는 포트
#   ./editor.sh --no-open       브라우저를 띄우지 않는다
#
# 편집기 본체는 editor/ 서브모듈이다. 없으면 여기서 내려받는다.
# 고친 결과는 덱 HTML 에 바로 저장된다. PDF 는 ./build.sh 로 다시 굽는다.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f editor/editor.py ]; then
  echo "editor/ 서브모듈을 내려받는다"
  git submodule update --init editor
fi

# 인자에 경로가 없으면 build/ 를 연다. --port 뒤의 값은 경로가 아니다
target_given=0
skip_next=0
for a in "$@"; do
  if [ "$skip_next" -eq 1 ]; then skip_next=0; continue; fi
  case "$a" in
    --port) skip_next=1 ;;
    -*) ;;
    *) target_given=1 ;;
  esac
done
if [ "$target_given" -eq 0 ]; then
  [ -d build ] || { echo "build/ 가 없다. ./create.sh 를 먼저 실행한다" >&2; exit 1; }
  set -- build "$@"
fi

# --port 를 주지 않았으면 비어 있는 포트를 고른다. 편집기를 둘 이상 띄워도 충돌하지 않는다
port_given=0
for a in "$@"; do
  case "$a" in --port|--port=*) port_given=1 ;; esac
done
if [ "$port_given" -eq 0 ]; then
  port=$(python3 -c "
import socket
for p in range(8770, 8790):
    s = socket.socket()
    free = s.connect_ex(('127.0.0.1', p)) != 0
    s.close()
    if free:
        print(p)
        break
else:
    print(0)
")
  [ "$port" != "0" ] || { echo "8770-8789 에 빈 포트가 없다. --port 로 지정한다" >&2; exit 1; }
  set -- "$@" --port "$port"
fi

exec python3 editor/editor.py "$@"
