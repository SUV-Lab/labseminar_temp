#!/usr/bin/env python3
"""Keep the live audience preview visible while browsing or reading private Q&A."""
import argparse
import json
import tempfile
from pathlib import Path

from test_presenter import current_preview, screenshot_color_count
from test_presenter_displays import click, evaluate, wait_for
from test_presenter_qa import load, open_notes, search
from test_presenter_qa_browse import category, make_browse_fixture, overview, resize, visible_questions


def fixture(folder):
    path, _ = make_browse_fixture(folder)
    document = path.read_text()
    document = document.replace('<h1>Public slide one</h1>', '''<h1>Public slide one</h1>
      <canvas id="qa-live" width="1200" height="300"
        style="position:absolute;left:80px;top:330px;width:1200px;height:300px"></canvas>''', 1)
    script = '''<script>(function(){
      const canvas=document.querySelector('#qa-live'),ctx=canvas.getContext('2d');
      const state=window.qaLive={frames:0,playing:false};let pending=0;
      function draw(){ctx.fillStyle='white';ctx.fillRect(0,0,1200,300);
        ctx.fillStyle='#1d4ed8';ctx.fillRect(20+(state.frames*9)%900,50,200,200)}
      function pause(){state.playing=false;if(pending)SUVPresent.cancelAnimationFrame(pending);pending=0}
      function tick(){pending=0;if(!state.playing)return;state.frames++;draw();pending=SUVPresent.requestAnimationFrame(tick)}
      document.addEventListener('suv:media',e=>{if(e.detail.slide!==canvas.closest('.slide'))return;
        e.preventDefault();if(e.detail.action==='reset'){pause();state.frames=0;draw()}
        else if(state.playing)pause();else{state.playing=true;pending=SUVPresent.requestAnimationFrame(tick)}});
      document.addEventListener('suv:slidechange',e=>{if(e.detail.index!==0)pause()});
      document.addEventListener('suv:playbackvisibility',e=>{if(!e.detail.visible)pause()});draw();
    })();</script>'''
    path.write_text(document.replace('</body>', script + '</body>'))
    return path


def preview_geometry(p):
    return evaluate(p, '''(()=>{
      const pane=document.querySelector('.current-pane'),box=pane.querySelector('.preview-box');
      const frame=document.querySelector('#current-preview'),r=box.getBoundingClientRect(),f=frame.getBoundingClientRect();
      const top=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
      return {width:r.width,height:r.height,left:r.left,top:r.top,right:r.right,bottom:r.bottom,
        frameWidth:f.width,frameHeight:f.height,scale:new DOMMatrixReadOnly(getComputedStyle(frame).transform).a,
        visible:getComputedStyle(pane).display!=='none'&&pane.contains(top),
        inViewport:r.left>=0&&r.top>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1,
        horizontalOverflow:document.documentElement.scrollWidth>innerWidth};
    })()''')


def assert_preview(p):
    geometry = preview_geometry(p)
    assert geometry['visible'] and geometry['inViewport'], geometry
    assert geometry['width'] >= 150 and geometry['height'] >= 80, geometry
    assert geometry['scale'] > 0, geometry
    assert abs(geometry['frameWidth'] - geometry['width']) < 4, geometry
    assert abs(geometry['frameHeight'] - geometry['height']) < 4, geometry
    assert not geometry['horizontalOverflow'], geometry
    return geometry


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    checks, geometry, pixels = [], {}, {}

    def passed(message):
        checks.append(message)
        print('PASS ' + message, flush=True)

    with tempfile.TemporaryDirectory(prefix='qa-preview-fixture-') as tmp:
        path = fixture(Path(tmp))
        with load(path) as c:
            p = open_notes(c, path.as_uri())
            wait_for(p, current_preview('!!d?.querySelector("#qa-live")'))
            evaluate(p, 'window.qaPreviewDocument=document.querySelector("#current-preview").contentDocument')
            initial_geometry = assert_preview(p)
            click(p, '#qa-tab')
            for width, height in [(1280, 850), (800, 700), (781, 963), (560, 700)]:
                resize(p, width, height)
                overview(p)
                evaluate(p, 'document.querySelector("#qa-list").scrollTop=0')
                browse = assert_preview(p)
                browse['visibleQuestions'] = len(visible_questions(p))
                p.screenshot(out / f'browse_{width}x{height}.png')
                click(p, '#qa-list button')
                detail = assert_preview(p)
                assert not evaluate(p, 'document.querySelector("#qa-answer-panel").hidden')
                assert evaluate(c, 'SUVPresent.currentIndex()') == 0
                p.screenshot(out / f'detail_{width}x{height}.png')
                assert evaluate(p, 'qaPreviewDocument===document.querySelector("#current-preview").contentDocument')
                geometry[f'{width}x{height}'] = dict(browse=browse, detail=detail)
            passed('Current audience preview stays visible, correctly scaled and unobscured during browse/detail at four window sizes')

            resize(p, 1280, 850)
            overview(p)
            category(p, '연구 배경')
            search(p, 'topic-1')
            assert_preview(p)
            assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            search(p, '')
            category(p, '')
            assert_preview(p)
            passed('Search and category filters retain the live preview without changing the audience slide')

            source = 'document.querySelector("#qa-live").toDataURL()'
            mirrored = current_preview('d.querySelector("#qa-live").toDataURL()')
            for mode in ('browse', 'detail'):
                if mode == 'detail':
                    click(p, '#qa-list button')
                before = evaluate(c, source)
                evaluate(p, 'document.querySelector("#qa-tab").focus()')
                p.key('p')
                wait_for(c, 'qaLive.playing')
                wait_for(c, source + '!==' + json.dumps(before))
                wait_for(p, mirrored + '!==' + json.dumps(before))
                p.key('p')
                wait_for(c, '!qaLive.playing')
                paused = evaluate(c, source)
                wait_for(p, mirrored + '===' + json.dumps(paused))
                assert_preview(p)
                pixels[mode] = screenshot_color_count(p, '#qa-live', out / f'live_{mode}.png', 2)
                assert pixels[mode] > 20, pixels
                assert evaluate(p, 'qaPreviewDocument===document.querySelector("#current-preview").contentDocument')
                assert evaluate(c, 'SUVPresent.currentIndex()') == 0
            passed('Animated canvas frames reach the visible preview in Q&A overview and answer modes without recreating the iframe')

            click(p, '#notes-tab')
            restored = assert_preview(p)
            assert abs(initial_geometry['width'] - restored['width']) < 2
            assert abs(initial_geometry['height'] - restored['height']) < 2
            assert evaluate(p, 'qaPreviewDocument===document.querySelector("#current-preview").contentDocument')
            assert not [e for e in c.events+p.events if e.get('method') == 'Runtime.exceptionThrown']
            p.screenshot(out / 'restored_notes.png')
            p.ws.close()
            passed('Returning to the script restores the original preview dimensions and retains the same live document')

    report = dict(result='PASS', passed=len(checks), checks=checks, geometry=geometry,
        visibleBluePixels=pixels, transport='offline file://', browser='Headless Chrome',
        fixture='Generic46-card Q&A with a blue canvas animation',
        browserSecurity='Default local-file security; no relaxed origin or file-access flags')
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        run(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='qa-preview-result-') as tmp:
            run(Path(tmp))
