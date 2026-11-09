#!/usr/bin/env python3
"""Laser pointer and media control shared between the audience and presenter windows.

Audience mouse -> dot on the presenter's current preview.
Presenter hover on the preview -> dot on the audience slide.
Presenter click on a video in the preview -> the audience video plays/pauses.
"""
import argparse
import json
import tempfile
from pathlib import Path

from test_presenter_displays import evaluate, wait_for
from test_presenter_qa import load, make_fixture, open_notes

DOT = 'document.querySelector("#laser-dot")'


def move(c, fx, fy):
    """Move the audience mouse to a fraction of the current slide (may be outside 0..1)."""
    point = evaluate(c, '''(()=>{const r=document.querySelector(".slide.current").getBoundingClientRect();
      return {x:r.left+r.width*%s,y:r.top+r.height*%s}})()''' % (fx, fy))
    c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **point})


VIDEO = '''<video id="v" muted playsinline data-noautoplay
      style="position:absolute;left:960px;top:540px;width:640px;height:360px"></video>'''
# A canvas stream stands in for a media file, so the fixture stays offline and tiny.
STREAM = '''<script>(function(){const c=document.createElement('canvas');c.width=64;c.height=36;
  const g=c.getContext('2d');let n=0;setInterval(()=>{g.fillStyle=n++%2?'#1d4ed8':'#dc2626';g.fillRect(0,0,64,36)},50);
  document.querySelector('#v').srcObject=c.captureStream(20);})();</script>'''


def add_video(path):
    doc = path.read_text()
    doc = doc.replace('<h1>Public slide one</h1>', '<h1>Public slide one</h1>' + VIDEO, 1)
    path.write_text(doc.replace('</body>', STREAM + '</body>'))


def hover_preview(p, fx, fy, kind='mouseMoved'):
    """Mouse event on the presenter's current preview at a fraction of the slide."""
    point = evaluate(p, '''(()=>{const r=document.querySelector("#current-preview").parentNode.getBoundingClientRect();
      return {x:r.left+r.width*%s,y:r.top+r.height*%s}})()''' % (fx, fy))
    if kind == 'click':
        for t in ('mousePressed', 'mouseReleased'):
            p.call('Input.dispatchMouseEvent', {'type': t, 'button': 'left', 'clickCount': 1, **point})
    else:
        p.call('Input.dispatchMouseEvent', {'type': kind, **point})


def laser_fraction(c):
    return evaluate(c, '''(()=>{const d=document.querySelector("#suv-laser");if(!d||d.hidden)return null;
      const b=document.querySelector(".slide.current").getBoundingClientRect(),r=d.getBoundingClientRect();
      return {x:(r.left+r.width/2-b.left)/b.width,y:(r.top+r.height/2-b.top)/b.height}})()''')


