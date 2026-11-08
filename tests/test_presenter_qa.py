#!/usr/bin/env python3
"""Private Q&A lookup in real offline Chromium; no domain-specific content.

The fixture checks audience/PDF exclusion, plain-text answer rendering, and
keyboard/scroll behavior in the dedicated Q&A browsing view.
"""
import argparse
import base64
import html
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from chrome_driver import ChromeSession
from test_presenter import attach, targets
from test_presenter_displays import click, evaluate, wait_for

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'PRIVATE_QA_'
LITERAL = '<img src="missing.png" onerror="window.qaInjected=1">'


def make_fixture(folder, with_qa=True):
    folder.mkdir(parents=True, exist_ok=True)
    for name in ('present.js', 'presenter.js', 'deck.css'):
        shutil.copy2(ROOT / 'design' / name, folder / name)
    paragraphs = ''.join('<p>Script line %d. This is public-speaking practice text for a long presenter note.</p>' % i for i in range(25))
    cards = '''<template class="speaker-qa">
      <article data-qa-card id="common" data-keywords="repeat 다시 질문">
        <h3 data-qa-question>질문을 다시 듣기</h3>
        <p data-qa-question-en>Could you repeat the question?</p>
        <p data-qa-answer>PRIVATE_QA_COMMON Please repeat the question.</p>
        <p data-qa-note>질문을 확인한 뒤 답합니다.</p>
      </article>
      <article data-qa-card id="sign" data-pages="1" data-keywords="minus 부호 symbol">
        <h3 data-qa-question>부호 의미</h3>
        <p data-qa-question-en>Why is there a minus sign?</p>
        <p data-qa-answer>PRIVATE_QA_SIGN This is an example answer about a symbol.</p>
        <p data-qa-note>어느 기호를 말하는지 확인합니다.</p>
      </article>
      <article data-qa-card id="test" data-pages="2, 2, 0, -1, 999, invalid" data-keywords="conditions 조건">
        <h3 data-qa-question>실험 조건</h3>
        <p data-qa-question-en>What were the test conditions?</p>
        <p data-qa-answer>PRIVATE_QA_TEST This example used a fixed setup.</p>
        <p data-qa-note>실험 설명 카드입니다.</p>
      </article>
      <article data-qa-card id="literal" data-pages="1,2" data-keywords="literal markup">
        <h3 data-qa-question>문자 그대로 표시</h3>
        <p data-qa-question-en>How is plain text shown?</p>
        <p data-qa-answer>PRIVATE_QA_LITERAL LITERAL_TEXT<script>window.qaInjected=2</script><style>.unwanted{display:block}</style></p>
        <p data-qa-note>메모 &lt;b&gt;그대로&lt;/b&gt;</p>
      </article>
    </template>'''.replace('LITERAL_TEXT', html.escape(LITERAL) + ' ' +
        ' '.join('Reading practice sentence %d keeps this answer long enough to test scrolling.' % i for i in range(36))) if with_qa else ''
    direct = '''<aside class="speaker-qa"><article data-qa-card id="direct" data-pages="3">
      <h3 data-qa-question>마지막 질문</h3><p data-qa-question-en>Any final comments?</p>
      <p data-qa-answer>PRIVATE_QA_DIRECT Thank you for the question.</p>
    </article></aside>''' if with_qa else ''
    document = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
    <title>Private Q&A test</title><link rel="stylesheet" href="deck.css">
    <style>@page{size:1920px 1080px;margin:0}html,body{margin:0}deck-stage{display:block}
    .slide{width:1920px;height:1080px;box-sizing:border-box;overflow:hidden;break-after:page}
    .slide:last-child{break-after:auto}h1{font-size:100px}</style></head><body><deck-stage>
    <section class="slide" data-label="First"><h1>Public slide one</h1><aside class="speaker-notes" hidden>LONG_NOTES</aside></section>
    <section class="slide" data-label="Second"><h1>Public slide two</h1><aside class="speaker-notes" hidden><p>The second script stays independent of the selected answer.</p></aside></section>
    <section class="slide" data-label="Third"><h1>Public slide three</h1>DIRECT_QA<aside class="speaker-notes" hidden><p>Final script.</p></aside></section>
    </deck-stage>QA_CARDS<script src="present.js"></script></body></html>'''
    document = document.replace('LONG_NOTES', paragraphs).replace('DIRECT_QA', direct).replace('QA_CARDS', cards)
    path = folder / 'deck.html'
    path.write_text(document)
    return path


def load(path):
    c = ChromeSession(width=1280, height=850)
    c.call('Network.emulateNetworkConditions', dict(offline=True, latency=0, downloadThroughput=0, uploadThroughput=0))
    c.call('Page.navigate', {'url': path.as_uri()})
    wait_for(c, 'document.readyState==="complete" && !!window.SUVPresent')
    return c


def open_notes(c, url):
    source = next(t for t in targets(c) if t['url'] == url)['id']
    c.key('n')
    deadline = time.monotonic() + 8
    while len(targets(c)) < 2 and time.monotonic() < deadline:
        time.sleep(.05)
    p = attach(c, next(t for t in targets(c) if t['id'] != source))
    wait_for(p, '!!document.querySelector("#qa-tab")')
    return p


def search(p, text):
    click(p, '#qa-search')
    # Select text using DOM only; the edit itself uses the browser's input path.
    evaluate(p, 'document.querySelector("#qa-search").select()')
    p.call('Input.insertText', {'text': text})
    if not text:
        # insertText('') is not guaranteed to delete a selected range in every CDP version.
        evaluate(p, 'document.querySelector("#qa-search").value="";document.querySelector("#qa-search").dispatchEvent(new Event("input",{bubbles:true}))')


def pick(p, text):
    selector = evaluate(p, '''(()=>{const a=[...document.querySelectorAll('#qa-list button')],i=a.findIndex(b=>b.textContent.includes(%s));return i<0?null:'#qa-list button[data-test-index="'+i+'"]'})()''' % json.dumps(text))
    assert selector, 'Missing Q&A result ' + text
    evaluate(p, '[...document.querySelectorAll("#qa-list button")].forEach((b,i)=>b.dataset.testIndex=String(i))')
    click(p, selector)


def list_text(p):
    return evaluate(p, '[...document.querySelectorAll("#qa-list button")].map(b=>b.textContent)')


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    checks = []
    def passed(message):
        checks.append(message)
        print('PASS ' + message, flush=True)

    with tempfile.TemporaryDirectory(prefix='suvlab-qa-fixture-') as temporary:
        fixture = make_fixture(Path(temporary) / 'with-cards')
        with load(fixture) as c:
            records = evaluate(c, 'SUVPresent.getQA()')
            assert len(records) == 5, records
            assert all(isinstance(x['pages'], list) for x in records)
            test = next(x for x in records if x['question'] == '실험 조건')
            assert test['pages'] == [2], test
            assert not evaluate(c, 'document.body.innerText.includes("PRIVATE_QA_")')
            assert evaluate(c, '[...document.querySelectorAll(".speaker-qa")].every(x=>getComputedStyle(x).display==="none")')
            assert not evaluate(c, '!!window.qaInjected')
            passed('Q&A source stays private; page metadata is normalized and inert source code does not execute')
            p = open_notes(c, fixture.as_uri())
            evaluate(p, 'document.querySelector("#notes").scrollTop=280')
            before_scroll = evaluate(p, 'document.querySelector("#notes").scrollTop')
            assert before_scroll >= 270
            click(p, '#qa-tab')
            assert evaluate(p, 'document.querySelector("#qa-tab").getAttribute("aria-selected")==="true"')
            assert len(list_text(p)) == 5
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            click(p, '#notes-tab')
            assert abs(evaluate(p, 'document.querySelector("#notes").scrollTop') - before_scroll) < 2
            click(p, '#qa-tab')
            passed('Script/Q&A tabs preserve the position in a long script')

            search(p, 'MINUS')
            wait_for(p, 'document.querySelectorAll("#qa-list button").length===1')
            assert '부호 의미' in list_text(p)[0]
            pick(p, '부호 의미')
            assert 'PRIVATE_QA_SIGN' in evaluate(p, 'document.querySelector("#qa-answer").textContent')
            assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            search(p, '실험')
            wait_for(p, 'document.querySelectorAll("#qa-list button").length===1')
            pick(p, '실험 조건')
            assert 'PRIVATE_QA_TEST' in evaluate(p, 'document.querySelector("#qa-answer").textContent')
            search(p, 'fixed setup')
            wait_for(p, 'document.querySelectorAll("#qa-list button").length===1')
            passed('Korean questions, English keywords and answer text can be searched without changing the audience slide')

            evaluate(c, 'window.qaMedia=[];document.addEventListener("suv:media",e=>qaMedia.push(e.detail.action))')
            for key in ('q', 'p', 'r', 'ArrowRight', 'Home', 'End'):
                p.key(key)
            assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            assert evaluate(c, 'qaMedia') == []
            assert evaluate(p, 'document.querySelector("#qa-tab").getAttribute("aria-selected")==="true"')
            assert evaluate(p, 'document.activeElement.id') == 'qa-search'
            search(p, '')
            evaluate(p, 'document.querySelector("#qa-list button").focus()')
            for key in ('ArrowRight', 'ArrowDown', 'Home', 'End'):
                p.key(key)
            assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            passed('Search typing and question-list navigation do not trigger slide or media shortcuts')

            pick(p, '실험 조건')
            selected = evaluate(p, 'document.querySelector("#qa-answer").textContent')
            click(p, '#qa-current-only')
            shown = list_text(p)
            assert len(shown) == 3, shown
            assert not any('실험 조건' in x for x in shown)
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == selected
            evaluate(c, 'SUVPresent.show(1)')
            wait_for(p, 'document.querySelector("#jump").value==="2"')
            shown = list_text(p)
            assert len(shown) == 3 and any('실험 조건' in x for x in shown), shown
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == selected
            passed('Current-slide filtering includes common cards and preserves a selected answer while the slide changes')

            search(p, 'not-a-matching-question')
            wait_for(p, 'document.querySelectorAll("#qa-list button").length===0')
            assert evaluate(p, 'document.querySelector("#qa-count").textContent').strip()
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == selected
            search(p, '')
            pick(p, '문자 그대로 표시')
            answer = evaluate(p, 'document.querySelector("#qa-answer").textContent')
            assert LITERAL in answer, answer
            assert 'window.qaInjected=2' not in answer
            assert not evaluate(p, '!!document.querySelector("#qa-answer img,#qa-answer script,#qa-answer style,#qa-note b") || !!window.qaInjected')
            assert not evaluate(c, '!!window.qaInjected')
            passed('Empty search results retain the chosen answer; markup-like answer and note text never becomes executable HTML')

            wait_for(p, '!!document.querySelector("#next-preview").contentDocument?.querySelector(".slide")')
            for frame in ('current-preview', 'next-preview'):
                assert evaluate(p, '''(()=>{const d=document.getElementById(%s).contentDocument;return !d.querySelector('.speaker-qa,[data-speaker-qa]')&&!d.documentElement.innerHTML.includes('PRIVATE_QA_')})()''' % json.dumps(frame))
            pdf = c.call('Page.printToPDF', {'printBackground': True, 'preferCSSPageSize': True, 'displayHeaderFooter': False})
            pdf_path = out / 'audience.pdf'
            pdf_path.write_bytes(base64.b64decode(pdf['data']))
            text = subprocess.check_output(['pdftotext', str(pdf_path), '-'], text=True)
            assert MARKER not in text and 'Public slide three' in text
            passed('Q&A content is absent from both slide previews and the audience PDF')

            before = evaluate(p, 'parseFloat(getComputedStyle(document.querySelector("#qa-answer")).fontSize)')
            click(p, '#font-larger')
            after = evaluate(p, 'parseFloat(getComputedStyle(document.querySelector("#qa-answer")).fontSize)')
            assert after > before, (before, after)
            evaluate(p, 'document.querySelector("#qa-tab").focus()')
            p.key('q')
            assert evaluate(p, 'document.querySelector("#notes-tab").getAttribute("aria-selected")==="true"')
            p.key('q')
            assert evaluate(p, 'document.querySelector("#qa-tab").getAttribute("aria-selected")==="true"')
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == answer
            p.screenshot(out / 'qa_1280.png')
            p.call('Emulation.setDeviceMetricsOverride', {'width': 800, 'height': 700, 'deviceScaleFactor': 1, 'mobile': False})
            p.width = 800; p.height = 700
            time.sleep(.1)
            assert evaluate(p, 'document.documentElement.scrollWidth<=innerWidth')
            bounds = evaluate(p, '''['qa-search','qa-answer'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return {id,left:r.left,right:r.right,top:r.top,bottom:r.bottom}})''')
            assert all(b['left'] >= 0 and b['right'] <= 801 and b['top'] >= 0 for b in bounds), bounds
            p.screenshot(out / 'qa_800.png')
            passed('Q switches tabs outside typing; answer text scales and remains usable in a compact presenter window')
            evaluate(p, 'document.querySelector("#qa-answer-panel").focus()')
            p.key('End')
            wait_for(p, '(()=>{const e=document.querySelector("#qa-answer-panel");return e.scrollTop>0 && e.scrollTop+e.clientHeight>=e.scrollHeight-2})()')
            assert evaluate(c, 'SUVPresent.currentIndex()') == 1
            assert evaluate(p, '(()=>{const a=document.querySelector("#qa-answer-panel").getBoundingClientRect(),n=document.querySelector("#qa-note").getBoundingClientRect();return n.top>=a.top && n.bottom<=a.bottom})()')
            p.screenshot(out / 'qa_800_scrolled.png')
            p.key('Escape')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert evaluate(p, 'document.querySelector("#qa-tab").getAttribute("aria-selected")==="true"')
            p.key('Escape')
            assert evaluate(p, 'document.querySelector("#notes-tab").getAttribute("aria-selected")==="true"')
            passed('A long answer and its final note can be scrolled without moving the audience; Escape returns through the question overview to the script')
            errors = [e for e in c.events + p.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not errors, errors
            p.ws.close()

        fixture = make_fixture(Path(temporary) / 'no-cards', with_qa=False)
        with load(fixture) as c:
            assert evaluate(c, 'SUVPresent.getQA()') == []
            p = open_notes(c, fixture.as_uri())
            click(p, '#qa-tab')
            assert len(list_text(p)) == 0
            assert evaluate(p, 'document.querySelector("#qa-panel").innerText').strip()
            click(p, '#notes-tab')
            assert 'Script line 0' in evaluate(p, 'document.querySelector("#notes").textContent')
            p.ws.close()
            passed('Decks without Q&A cards show a useful empty state and retain normal speaker notes')

    report = {'result': 'PASS', 'passed': len(checks), 'checks': checks,
              'transport': 'offline file://', 'fixtures': 'Generic speaking-practice text only',
              'browserSecurity': 'Default local-file security; no allow-file-access-from-files or disable-web-security',
              'activationEvidence': 'Actual CDP mouse/key input; passive evaluations use userGesture:false'}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        run(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='suvlab-qa-test-') as temporary:
            run(Path(temporary))
