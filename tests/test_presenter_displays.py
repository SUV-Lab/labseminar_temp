#!/usr/bin/env python3
"""Multi-display setup checks in offline Chromium.

The success path uses Chromium's virtual screens and genuine fullscreen/window
APIs. Failure paths explicitly stub display APIs. Neither is physical HDMI proof.
No test evaluation grants user activation: controls receive actual mouse events.
"""
import argparse
import json
import tempfile
import time
from pathlib import Path

from chrome_driver import ChromeSession
from test_presenter import attach, targets

ROOT = Path(__file__).resolve().parents[1]
DECK = (ROOT / 'examples/presenter-notes.html').as_uri()


def evaluate(page, expression):
    result = page.call('Runtime.evaluate', {
        'expression': expression, 'awaitPromise': True,
        'returnByValue': True, 'userGesture': False,
    })
    if 'exceptionDetails' in result:
        raise RuntimeError(json.dumps(result['exceptionDetails']))
    return result.get('result', {}).get('value')


def wait_for(page, expression, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if evaluate(page, expression):
            return
        time.sleep(.04)
    raise AssertionError('Timed out: ' + expression)


def click(page, selector):
    point = evaluate(page, '''(()=>{
      const e=document.querySelector(%s);if(!e)throw new Error('Missing control');
      e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
      if(e.disabled||!r.width||!r.height)throw new Error('Control unavailable: '+%s);
      return {x:r.left+r.width/2,y:r.top+r.height/2};
    })()''' % (json.dumps(selector), json.dumps(selector)))
    page.call('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, **point})
    page.call('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, **point})


def select_label(page, selector, label):
    evaluate(page, '''(()=>{
      const e=document.querySelector(%s),o=[...e.options].find(o=>o.textContent.includes(%s));
      if(!o)throw new Error('Missing screen option');e.value=o.value;
      e.dispatchEvent(new Event('change',{bubbles:true}));
    })()''' % (json.dumps(selector), json.dumps(label)))


def open_setup(page):
    click(page, '#suv-display-setup')
    wait_for(page, 'document.querySelector("#suv-display-dialog").open')


def setup_ready(page):
    wait_for(page, '!document.querySelector("#suv-start-presentation").disabled')


MOCK = r'''(()=>{
  const mode=MODE;
  const primary={left:0,top:0,width:1440,height:900,availLeft:0,availTop:24,
    availWidth:1440,availHeight:876,isPrimary:true,isInternal:true,label:'Laptop'};
  const external={left:-1920,top:0,width:1920,height:1080,availLeft:-1920,availTop:0,
    availWidth:1920,availHeight:1040,isPrimary:false,isInternal:false,label:'Projector <safe>'};
  const details=new EventTarget();details.screens=mode==='single'?[primary]:[primary,external];
  details.currentScreen=primary;
  const state=window.__displayTest={mode,details,primary,external,requests:[],opens:[],
    moves:[],resizes:[],focuses:0,enumerations:0,alerts:[]};
  Object.defineProperty(window.screen,'isExtended',{configurable:true,get:()=>details.screens.length>1});
  if(mode==='mac-escape')Object.defineProperty(navigator,'platform',{configurable:true,value:'MacIntel'});
  Object.defineProperty(window,'getScreenDetails',{configurable:true,value:
    mode==='unsupported'?undefined:function(){
      state.enumerations++;
      if(mode==='denied')return Promise.reject(new DOMException('Permission denied','NotAllowedError'));
      if(mode==='deferred')return new Promise(resolve=>state.resolve=()=>resolve(details));
      return Promise.resolve(details);
    }});
  let fullscreen=null;
  Object.defineProperty(document,'fullscreenElement',{configurable:true,get:()=>fullscreen});
  Element.prototype.requestFullscreen=function(options){
    state.requests.push({screen:options?.screen?.label,navigationUI:options?.navigationUI,
      popupCount:state.opens.length,active:navigator.userActivation.isActive});
    if(mode==='reject')return Promise.reject(new DOMException('Fullscreen blocked','NotAllowedError'));
    fullscreen=this;
    if(mode!=='mismatch')details.currentScreen=options?.screen||primary;
    document.dispatchEvent(new Event('fullscreenchange'));
    details.dispatchEvent(new Event('currentscreenchange'));
    if(mode==='mac-escape')setTimeout(()=>document.exitFullscreen(),100);
    return Promise.resolve();
  };
  document.exitFullscreen=function(){fullscreen=null;document.dispatchEvent(new Event('fullscreenchange'));return Promise.resolve()};
  window.alert=message=>state.alerts.push(message);
  const originalOpen=window.open;
  window.open=function(...args){
    state.opens.push({features:args[2],fullscreen:!!fullscreen});
    if(mode==='blocked')return null;
    const popup=originalOpen.apply(this,args);state.popup=popup;
    if(popup){
      const focus=popup.focus.bind(popup);
      popup.focus=function(){state.focuses++;focus()};
      popup.moveTo=(...args)=>state.moves.push(args);
      popup.resizeTo=(...args)=>state.resizes.push(args);
      if(mode==='wrong-popup'){
        Object.defineProperty(popup,'screenX',{configurable:true,value:-1900});
        Object.defineProperty(popup,'outerWidth',{configurable:true,value:1000});
      }
      if(mode==='lost-fullscreen')document.exitFullscreen();
    }
    return popup;
  };
})();'''


def session(mode=None):
    c = ChromeSession(width=1280, height=850)
    c.call('Network.emulateNetworkConditions', dict(offline=True, latency=0, downloadThroughput=0, uploadThroughput=0))
    if mode:
        c.call('Page.addScriptToEvaluateOnNewDocument', {'source': MOCK.replace('MODE', json.dumps(mode))})
    c.call('Page.navigate', {'url': DECK})
    wait_for(c, 'location.href===' + json.dumps(DECK) + ' && document.readyState==="complete" && !!window.SUVPresent')
    return c


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    checks = []
    evidence = {}

    def passed(name):
        checks.append(name)
        print('PASS ' + name, flush=True)

    # A genuine Chrome ScreenDetailed target exercises activation and the
    # fullscreen/popup companion sequence that ordinary JS mocks cannot prove.
    with session() as c:
        evidence['browser'] = c.call('Browser.getVersion')['product']
        virtual = c.call('Emulation.addScreen', {
            'left': -1920, 'top': 0, 'width': 1920, 'height': 1080,
            'label': 'Virtual projector', 'isInternal': False,
        })['screenInfo']
        c.call('Browser.setPermission', {
            'permission': {'name': 'window-management'}, 'setting': 'granted', 'origin': 'file://',
        })
        source = next(t for t in targets(c) if t['url'] == DECK)['id']
        open_setup(c)
        setup_ready(c)
        select_label(c, '#suv-audience-screen', 'Virtual projector')
        evidence['screenOptions'] = evaluate(c, '[...document.querySelector("#suv-audience-screen").options].map(o=>o.textContent)')
        c.screenshot(out / 'display_setup_virtual.png')
        click(c, '#suv-start-presentation')
        wait_for(c, '!!document.fullscreenElement')
        deadline = time.monotonic() + 8
        while len(targets(c)) < 2 and time.monotonic() < deadline:
            time.sleep(.05)
        popup_target = next(t for t in targets(c) if t['id'] != source)
        p = attach(c, popup_target)
        wait_for(p, '!!document.querySelector("#notes")')
        time.sleep(.3)
        evidence['fullscreenScreen'] = evaluate(c, 'getScreenDetails().then(d=>({left:d.currentScreen.left,label:d.currentScreen.label,fullscreen:!!document.fullscreenElement}))')
        assert evidence['fullscreenScreen']['left'] == virtual['left'], evidence
        assert evidence['fullscreenScreen']['fullscreen'], evidence
        evidence['notesWindow'] = c.call('Browser.getWindowForTarget', {'targetId': popup_target['id']})['bounds']
        assert evidence['notesWindow']['left'] >= 0, evidence
        passed('Real Chromium virtual display receives fullscreen; notes open on the other screen without synthetic user activation')
        click(p, '#next')
        wait_for(c, 'SUVPresent.currentIndex()===1')
        wait_for(p, 'document.querySelector("#slide-count").textContent.includes("2")')
        assert evaluate(c, '!!document.fullscreenElement')
        passed('Presenter navigation stays synchronized while the audience remains fullscreen on a separate virtual screen')
        click(p, '#display-setup')
        wait_for(c, 'document.querySelector("#suv-display-dialog").open')
        setup_ready(c)
        c.key('Escape')
        wait_for(c, '!document.querySelector("#suv-display-dialog").open')
        assert evaluate(c, 'SUVPresent.currentIndex()===1 && document.body.classList.contains("presenting")')
        click(p, '#display-setup')
        wait_for(c, 'document.querySelector("#suv-display-dialog").open')
        setup_ready(c)
        select_label(c, '#suv-audience-screen', 'Virtual projector')
        click(c, '#suv-start-presentation')
        wait_for(c, '!!document.fullscreenElement')
        time.sleep(.3)
        assert len(targets(c)) == 2
        assert next(t for t in targets(c) if t['id'] != source)['id'] == popup_target['id']
        assert evaluate(c, '!!document.fullscreenElement && SUVPresent.currentIndex()===1')
        assert evaluate(p, 'getComputedStyle(document.body).visibility') == 'visible'
        click(p, '#next')
        wait_for(c, 'SUVPresent.currentIndex()===2')
        evaluate(c, 'window.displayMediaActions=[];document.addEventListener("suv:media",e=>displayMediaActions.push(e.detail.action))')
        p.key('p')
        p.key('r')
        assert evaluate(c, 'displayMediaActions') == ['toggle', 'reset']
        passed('Notes can reopen setup and reuse the same popup; Escape keeps the current slide and media controls still reach the source')
        p.ws.close()

    for mode, expected in [('unsupported', '확장'), ('denied', '허용'), ('single', '확장')]:
        with session(mode) as c:
            open_setup(c)
            wait_for(c, 'document.querySelector("#suv-display-status").textContent.length>10')
            assert evaluate(c, 'document.querySelector("#suv-start-presentation").disabled')
            body = evaluate(c, 'document.querySelector("#suv-display-dialog").innerText')
            assert expected in body, body
            assert len(targets(c)) == 1
            assert not evaluate(c, '!!document.fullscreenElement')
            click(c, '#suv-manual-notes')
            wait_for(c, '!!window.SUVPresenter')
            wait_for(c, '__displayTest.popup && !!__displayTest.popup.document.querySelector("#notes")')
            assert len(targets(c)) == 2
            passed(f'{mode}: explains manual display setup and opens ordinary notes without automatic placement')

    for mode in ('reject', 'mismatch', 'blocked'):
        with session(mode) as c:
            open_setup(c)
            setup_ready(c)
            click(c, '#suv-start-presentation')
            wait_for(c, 'document.querySelector("#suv-display-dialog").open && document.querySelector("#suv-display-status").textContent.length>10')
            state = evaluate(c, '({requests:__displayTest.requests,opens:__displayTest.opens,text:document.querySelector("#suv-display-status").textContent})')
            assert len(state['requests']) == 1, state
            assert state['requests'][0]['popupCount'] == 0, state
            assert state['requests'][0]['screen'] == 'Projector <safe>', state
            assert len(state['opens']) == (1 if mode == 'blocked' else 0), state
            assert len(targets(c)) == 1
            assert not evaluate(c, '!!document.fullscreenElement')
            assert 'F' in evaluate(c, 'document.querySelector("#suv-display-dialog").innerText')
            passed(f'{mode}: keeps recovery available and never opens notes before the selected fullscreen screen is verified')

    for mode in ('wrong-popup', 'lost-fullscreen', 'mac-escape'):
        with session(mode) as c:
            open_setup(c)
            setup_ready(c)
            click(c, '#suv-start-presentation')
            wait_for(c, 'document.querySelector("#suv-display-dialog").open && !document.querySelector("#suv-start-presentation").disabled')
            assert not evaluate(c, '!!document.fullscreenElement')
            assert evaluate(c, '__displayTest.requests.length') == 1
            if mode == 'mac-escape':
                assert evaluate(c, '__displayTest.opens.length') == 0
            else:
                assert evaluate(c, '__displayTest.opens.length') == 1
                assert not evaluate(c, '__displayTest.popup && !__displayTest.popup.closed && !!__displayTest.popup.document.querySelector("#notes")')
            passed(f'{mode}: returns to setup without mounting private notes after placement or fullscreen is lost')

    with session('wrong-popup') as c:
        source = next(t for t in targets(c) if t['url'] == DECK)['id']
        c.key('n')
        wait_for(c, '__displayTest.popup && !!__displayTest.popup.document.querySelector("#notes")')
        p = attach(c, next(t for t in targets(c) if t['id'] != source))
        assert evaluate(p, 'getComputedStyle(document.body).visibility') == 'visible'
        click(p, '#display-setup')
        wait_for(c, 'document.querySelector("#suv-display-dialog").open')
        setup_ready(c)
        click(c, '#suv-start-presentation')
        wait_for(c, 'document.querySelector("#suv-display-dialog").open && !document.querySelector("#suv-start-presentation").disabled')
        assert not evaluate(c, '!!document.fullscreenElement')
        assert evaluate(p, 'getComputedStyle(document.body).visibility') == 'hidden'
        assert len(targets(c)) == 2
        click(c, '#suv-manual-notes')
        wait_for(p, 'getComputedStyle(document.body).visibility==="visible"')
        assert len(targets(c)) == 2
        passed('A reused notes window stays hidden if relocation is ignored, and explicit manual placement restores it')
        p.ws.close()

    with session('success') as c:
        open_setup(c)
        setup_ready(c)
        assert not evaluate(c, '!!document.querySelector("#suv-audience-screen safe")')
        before = evaluate(c, 'SUVPresent.currentIndex()')
        evaluate(c, 'document.querySelector("#suv-audience-screen").focus()')
        c.key('ArrowDown')
        c.key('p')
        assert evaluate(c, 'SUVPresent.currentIndex()') == before
        assert not evaluate(c, 'document.body.classList.contains("presenting")')
        c.call('Emulation.setEmulatedMedia', {'media': 'print'})
        assert evaluate(c, 'getComputedStyle(document.querySelector("#suv-display-dialog")).display') == 'none'
        c.call('Emulation.setEmulatedMedia', {'media': 'screen'})
        passed('Dialog keyboard interactions do not navigate/play slides, and setup is hidden in print')
        evaluate(c, '''(()=>{const a=document.querySelector('#suv-audience-screen'),n=document.querySelector('#suv-notes-screen');n.value=a.value;n.dispatchEvent(new Event('change',{bubbles:true}))})()''')
        assert evaluate(c, 'document.querySelector("#suv-start-presentation").disabled')
        passed('Selecting the same screen for audience and notes cannot start presentation')
        evaluate(c, '__displayTest.details.screens=[__displayTest.primary];__displayTest.details.dispatchEvent(new Event("screenschange"))')
        wait_for(c, 'document.querySelector("#suv-start-presentation").disabled')
        assert evaluate(c, '__displayTest.requests.length===0 && __displayTest.opens.length===0')
        passed('Screen disconnection invalidates setup without opening or moving windows')
        before = evaluate(c, 'SUVPresent.currentIndex()')
        evaluate(c, 'document.querySelector("#suv-display-close").focus()')
        c.key('Escape')
        wait_for(c, '!document.querySelector("#suv-display-dialog").open')
        assert evaluate(c, 'SUVPresent.currentIndex()') == before
        passed('Escape dismisses the setup dialog without changing the current slide')

    with session('deferred') as c:
        open_setup(c)
        click(c, '#suv-display-close')
        evaluate(c, '__displayTest.resolve()')
        time.sleep(.15)
        assert not evaluate(c, 'document.querySelector("#suv-display-dialog").open')
        assert evaluate(c, '__displayTest.requests.length===0 && __displayTest.opens.length===0')
        passed('A late permission response after closing does not reopen setup or start presentation')

    report = {
        'result': 'PASS', 'passed': len(checks), 'checks': checks,
        'evidence': evidence, 'transport': 'offline file://',
        'displayEvidence': 'Chromium virtual displays for success; explicit JS API mocks for failure paths. No physical HDMI/projector test.',
        'activationEvidence': 'Real CDP mouse events. All Runtime.evaluate calls use userGesture:false.',
        'browserSecurity': 'Default file-origin policy; no disable-web-security or allow-file-access-from-files.',
    }
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        run(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='suvlab-display-check-') as temporary:
            run(Path(temporary))
