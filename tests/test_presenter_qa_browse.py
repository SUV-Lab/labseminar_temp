#!/usr/bin/env python3
"""Exercise fast Q&A browsing with 46 generic cards in real offline Chromium."""
import argparse
import html
import json
import tempfile
from pathlib import Path

from test_presenter_displays import click, evaluate, wait_for
from test_presenter_qa import load, make_fixture, open_notes, search


CATEGORIES = ['연구 배경', '자료와 설명', '비교와 통계', '검증 범위', '발표 조작', '<b>질문 확인</b>']
QUESTIONS = [
    '이 발표에서 다루는 문제의 범위는 어디까지인가요?',
    '비교 자료를 선택한 이유는 무엇인가요?',
    '그림의 설명과 측정 결과는 어떻게 구분하나요?',
    '평균값만으로 모든 경우를 설명할 수 있나요?',
    '추가로 확인해야 할 조건은 무엇인가요?',
    '다른 사례에도 같은 결론을 적용할 수 있나요?',
    '설명에 사용한 예시가 같은 자료인가요?',
    '질문에서 어떤 부분을 말씀하시는 건가요?',
]


def make_browse_fixture(folder):
    path = make_fixture(folder, with_qa=False)
    document = path.read_text()
    cards, records = [], []
    for index in range(46):
        category = '__proto__' if index == 45 else CATEGORIES[index // 8]
        pages = [] if index % 7 == 0 else [1 if index % 2 else 2]
        question = f'{index + 1:02}. ' + QUESTIONS[index % len(QUESTIONS)]
        answer = f'PRIVATE_BROWSE_{index + 1:02} This is prepared answer number {index + 1}. It describes the scope of this example.'
        records.append(dict(category=category, pages=pages, question=question, answer=answer))
        cards.append('<article data-qa-card data-category="' + html.escape(category, quote=True) +
            '" data-pages="' + ','.join(map(str, pages)) + '" data-keywords="example topic-' + str(index + 1) + '">' +
            '<h3 data-qa-question>' + question + '</h3><p data-qa-question-en>What does example ' + str(index + 1) +
            ' show?</p><p data-qa-answer>' + answer + '</p><p data-qa-note>이 카드는 발표 연습용 예시입니다.</p></article>')
    document = document.replace('</deck-stage>', '</deck-stage><template class="speaker-qa">' + ''.join(cards) + '</template>')
    path.write_text(document)
    return path, records


def resize(p, width, height):
    p.call('Emulation.setDeviceMetricsOverride', dict(width=width, height=height, deviceScaleFactor=1, mobile=False))
    p.width, p.height = width, height
    evaluate(p, 'new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')


def overview(p):
    if evaluate(p, '!document.querySelector("#qa-back").hidden'):
        click(p, '#qa-back')
    wait_for(p, 'document.querySelector("#qa-answer-panel").hidden')


def visible_questions(p):
    return evaluate(p, '''(()=>{
      const list=document.querySelector('#qa-list'),r=list.getBoundingClientRect();
      return [...list.querySelectorAll('button')].filter(b=>{
        const q=b.getBoundingClientRect();
        return q.width>0 && q.height>0 && q.left>=r.left-1 && q.right<=r.right+1 &&
          q.top>=r.top-1 && q.bottom<=r.bottom+1;
      }).map(b=>({id:b.dataset.qaId,font:parseFloat(getComputedStyle(b).fontSize)}));
    })()''')


def pointer_click_visible(p, selector):
    point = evaluate(p, '''(()=>{const e=document.querySelector(%s),r=e.getBoundingClientRect();
      return {x:r.left+r.width/2,y:r.top+r.height/2}})()''' % json.dumps(selector))
    p.call('Input.dispatchMouseEvent', dict(type='mousePressed', button='left', clickCount=1, **point))
    p.call('Input.dispatchMouseEvent', dict(type='mouseReleased', button='left', clickCount=1, **point))


def category(p, label):
    selector = '#qa-categories button[data-qa-category=' + json.dumps(label, ensure_ascii=False) + ']'
    click(p, selector)


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    checks, counts = [], {}

    def passed(message):
        checks.append(message)
        print('PASS ' + message, flush=True)

    with tempfile.TemporaryDirectory(prefix='suvlab-qa-browse-') as temporary:
        fixture, records = make_browse_fixture(Path(temporary))
        with load(fixture) as c:
            source_cards = evaluate(c, 'SUVPresent.getQA()')
            assert [x['category'] for x in source_cards] == [x['category'] for x in records]
            assert not evaluate(c, 'document.body.innerText.includes("PRIVATE_BROWSE_")')
            p = open_notes(c, fixture.as_uri())
            evaluate(p, 'document.querySelector("#notes").scrollTop=300')
            notes_scroll = evaluate(p, 'document.querySelector("#notes").scrollTop')
            assert notes_scroll >= 299
            click(p, '#qa-tab')
            wait_for(p, 'document.querySelector("main").classList.contains("qa-mode")')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == 46
            assert not evaluate(p, '!!document.querySelector("#qa-categories b,#qa-list h3 b")')
            assert '<b>질문 확인</b>' in evaluate(p, 'document.querySelector("#qa-categories").textContent')
            passed('Q&A opens a full-work-area question overview; all 46 categories/questions are plain text and stay private')
            category(p, '__proto__')
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == 1
            category(p, '')

            for width, height, minimum in [(1280, 850, 16), (800, 700, 12), (560, 700, 5)]:
                resize(p, width, height)
                evaluate(p, 'document.querySelector("#qa-list").scrollTop=0')
                shown = visible_questions(p)
                counts[f'{width}x{height}'] = len(shown)
                p.screenshot(out / f'overview_{width}.png')
                assert len(shown) >= minimum, (width, height, len(shown), minimum)
                assert all(x['font'] >= 14 for x in shown), shown
                assert evaluate(p, 'document.documentElement.scrollWidth<=innerWidth')
                assert evaluate(p, 'document.querySelector("#qa-list").clientHeight>=200')
            passed('Readable overview exposes at least 16 questions on a laptop, 12 in a compact window and 5 on a narrow window')

            resize(p, 1280, 850)
            evaluate(p, 'window.qaList=document.querySelector("#qa-list");qaList.scrollTop=(qaList.scrollHeight-qaList.clientHeight)*0.6')
            shown = visible_questions(p)
            assert shown
            selected_id = shown[len(shown) // 2]['id']
            before = evaluate(p, 'document.querySelector("#qa-list").scrollTop')
            assert before > 0
            pointer_click_visible(p, '#qa-list button[data-qa-id=' + json.dumps(selected_id) + ']')
            wait_for(p, '!document.querySelector("#qa-answer-panel").hidden')
            selected_answer = evaluate(p, 'document.querySelector("#qa-answer").textContent')
            assert 'PRIVATE_BROWSE_' in selected_answer
            assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            bounds = evaluate(p, '''(()=>{const l=document.querySelector('#qa-list').getBoundingClientRect(),a=document.querySelector('#qa-answer-panel').getBoundingClientRect();return {list:l.width,answer:a.width,apart:l.right<=a.left+2}})()''')
            assert bounds['list'] > 250 and bounds['answer'] > 350 and bounds['apart'], bounds
            p.screenshot(out / 'detail_1280.png')
            click(p, '#qa-back')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert abs(evaluate(p, 'document.querySelector("#qa-list").scrollTop') - before) <= 2
            click(p, '#notes-tab')
            click(p, '#qa-tab')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert abs(evaluate(p, 'document.querySelector("#qa-list").scrollTop') - before) <= 2
            passed('Selecting opens a full-height list/answer split; back and tab reopening restore overview scroll without moving the audience')

            category(p, CATEGORIES[1])
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == 8
            click(p, '#qa-current-only')
            expected = sum(x['category'] == CATEGORIES[1] and (not x['pages'] or 1 in x['pages']) for x in records)
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == expected
            first_id = evaluate(p, 'document.querySelector("#qa-list button").dataset.qaId')
            click(p, '#qa-list button[data-qa-id=' + json.dumps(first_id) + ']')
            selected_answer = evaluate(p, 'document.querySelector("#qa-answer").textContent')
            evaluate(c, 'SUVPresent.show(1)')
            expected = sum(x['category'] == CATEGORIES[1] and (not x['pages'] or 2 in x['pages']) for x in records)
            wait_for(p, f'document.querySelectorAll("#qa-list button").length==={expected}')
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == selected_answer
            assert not evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            search(p, 'not-found')
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == 0
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert evaluate(p, 'document.querySelector("#qa-answer").textContent') == selected_answer
            assert evaluate(p, '!document.querySelector("#qa-empty").hidden')
            search(p, '')
            category(p, '')
            click(p, '#qa-current-only')
            assert evaluate(p, 'document.querySelectorAll("#qa-list button").length') == 46
            passed('Category, current-page and search filters intersect correctly; a chosen answer survives slide/filter changes')

            evaluate(c, 'window.qaMedia=[];document.addEventListener("suv:media",e=>qaMedia.push(e.detail.action))')
            click(p, '#qa-search')
            for key in ('q', 'p', 'r', 'ArrowRight', 'Home', 'End'):
                p.key(key)
            assert evaluate(c, 'qaMedia') == []
            assert evaluate(c, 'SUVPresent.currentIndex()') == 1
            search(p, '')
            evaluate(p, 'document.querySelector("#qa-categories button").focus()')
            for key in ('ArrowRight', 'ArrowDown', 'PageDown', 'Home', 'End'):
                p.key(key)
            assert evaluate(c, 'SUVPresent.currentIndex()') == 1
            evaluate(p, 'document.querySelector("#qa-list button").focus()')
            for key in ('ArrowRight', 'ArrowDown', 'Home', 'End'):
                p.key(key)
            assert evaluate(c, 'SUVPresent.currentIndex()') == 1
            p.key('Enter')
            wait_for(p, '!document.querySelector("#qa-answer-panel").hidden')
            passed('Search typing, category navigation and question keyboard selection never send slide or media shortcuts')

            resize(p, 800, 700)
            assert evaluate(p, 'document.querySelector("#qa-list").getBoundingClientRect().width===0')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").getBoundingClientRect().width>700')
            assert evaluate(p, 'document.documentElement.scrollWidth<=innerWidth')
            p.screenshot(out / 'detail_800.png')
            p.key('Escape')
            assert evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
            assert evaluate(p, 'document.querySelector("#qa-tab").getAttribute("aria-selected")==="true"')
            assert evaluate(c, 'SUVPresent.currentIndex()') == 1
            p.key('Escape')
            assert evaluate(p, 'document.querySelector("#notes-tab").getAttribute("aria-selected")==="true"')
            assert not evaluate(p, 'document.querySelector("main").classList.contains("qa-mode")')
            resize(p, 1280, 850)
            evaluate(c, 'SUVPresent.show(0)')
            wait_for(p, 'document.querySelector("#jump").value==="1"')
            assert abs(evaluate(p, 'document.querySelector("#notes").scrollTop') - notes_scroll) <= 2
            passed('Compact detail gives the answer the full width; Escape returns to overview then notes and restores the earlier script position')
            errors = [e for e in c.events + p.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not errors, errors
            p.ws.close()

    report = dict(result='PASS', passed=len(checks), checks=checks, fullyVisibleQuestions=counts,
        transport='offline file://', fixture='46 generic presentation-practice cards',
        browserSecurity='Default local-file security', activationEvidence='Actual CDP mouse/key input; passive evaluations use userGesture:false')
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        run(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='suvlab-qa-browse-report-') as folder:
            run(Path(folder))