def dot_fraction(p):
    return evaluate(p, '''(()=>{const d=%s,b=d.parentNode.getBoundingClientRect(),r=d.getBoundingClientRect();
      return d.hidden?null:{x:(r.left+r.width/2-b.left)/b.width,y:(r.top+r.height/2-b.top)/b.height}})()''' % DOT)


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix='laser-fixture-') as tmp:
        path = make_fixture(Path(tmp), with_qa=False)
        add_video(path)
        with load(path) as c:
            c.key('f')
            wait_for(c, 'document.body.classList.contains("presenting")')
            p = open_notes(c, path.as_uri())
            wait_for(p, DOT + '.hidden')

            cursor = evaluate(c, 'getComputedStyle(document.querySelector(".slide.current h1")).cursor')
            assert cursor.startswith('url("data:image/svg+xml'), cursor
            checks.append('Audience cursor is the laser dot while presenting')

            for fx, fy in [(.25, .4), (.9, .3)]:
                move(c, fx, fy)
                wait_for(p, '!%s.hidden' % DOT)
                wait_for(p, 'Math.abs(parseFloat(%s.style.left)-%s)<0.5' % (DOT, fx * 100))
                got = dot_fraction(p)
                assert abs(got['x'] - fx) < .02 and abs(got['y'] - fy) < .02, (fx, fy, got)
            p.screenshot(out / 'laser_dot.png')
            checks.append('Presenter preview dot follows the audience mouse position')

            move(c, .5, -.05)
            wait_for(p, DOT + '.hidden')
            checks.append('Dot hides when the mouse leaves the slide')

            move(c, .4, .3)
            wait_for(p, '!%s.hidden' % DOT)
            c.key('ArrowRight')
            wait_for(c, 'SUVPresent.currentIndex()===1')
            assert not evaluate(p, DOT + '.hidden'), 'dot should survive a slide change'
            c.key('b')
            wait_for(p, DOT + '.hidden')
            move(c, .4, .4)
            assert evaluate(p, DOT + '.hidden'), 'no dot while the audience screen is blank'
            c.key('b')
            move(c, .45, .45)
            wait_for(p, '!%s.hidden' % DOT)
            checks.append('Dot survives slide changes and hides while the audience screen is blank')

            c.key('ArrowLeft')
            wait_for(c, 'SUVPresent.currentIndex()===0')
            for fx, fy in [(.3, .3), (.2, .8)]:
                hover_preview(p, fx, fy)
                wait_for(c, '!!document.querySelector("#suv-laser") && !document.querySelector("#suv-laser").hidden')
                wait_for(c, '''(()=>{const d=document.querySelector("#suv-laser"),b=document.querySelector(".slide.current").getBoundingClientRect();
                  return Math.abs(parseFloat(d.style.left)-(b.left+b.width*%s))<2})()''' % fx)
                got = laser_fraction(c)
                assert abs(got['x'] - fx) < .02 and abs(got['y'] - fy) < .02, (fx, fy, got)
                assert not evaluate(p, DOT + '.hidden'), 'presenter sees where the audience laser is'
            c.screenshot(out / 'audience_laser.png')
            hover_preview(p, 1.2, .5)  # leave the preview box
            wait_for(c, 'document.querySelector("#suv-laser").hidden')
            wait_for(p, DOT + '.hidden')
            checks.append('Pointing at the presenter preview shows the laser on the audience slide and hides it on leave')

            hover_preview(p, .5, .5)
            wait_for(c, '!document.querySelector("#suv-laser").hidden')
            for selector in ('#next-preview', '#notes'):  # anywhere else in the presenter window
                point = evaluate(p, '''(()=>{const r=document.querySelector(%s).getBoundingClientRect();
                  return {x:r.left+r.width/2,y:r.top+r.height/2}})()''' % json.dumps(selector))
                p.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **point})
                wait_for(c, 'document.querySelector("#suv-laser").hidden')
            checks.append('Only the current-slide preview points; the next preview and notes do not')

            HOT = 'document.querySelector(".video-hotspot")'
            wait_for(p, '!!' + HOT)
            box = evaluate(p, '''(()=>{const b=%s.getBoundingClientRect(),r=%s.parentNode.getBoundingClientRect();
              return {x:(b.left-r.left)/r.width,y:(b.top-r.top)/r.height,w:b.width/r.width,h:b.height/r.height,
                label:%s.getAttribute("aria-label"),visible:getComputedStyle(%s.firstChild).display!=="none"}})()''' % (HOT, HOT, HOT, HOT))
            want = dict(x=960/1920, y=540/1080, w=640/1920, h=360/1080)
            assert all(abs(box[k] - want[k]) < .01 for k in want), box
            assert box['visible'] and box['label'] == '청중 화면 동영상 재생', box
            p.screenshot(out / 'video_button.png')
            assert evaluate(c, 'document.querySelector("#v").paused')
            hover_preview(p, .75, .8, 'click')
            wait_for(c, '!document.querySelector("#v").paused')
            wait_for(p, HOT + '.getAttribute("aria-label")==="청중 화면 동영상 일시정지"')
            p.screenshot(out / 'video_button_playing.png')
            hover_preview(p, .75, .8, 'click')
            wait_for(c, 'document.querySelector("#v").paused')
            wait_for(p, HOT + '.getAttribute("aria-label")==="청중 화면 동영상 재생"')
            evaluate(c, 'document.querySelector("#v").play()')  # audience-side play shows up too
            wait_for(p, HOT + '.classList.contains("playing")')
            evaluate(c, 'document.querySelector("#v").pause()')
            c.key('ArrowRight')
            wait_for(p, '!' + HOT)
            c.key('ArrowLeft')
            wait_for(p, '!!' + HOT)
            checks.append('A visible play/pause button over the preview video controls the audience video, tracks its state and follows slide changes')

            hover_preview(p, .4, .4)
            wait_for(c, '!document.querySelector("#suv-laser").hidden')
            c.key('Escape')
            wait_for(c, '!document.body.classList.contains("presenting")')
            wait_for(p, DOT + '.hidden')
            assert evaluate(c, 'document.querySelector("#suv-laser").hidden')
            hover_preview(p, .5, .5)
            assert evaluate(c, 'document.querySelector("#suv-laser").hidden'), 'no laser outside a presentation'
            checks.append('Both dots hide when the presentation stops')

            errors = [e for e in c.events + p.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not errors, json.dumps(errors)[:500]
            p.ws.close()
    report = dict(result='PASS', checks=checks, transport='offline file://')
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
