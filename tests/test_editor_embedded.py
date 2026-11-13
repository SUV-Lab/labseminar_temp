#!/usr/bin/env python3
"""In-deck editor of the single-file deck, opened directly as a file, no server.

Bundles a small deck with bundle.py, opens the editor over the page from its
"에디터" button, edits a title, saves through a stubbed browser file-save dialog,
checks that closing or saving shows the edit in place, that only the first save
asks for the file, and reopens the saved file. Needs the
editor/ submodule.
"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from test_presenter_displays import evaluate, wait_for
from chrome_driver import ChromeSession
from test_presenter_qa import load, make_fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bundle  # noqa: E402

FRAME = 'document.querySelector("iframe[data-suv-ui][title=\\"슬라이드 편집\\"]")'
ED = FRAME + '.contentWindow'
STAGE = ED + '.document.querySelector("#stage").contentDocument'


def make_deck(folder):
    source = make_fixture(folder / 'src', with_qa=False)
    shutil.copy2(ROOT / 'design' / 'editor-host.js', source.parent / 'editor-host.js')
    text = source.read_text().replace('<h1>Public slide one</h1>', '<h1 class="title">Public slide one</h1>')
    source.write_text(text)
    deck = folder / 'deck.html'
    deck.write_text(bundle.bundle(source))  # remote fonts may be missing offline; not needed here
    return deck


def press(c, expression):
    """Real mouse click on an element found by a JS expression (frames sit at 0,0)."""
    point = evaluate(c, '(()=>{const r=(%s).getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()'
                     % expression)
    for kind in ('mousePressed', 'mouseReleased'):
        c.call('Input.dispatchMouseEvent', {'type': kind, 'button': 'left', 'clickCount': 1, **point})


def open_editor(c):
    press(c, 'document.querySelector(".editor-btn")')
    wait_for(c, '!!%s && %s.document.querySelector("#status")?.textContent==="준비됨"' % (FRAME, ED), 15)
    # A handle picked in the editor frame dies when the frame closes after a save,
    # so the dialog must be opened by the deck page.
    evaluate(c, '%s.showSaveFilePicker=%s.showOpenFilePicker=async()=>{throw new Error("picker called in the editor frame")}'
             % (ED, ED))


def ctrl_s(c, key='s'):
    """Ctrl+S; key "ㄴ" is what a Korean IME reports for the same physical key."""
    args = {'modifiers': 2, 'key': key, 'code': 'KeyS', 'windowsVirtualKeyCode': 83, 'nativeVirtualKeyCode': 83}
    c.call('Input.dispatchKeyEvent', {'type': 'rawKeyDown', **args})
    c.call('Input.dispatchKeyEvent', {'type': 'keyUp', **args})


def stub_picker(c, name, ours=True):
    """The file dialog cannot be driven headless: the open picker hands back a
    file that is (ours) or is not this deck, and records what would be written."""
    evaluate(c, '''(()=>{window.__saved=[];window.__picked=0;
      const text=%s?document.querySelector('meta[name="suv-deck-id"]').outerHTML:"<html>another deck</html>";
      window.showOpenFilePicker=async(o)=>{__picked++;window.__opts=o;
        return [{name:%s,getFile:async()=>({text:async()=>text}),
                 createWritable:async()=>({write:async t=>__saved.push(String(t)),close:async()=>{}})}]}})()'''
             % ('true' if ours else 'false', json.dumps(name)))


def edit_title(c, text):
    evaluate(c, '(()=>{const t=%s.querySelector(".title");t.focus();'
                'const r=t.ownerDocument.createRange();r.selectNodeContents(t);r.collapse(false);'
                'const s=t.ownerDocument.getSelection();s.removeAllRanges();s.addRange(r)})()' % STAGE)
    c.call('Input.insertText', {'text': text})
    wait_for(c, STAGE + '.querySelector(".title").textContent.endsWith(%s)' % json.dumps(text))


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix='editor-fixture-') as tmp:
        deck = make_deck(Path(tmp))
        with load(deck) as c:
            c.call('Browser.grantPermissions', {'permissions': ['clipboardReadWrite', 'clipboardSanitizedWrite']})
            assert evaluate(c, 'document.querySelectorAll(".present-btn").length') == 4
            # Opened normally, the deck fits the window width (no sideways scroll).
            fitted = evaluate(c, '''(()=>{const r=document.querySelector(".slide").getBoundingClientRect(),w=document.documentElement;
              return [Math.round(r.width), w.clientWidth, w.scrollWidth]})()''')
            assert abs(fitted[0] - fitted[1]) <= 1 and fitted[2] <= fitted[1], fitted
            checks.append('The deck opens fitted to the browser window width')
            open_editor(c)
            assert evaluate(c, 'innerWidth') == evaluate(c, '%s.getBoundingClientRect().width' % FRAME)
            assert len([t for t in c.call('Target.getTargets')['targetInfos'] if t['type'] == 'page']) == 1
            assert evaluate(c, STAGE + '.querySelectorAll("section.slide").length') == 3
            assert evaluate(c, STAGE + '.querySelectorAll(".present-btn,[data-suv-ui]").length') == 0
            assert evaluate(c, 'getComputedStyle(%s.document.querySelector("label.chk")).display' % ED) == 'none'
            assert '1회 선택' in evaluate(c, '%s.document.querySelector(".bar").textContent' % ED)
            # Toolbar stays on one line: no button wraps into a tall column.
            tall = evaluate(c, '''[...%s.document.querySelectorAll(".bar button")]
              .filter(b=>b.offsetParent&&b.getBoundingClientRect().height>40).map(b=>b.textContent)''' % ED)
            assert tall == [], tall
            cut = evaluate(c, '''[...%s.document.querySelectorAll(".bar button")]
              .filter(b=>b.offsetParent&&b.getBoundingClientRect().right>innerWidth).map(b=>b.textContent)''' % ED)
            assert cut == [], cut
            c.screenshot(out / 'editor.png')
            checks.append('에디터 opens over the current page (no new window), offline, without presentation UI')

            # 닫기 applies the edit to the page in place, without a file dialog.
            evaluate(c, 'window.__marker=1')
            edit_title(c, ' EDITED')
            press(c, '[...%s.document.querySelectorAll(".bar button")].find(b=>b.textContent==="닫기")' % ED)
            wait_for(c, '!%s && document.querySelector(".slide .title")?.textContent==="Public slide one EDITED"' % FRAME, 10)
            assert evaluate(c, 'window.__marker') == 1, '닫기 must not reload the page'
            assert evaluate(c, '__suvEditorState.unsaved') is True
            assert evaluate(c, 'document.querySelectorAll(".present-btn").length') == 4
            checks.append('닫기 shows the edit on the deck at once, without a reload, and marks it unsaved')

            # First save asks for the file once; the edit stays on the page.
            open_editor(c)
            assert evaluate(c, STAGE + '.querySelector(".title").textContent') == 'Public slide one EDITED'
            stub_picker(c, 'deck.html')
            # Ctrl+S is not a click for Chrome: before a file is picked it must not
            # try the picker (Chrome refuses it) and must say what to do.
            edit_title(c, '')
            ctrl_s(c)
            wait_for(c, '%s.document.querySelector("#status").textContent.startsWith("처음 한 번은")' % ED, 10)
            assert evaluate(c, '__picked') == 0 and evaluate(c, '!!' + FRAME)
            checks.append('Ctrl+S before the file is picked explains the one click instead of failing')
            # A same-named copy somewhere else is refused: a reload would not show it.
            stub_picker(c, 'deck.html', ours=False)
            press(c, '%s.document.querySelector(\'[data-act="save"]\')' % ED)
            wait_for(c, '%s.document.querySelector("#status").textContent.startsWith("고른 파일")' % ED, 10)
            assert evaluate(c, '__saved.length') == 0 and evaluate(c, '!!' + FRAME)
            checks.append('Picking a file other than the opened deck is refused, nothing is written')
            # The dialog cannot be opened at a path: the deck path goes to the clipboard
            # (Ctrl+L, Ctrl+V, Enter) and the id makes Chrome remember the folder.
            assert evaluate(c, '__opts.id') == 'suv-deck' and evaluate(c, '!("startIn" in __opts)')
            assert evaluate(c, '%s.navigator.clipboard.readText()' % ED) == str(deck), 'deck path not copied'
            checks.append('The first file dialog gets the deck path on the clipboard and remembers the folder')
            stub_picker(c, 'deck.html')
            edit_title(c, ' TWICE')
            press(c, '%s.document.querySelector(\'[data-act="save"]\')' % ED)
            wait_for(c, '!%s && document.querySelector(".slide .title")?.textContent.endsWith("TWICE")' % FRAME, 10)
            assert evaluate(c, '__picked') == 1
            assert evaluate(c, 'window.__marker') == 1, 'saving must not reload the page'
            assert evaluate(c, '__suvEditorState.unsaved') is False
            saved = evaluate(c, '__saved[__saved.length-1]')
            assert 'Public slide one EDITED TWICE' in saved
            # Inspect elements, not text: the embedded scripts mention these names.
            leftovers = evaluate(c, '''(()=>{const d=new DOMParser().parseFromString(__saved[__saved.length-1],"text/html");
              return {ui:d.querySelectorAll("[data-suv-ui],[data-cde-ui],.present-btn,[contenteditable],.slide.current,[data-cde-slide]").length,
                link:d.querySelectorAll('link[href$="cde-layout.css"]').length,
                layout:d.querySelectorAll("style[data-suv-cde-layout]").length,
                body:d.body.className+"|"+(d.body.getAttribute("style")||""),
                root:d.documentElement.getAttribute("style")}})()''')
            assert leftovers == {'ui': 0, 'link': 0, 'layout': 1, 'body': '|', 'root': None}, leftovers
            assert 'SUVEditorApp' in saved
            assert evaluate(c, 'getComputedStyle(document.documentElement).overflow') != 'hidden'
            checks.append('First save asks for the file, writes a self-contained deck, and returns to it')

            # Later saves go straight to the same file.
            open_editor(c)
            assert '한 번 고른다' not in evaluate(c, '%s.document.querySelector(".bar").textContent' % ED)
            evaluate(c, 'window.showOpenFilePicker=async()=>{__picked++;throw new DOMException("x","AbortError")}')
            src = evaluate(c, '''%s.fetch("/_upload?name=a.png",{method:"POST",body:new File(["x"],"a.png",{type:"image/png"})})
                                 .then(r=>r.json()).then(j=>j.src)''' % ED)
            assert src.startswith('data:image/png;base64,'), src[:40]
            checks.append('Picked images become data URIs inside the deck')
            edit_title(c, ' 3')
            ctrl_s(c, 'ㄴ')
            wait_for(c, '!%s && document.querySelector(".slide .title")?.textContent.endsWith("TWICE 3")' % FRAME, 10)
            assert evaluate(c, '__picked') == 1, 'the second save must not show the file dialog'
            assert evaluate(c, '__saved.length') == 2
            checks.append('Later saves (Ctrl+S, also with a Korean IME) write to the same file without a dialog')

            # A cancelled dialog is reported as cancelled, not as a failure.
            open_editor(c)
            evaluate(c, 'window.showSaveFilePicker=async()=>{throw new DOMException("x","AbortError")};%s.prompt=()=>"copy.html"'
                     % ED)
            edit_title(c, ' X')
            press(c, '[...%s.document.querySelectorAll("button")].find(b=>b.textContent.includes("다른 이름"))' % ED)
            wait_for(c, '%s.document.querySelector("#status").textContent.startsWith("저장 취소")' % ED, 10)
            assert evaluate(c, '!!' + FRAME)
            checks.append('Cancelling the file dialog keeps the editor open and says so')
            press(c, '[...%s.document.querySelectorAll(".bar button")].find(b=>b.textContent==="닫기")' % ED)
            wait_for(c, '!%s && document.querySelector(".slide .title")?.textContent.endsWith("3 X")' % FRAME, 10)
            assert evaluate(c, '__suvEditorState.unsaved') is True

            # Ctrl+S on the deck page saves the applied edit, not the browser's "Save page as".
            evaluate(c, 'window.__picked=0;window.showOpenFilePicker=async()=>{__picked++;throw new DOMException("x","AbortError")}')
            ctrl_s(c)
            wait_for(c, '__saved.length===3 && !__suvEditorState.unsaved', 10)
            assert evaluate(c, '__picked') == 0
            assert '3 X' in evaluate(c, '__saved[2]')
            assert evaluate(c, 'new DOMParser().parseFromString(__saved[2],"text/html").querySelectorAll("[data-suv-ui],.present-btn").length') == 0
            checks.append('Ctrl+S on the deck page writes the deck to its file without a dialog')

            c.key('f')
            wait_for(c, 'document.body.classList.contains("presenting")')
            # Presenting scales to the screen by itself; the width fit must not apply.
            assert evaluate(c, 'getComputedStyle(document.querySelector("deck-stage")).zoom') == '1'
            errors = [ev for ev in c.events if ev.get('method') == 'Runtime.exceptionThrown']
            assert not errors, json.dumps(errors)[:500]
            checks.append('The page keeps presenting after edits were applied in place')

        (Path(tmp) / 'saved.html').write_text(saved)
        with load(Path(tmp) / 'saved.html') as c:
            assert evaluate(c, 'document.querySelector(".slide .title").textContent') == 'Public slide one EDITED TWICE'
            assert evaluate(c, 'document.querySelectorAll(".present-btn").length') == 4
            c.key('f')
            wait_for(c, 'document.body.classList.contains("presenting")')
            errors = [ev for ev in c.events if ev.get('method') == 'Runtime.exceptionThrown']
            assert not errors, json.dumps(errors)[:500]
            checks.append('The saved file reopens as a working deck with the edit and one set of buttons')

        # Real FileSystemFileHandle (origin private file system needs http, not file://):
        # the handle must still write after the editor frame is gone and the page rewritten.
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        plain = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1',
                                  '--directory', tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        c = ChromeSession(width=1280, height=850)
        try:
            time.sleep(0.5)
            c.navigate('http://127.0.0.1:%d/deck.html' % port)
            wait_for(c, 'document.readyState==="complete" && !!window.SUVPresent', 15)
            # The picked file is this deck: same content as the page was loaded from.
            evaluate(c, '''(async()=>{const d=await navigator.storage.getDirectory();
              const h=await d.getFileHandle("deck.html",{create:true});window.__picked=0;
              const w=await h.createWritable();await w.write(await (await fetch(location.href)).text());await w.close();
              window.showOpenFilePicker=async(o)=>{__picked++;window.__opts=o;return [h]}})()''')
            for text in (' REAL', ' TWO'):
                open_editor(c)
                edit_title(c, text)
                if text == ' REAL':
                    press(c, '%s.document.querySelector(\'[data-act="save"]\')' % ED)
                else:
                    ctrl_s(c)
                wait_for(c, '!%s && document.querySelector(".slide .title")?.textContent.endsWith(%s)'
                         % (FRAME, json.dumps(text)), 10)
            written = evaluate(c, '''navigator.storage.getDirectory().then(d=>d.getFileHandle("deck.html"))
                                     .then(h=>h.getFile()).then(f=>f.text())''')
            assert 'Public slide one REAL TWO' in written, written[:200]
            assert evaluate(c, '__picked') == 1
            checks.append('A real file handle keeps writing after the editor closes and the page is rewritten')
        finally:
            c.close()
            plain.terminate()

    report = dict(result='PASS', checks=checks, transport='offline file://, plus localhost for a real file handle')
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
