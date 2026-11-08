#!/usr/bin/env python3
"""Headed regression for animation playback while the audience window is hidden.

Uses a separate Chrome profile and native window minimization. No background
throttling, visibility emulation, or browser-security bypass flags are used.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time

from chrome_driver import ChromeSession
from test_presenter import attach, screenshot_color_count, targets, wait_for


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    base = (ROOT / 'design').as_uri() + '/'
    return '''<!doctype html><meta charset="utf-8"><title>Presenter animation clock test</title>
<base href="''' + base + '''"><link rel="stylesheet" href="deck.css">
<style>body{margin:0}deck-stage{display:block}.slide{width:1920px;height:1080px}
canvas{display:block;width:1500px;height:420px}.body{padding:80px}</style>
<deck-stage>
<section class="slide"><h1 class="title">Start</h1><aside class="speaker-notes" hidden><p>Advance from the notes window.</p></aside></section>
<section class="slide"><h1 class="title">Playback from notes</h1><div class="body">
<canvas id="clock-canvas" width="1500" height="420"></canvas><p id="clock-label">0.00</p></div>
<aside class="speaker-notes" hidden><p>Keep this window focused while the animation plays.</p></aside></section>
<section class="slide"><h1 class="title">Finish</h1><aside class="speaker-notes" hidden><p>Animation is paused when leaving its slide.</p></aside></section>
</deck-stage><script src="present.js"></script><script>
(function(){
  const canvas=document.querySelector('#clock-canvas'),ctx=canvas.getContext('2d');
  const state=window.clockTest={elapsed:0,playing:false,frames:0,nativeFrames:0,timestamps:[],cancelledCalls:0};
  let pending=0,last=0;
  function draw(){ctx.fillStyle='white';ctx.fillRect(0,0,1500,420);ctx.fillStyle='#1d4ed8';ctx.beginPath();ctx.arc(80+(state.elapsed%5)*260,210,36,0,Math.PI*2);ctx.fill();document.querySelector('#clock-label').textContent=state.elapsed.toFixed(2)}
  function pause(){state.playing=false;if(pending)SUVPresent.cancelAnimationFrame(pending);pending=0}
  function tick(now){pending=0;if(!state.playing)return;state.elapsed+=Math.max(0,Math.min(.1,(now-last)/1000));last=now;state.frames++;state.timestamps.push(now);draw();pending=SUVPresent.requestAnimationFrame(tick)}
  function control(action){if(action==='reset'){pause();state.elapsed=0;draw();return}if(state.playing){pause();return}state.playing=true;last=performance.now();pending=SUVPresent.requestAnimationFrame(tick)}
  document.addEventListener('suv:media',event=>{if(event.detail.slide!==canvas.closest('.slide'))return;event.preventDefault();control(event.detail.action)});
  document.addEventListener('suv:slidechange',event=>{if(event.detail.index!==1)pause()});
  document.addEventListener('suv:playbackvisibility',event=>{if(!event.detail.visible)pause()});
  function nativeTick(){state.nativeFrames++;requestAnimationFrame(nativeTick)}requestAnimationFrame(nativeTick);
  draw();
})();
</script>'''


def window_id(page, target):
    return page.call('Browser.getWindowForTarget', {'targetId': target})['windowId']


def set_window(page, ident, state):
    page.call('Browser.setWindowBounds', {'windowId': ident, 'bounds': {'windowState': state}})


def measure(page, seconds=2):
    before = page.evaluate('({elapsed:clockTest.elapsed,frames:clockTest.frames,nativeFrames:clockTest.nativeFrames})')
    started = time.monotonic()
    time.sleep(seconds)
    after = page.evaluate('({elapsed:clockTest.elapsed,frames:clockTest.frames,nativeFrames:clockTest.nativeFrames})')
    wall = time.monotonic() - started
    return {'wallSeconds': round(wall, 3),
        'animationSeconds': round(after['elapsed']-before['elapsed'], 3),
        'sharedFrames': after['frames']-before['frames'],
        'nativeAudienceFrames': after['nativeFrames']-before['nativeFrames']}


def assert_running(sample):
    assert sample['animationSeconds'] > sample['wallSeconds']*.65, sample
    assert sample['animationSeconds'] < sample['wallSeconds']*1.3, sample
    assert sample['sharedFrames'] > 10, sample


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    if (out/'report.json').exists():
        (out/'report.json').unlink()
    checks, measurements = [], {}
    def passed(name):
        checks.append(name)
        print('PASS '+name, flush=True)
    with tempfile.TemporaryDirectory(prefix='suv-presenter-clock-') as temp:
        path=Path(temp)/'clock.html';path.write_text(fixture())
        with ChromeSession(width=1280,height=850,headless=False) as audience:
            audience.call('Network.emulateNetworkConditions',dict(offline=True,latency=0,downloadThroughput=0,uploadThroughput=0))
            audience.navigate(path.as_uri())
            assert audience.evaluate("typeof SUVPresent.requestAnimationFrame==='function' && typeof SUVPresent.cancelAnimationFrame==='function' && typeof SUVPresent.playbackVisible==='function'")
            source_id=targets(audience)[0]['id']
            source_window=window_id(audience,source_id)
            audience.key('n');wait_for(audience,'!!window.SUVPresenter')
            audience.evaluate('window.clockNotes=SUVPresent.openNotes();true')
            wait_for(audience,'!!clockNotes.document.querySelector("#notes")')
            note_target=next(t for t in targets(audience) if t['id']!=source_id)
            presenter=attach(audience,note_target)
            note_window=window_id(presenter,note_target['id'])
            presenter.call('Page.bringToFront')
            wait_for(presenter,'document.hasFocus() && !document.hidden')
            presenter.key('ArrowRight')
            wait_for(audience,'SUVPresent.currentIndex()===1')
            set_window(audience,source_window,'minimized')
            presenter.call('Page.bringToFront')
            wait_for(audience,'document.hidden && !document.hasFocus()')
            wait_for(presenter,'document.hasFocus() && !document.hidden')
            presenter.key('p')
            wait_for(audience,'clockTest.playing')
            measurements['notesFocusedAudienceHidden']=measure(audience)
            assert_running(measurements['notesFocusedAudienceHidden'])
            assert measurements['notesFocusedAudienceHidden']['nativeAudienceFrames']<=1,measurements
            assert audience.evaluate('document.hidden && !document.hasFocus() && SUVPresent.playbackVisible()')
            assert presenter.evaluate('document.hasFocus()')
            passed('Notes-only navigation and P advance animation while native audience RAF is suspended')

            presenter.key('p')
            wait_for(audience,'!clockTest.playing')
            paused=measure(audience,.35)
            assert paused['animationSeconds']==0 and paused['sharedFrames']==0,paused
            visible=screenshot_color_count(presenter,'#clock-canvas',out/'notes_focused_playback.png',2)
            assert visible>50,visible
            presenter.key('r');wait_for(audience,'clockTest.elapsed===0 && !clockTest.playing')
            wait_for(presenter,"document.querySelector('#current-preview').contentDocument.querySelector('#clock-label').textContent==='0.00'")
            assert presenter.evaluate('document.hasFocus()')
            passed('Pause/reset and visible canvas preview work without returning focus to the audience')

            audience.evaluate('let cancelled=SUVPresent.requestAnimationFrame(()=>clockTest.cancelledCalls++);SUVPresent.cancelAnimationFrame(cancelled)')
            time.sleep(.15)
            assert audience.evaluate('clockTest.cancelledCalls')==0
            passed('A canceled shared animation callback never fires')

            presenter.key('p');wait_for(audience,'clockTest.playing')
            set_window(audience,source_window,'normal');audience.call('Page.bringToFront')
            wait_for(audience,'!document.hidden && document.hasFocus()')
            set_window(presenter,note_window,'minimized')
            wait_for(presenter,'document.hidden')
            measurements['audienceFocusedPresenterHidden']=measure(audience)
            assert_running(measurements['audienceFocusedPresenterHidden'])
            assert measurements['audienceFocusedPresenterHidden']['nativeAudienceFrames']>10
            set_window(presenter,note_window,'normal');presenter.call('Page.bringToFront')
            wait_for(presenter,'document.hasFocus() && !document.hidden')
            set_window(audience,source_window,'minimized')
            wait_for(audience,'document.hidden')
            measurements['notesFocusedAgain']=measure(audience)
            assert_running(measurements['notesFocusedAgain'])
            assert measurements['notesFocusedAgain']['nativeAudienceFrames']<=1
            passed('Clock transfers between windows without stalled time or doubled playback speed')

            presenter.key('ArrowRight');wait_for(audience,'SUVPresent.currentIndex()===2 && !clockTest.playing')
            presenter.key('ArrowLeft');wait_for(audience,'SUVPresent.currentIndex()===1')
            presenter.key('r');presenter.key('p')
            measurements['notesNavigationResume']=measure(audience,1)
            assert_running(measurements['notesNavigationResume'])
            presenter.key('p')
            passed('Leaving and returning to the animation from notes remains controllable')

            # Closing notes transfers future work to a visible audience window.
            set_window(audience,source_window,'normal');audience.call('Page.bringToFront')
            wait_for(audience,'!document.hidden')
            audience.key('p');wait_for(audience,'clockTest.playing')
            presenter.call('Target.closeTarget',{'targetId':note_target['id']})
            presenter.ws.close()
            measurements['presenterClosed']=measure(audience,1)
            assert_running(measurements['presenterClosed'])
            audience.key('n');audience.evaluate('window.clockNotes=SUVPresent.openNotes();true')
            wait_for(audience,'!!clockNotes.document.querySelector("#notes")')
            new_target=next(t for t in targets(audience) if t['id']!=source_id)
            presenter=attach(audience,new_target);presenter.call('Page.bringToFront')
            wait_for(presenter,'document.hasFocus()')
            set_window(audience,source_window,'minimized');wait_for(audience,'document.hidden')
            measurements['presenterReopened']=measure(audience,1)
            assert_running(measurements['presenterReopened'])
            assert presenter.evaluate('document.hasFocus()')
            passed('Closing and reopening notes restores the correct animation driver')
            presenter.key('p')
            errors=[e for e in audience.events+presenter.events if e.get('method')=='Runtime.exceptionThrown']
            assert not errors,errors
            presenter.ws.close()
    report={'result':'PASS','passed':len(checks),'checks':checks,'measurements':measurements,
        'mode':'headed native Chrome windows; audience minimized while notes focused',
        'visibilityEmulated':False,'backgroundThrottlingDisabled':False,
        'browserSecurity':'default; no allow-file-access-from-files or disable-web-security',
        'transport':'offline file://','visiblePreviewBluePixels':visible}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.output.resolve()),ensure_ascii=False,indent=2))
