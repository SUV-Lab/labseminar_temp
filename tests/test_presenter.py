#!/usr/bin/env python3
"""Real Chromium integration checks. No browser security relaxation is used."""
import argparse,base64,json,shutil,struct,subprocess,tempfile,time,urllib.request,zlib
from pathlib import Path
from chrome_driver import ChromeSession,WebSocket

ROOT=Path(__file__).resolve().parents[1]

def wait_for(page,expression,timeout=8):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if page.evaluate(expression):return
        time.sleep(.05)
    raise AssertionError('Timed out: '+expression)

def targets(browser):
    with urllib.request.urlopen(f'http://127.0.0.1:{browser.port}/json/list') as response:
        return [t for t in json.load(response) if t['type']=='page']

def attach(browser,target):
    page=object.__new__(ChromeSession)
    page.width=1280;page.height=850;page.timeout=20;page.events=[];page.counter=0
    page.ws=WebSocket(target['webSocketDebuggerUrl'])
    for method in ('Page.enable','Runtime.enable','Log.enable','Network.enable'):page.call(method)
    page.call('Network.emulateNetworkConditions',dict(offline=True,latency=0,downloadThroughput=0,uploadThroughput=0))
    page.call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':850,'deviceScaleFactor':1,'mobile':False})
    return page

def click_text(page,text):
    found=page.evaluate('''(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.textContent.includes(%s));if(!b)return false;b.click();b.blur();return true})()'''%json.dumps(text))
    assert found,'Missing button '+text

def current_preview(expression):
    """Evaluate against the inert current-slide document, not the presenter UI."""
    return '(d=>'+expression+')(document.querySelector("#current-preview").contentDocument)'

def screenshot_color_count(p,selector,path,channel,frame_id='current-preview'):
    """Count a primary color in the composited canvas area, not its readback buffer.

    A scripting-disabled iframe can have a populated canvas backing store while
    displaying only fallback content. PNG pixels catch that visible regression.
    The decoder supports Chromium's ordinary 8-bit RGB/RGBA non-interlaced PNGs.
    """
    if frame_id is None:
        box=p.evaluate('''(()=>{const b=document.querySelector(%s).getBoundingClientRect();return {left:b.left,top:b.top,right:b.right,bottom:b.bottom}})()'''%json.dumps(selector))
    else:
        box=p.evaluate('''(()=>{const f=document.getElementById(%s),a=f.getBoundingClientRect(),b=f.contentDocument.querySelector(%s).getBoundingClientRect(),s=a.width/f.offsetWidth;return {left:a.left+b.left*s,top:a.top+b.top*s,right:a.left+b.right*s,bottom:a.top+b.bottom*s}})()'''%(json.dumps(frame_id),json.dumps(selector)))
    png=p.screenshot(path)
    assert png[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8;compressed=[]
    while offset<len(png):
        length=struct.unpack('>I',png[offset:offset+4])[0]
        tag=png[offset+4:offset+8];data=png[offset+8:offset+8+length]
        if tag==b'IHDR':width,height,depth,color,compression,method,interlace=struct.unpack('>IIBBBBB',data)
        if tag==b'IDAT':compressed.append(data)
        offset+=12+length
    assert depth==8 and color in (2,6) and not compression and not method and not interlace
    channels=3 if color==2 else 4;stride=width*channels
    raw=zlib.decompress(b''.join(compressed));previous=bytearray(stride);matches=0
    left=max(0,int(box['left']));right=min(width,int(box['right'])+1)
    top=max(0,int(box['top']));bottom=min(height,int(box['bottom'])+1)
    assert right>left and bottom>top,box
    for y in range(height):
        start=y*(stride+1);kind=raw[start];row=bytearray(raw[start+1:start+1+stride])
        assert kind in range(5),kind
        if kind:
            for i in range(stride):
                a=row[i-channels] if i>=channels else 0;b=previous[i];c=previous[i-channels] if i>=channels else 0
                if kind==1:predict=a
                elif kind==2:predict=b
                elif kind==3:predict=(a+b)//2
                else:
                    value=a+b-c;pa=abs(value-a);pb=abs(value-b);pc=abs(value-c)
                    predict=a if pa<=pb and pa<=pc else b if pb<=pc else c
                row[i]=(row[i]+predict)&255
        if top<=y<bottom:
            for x in range(left,right):
                rgb=row[x*channels:x*channels+3]
                if rgb[channel]>140 and all(rgb[channel]>rgb[i]*1.5 for i in range(3) if i!=channel):matches+=1
        previous=row
    return matches

def live_canvas_checks(c,p,out,passed):
    """Check pixels and changing content; a working playback button is insufficient."""
    wait_for(p,current_preview('!!d?.querySelector("canvas#demo-animation")'))
    source='document.querySelector("#demo-animation").toDataURL()'
    mirrored=current_preview('d.querySelector("#demo-animation").toDataURL()')
    initial=c.evaluate(source)
    wait_for(p,mirrored+'==='+json.dumps(initial))
    p.evaluate('window.initialPreviewDocument=document.querySelector("#current-preview").contentDocument')
    p.key('p')
    wait_for(c,source+'!=='+json.dumps(initial))
    wait_for(p,mirrored+'!=='+json.dumps(initial))
    p.key('p')
    paused=c.evaluate(source)
    wait_for(p,mirrored+'==='+json.dumps(paused))
    time.sleep(.2)
    assert c.evaluate(source)==paused and p.evaluate(mirrored)==paused
    assert screenshot_color_count(p,'#demo-animation',out/'live_canvas_paused.png',2)>50,'Canvas backing store is populated but the blue dot is not visibly composited'
    p.key('r')
    wait_for(p,mirrored+'==='+json.dumps(initial))
    assert c.evaluate(source)==initial
    passed('Current preview displays moving canvas pixels and matches audience pause/reset frames')

    # Real players change text, property-only input values and their DOM tree.
    # Include a late canvas, then replace it with two canvases as scene panels do.
    c.evaluate('''(()=>{
      const host=document.createElement('div');host.id='live-probe';
      document.querySelectorAll('.slide')[2].append(host);
      host.innerHTML='<span id="live-phase" onclick="window.previewHandlerRan=true">Initial phase</span><input id="live-range" type="range" min="0" max="10" value="0"><canvas id="live-mini" width="80" height="40"></canvas><svg width="80" height="40"><circle id="live-circle" cx="10" cy="20" r="5"><animate attributeName="r" from="5" to="8" dur="2s" repeatCount="indefinite"></animate><set attributeName="opacity" to="0.5" begin="1s"></set></circle></svg><script id="live-script">window.previewScriptRan=true</script><aside class="speaker-notes" hidden>PRIVATE_LIVE_NOTE</aside>';
      const ctx=host.querySelector('canvas').getContext('2d');ctx.fillStyle='rgb(255,0,0)';ctx.fillRect(0,0,80,40);
      host.querySelector('#live-range').value='3';
    })()''')
    wait_for(p,current_preview('!!d.querySelector("#live-mini")'))
    pixel=current_preview('[...d.querySelector("#live-mini").getContext("2d").getImageData(10,10,1,1).data].join(",")')
    wait_for(p,pixel+'==="255,0,0,255"')
    wait_for(p,current_preview('d.querySelector("#live-range").value==="3"'))
    assert p.evaluate(current_preview('!d.querySelector("#live-phase").hasAttribute("onclick") && !d.querySelector("#live-script") && !d.body.textContent.includes("PRIVATE_LIVE_NOTE")'))
    c.evaluate('''(()=>{
      const h=document.querySelector('#live-probe');
      h.querySelector('#live-phase').textContent='Updated phase';
      h.querySelector('#live-phase').className='active';
      h.querySelector('#live-range').value='7';
      h.querySelector('#live-circle').setAttribute('cx','42');
      const old=h.querySelector('#live-mini');
      const replacement=document.createElement('canvas');replacement.id='live-mini';replacement.width=96;replacement.height=48;
      old.replaceWith(replacement);
      const ctx=replacement.getContext('2d');ctx.fillStyle='rgb(0,255,0)';ctx.fillRect(0,0,96,48);
      const extra=document.createElement('canvas');extra.id='live-extra';extra.width=32;extra.height=32;
      h.prepend(extra);extra.getContext('2d').fillRect(0,0,32,32);
    })()''')
    wait_for(p,current_preview('d.querySelector("#live-phase")?.textContent==="Updated phase" && d.querySelector("#live-phase").className==="active" && d.querySelector("#live-range").value==="7" && d.querySelector("#live-circle").getAttribute("cx")==="42"'))
    wait_for(p,current_preview('d.querySelector("#live-mini")?.width===96 && !!d.querySelector("#live-extra")'))
    wait_for(p,pixel+'==="0,255,0,255"')
    # A seek can change only pixels, without a DOM mutation or playback event.
    c.evaluate('''(()=>{const x=document.querySelector('#live-mini').getContext('2d');x.fillStyle='rgb(0,0,255)';x.fillRect(0,0,96,48)})()''')
    wait_for(p,pixel+'==="0,0,255,255"')
    assert p.evaluate('window.initialPreviewDocument===document.querySelector("#current-preview").contentDocument')
    assert p.evaluate(current_preview('!d.querySelector("script,video,audio,.speaker-notes,animate,animateMotion,animateTransform,animateColor,set")'))
    c.evaluate('document.querySelector("#live-extra").remove()')
    wait_for(p,current_preview('!d.querySelector("#live-extra")'))
    passed('Live preview mirrors DOM/input/SVG changes, late/replaced canvases and pixel-only seeking without reloading or executing scripts')

    c.evaluate('''(()=>{let x=document.createElement('canvas');x.id='next-probe';x.width=32;x.height=32;x.getContext('2d').fillRect(0,0,32,32);document.querySelectorAll('.slide')[3].append(x);const svg=document.querySelector('#live-probe svg').cloneNode(true);svg.id='next-svg-probe';document.querySelectorAll('.slide')[3].append(svg);SUVPresent.show(1);SUVPresent.show(2)})()''')
    next_image="document.querySelector('#next-preview').contentDocument?.querySelector('img[alt=\"Media preview\"]')"
    wait_for(p,'!!'+next_image)
    still=p.evaluate(next_image+'.src')
    c.evaluate('''(()=>{const x=document.querySelector('#next-probe').getContext('2d');x.fillStyle='red';x.fillRect(0,0,32,32)})()''')
    time.sleep(.15)
    assert p.evaluate(next_image+'.src')==still
    assert p.evaluate('!document.querySelector("#next-preview").contentDocument.querySelector("canvas,video,audio,script,animate,animateMotion,animateTransform,animateColor,set")')
    c.evaluate('document.querySelector("#next-probe").remove();document.querySelector("#next-svg-probe").remove();document.querySelector("#live-probe").remove()')
    wait_for(p,current_preview('!d.querySelector("#live-probe")'))
    passed('Next-slide preview remains a still image while the current preview updates')

def run(out,headless=True):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists():(out/'report.json').unlink()
    checks=[]
    def passed(name):checks.append(name);print('PASS '+name,flush=True)
    with ChromeSession(width=1280,height=850,headless=headless) as c:
        c.call('Network.emulateNetworkConditions',dict(offline=True,latency=0,downloadThroughput=0,uploadThroughput=0))
        c.navigate((ROOT/'examples/presenter-notes.html').as_uri())
        original_id=targets(c)[0]['id']
        assert c.evaluate('SUVPresent.getState().count===4')
        assert c.evaluate('[...document.querySelectorAll(".speaker-notes")].every(n=>getComputedStyle(n).display==="none")')
        assert not c.evaluate('document.body.innerText.includes("Thank you for the introduction.")')
        passed('Notes stay hidden in the ordinary audience view')

        c.evaluate("let field=document.createElement('input');field.id='closed-popup-input';document.body.append(field);field.focus()")
        c.key('n')
        assert len(targets(c))==1
        assert c.evaluate("document.querySelector('#closed-popup-input').value")=='n'
        c.evaluate("document.querySelector('#closed-popup-input').remove();window.scrollTo(0,0)")
        passed('Typing N in an input does not open a presenter window')

        c.key('f');wait_for(c,'!!document.fullscreenElement')
        c.key('n')
        wait_for(c,'!!window.SUVPresenter')
        c.evaluate('window.testNotes=SUVPresent.openNotes();true')
        wait_for(c,'testNotes.document.body.innerText.includes("Thank you for the introduction.")')
        note_target=next(t for t in targets(c) if t['id']!=original_id)
        p=attach(c,note_target)
        assert c.evaluate('testNotes.opener===window')
        assert c.evaluate('document.body.classList.contains("presenting")')
        wait_for(p,'''[...document.querySelectorAll('iframe')].every(f=>f.contentDocument.readyState==='complete' && f.contentDocument.querySelector('.slide') && getComputedStyle(f.contentDocument.querySelector('.slide')).display==='flex')''')
        p.screenshot(out/'presenter.png');c.screenshot(out/'audience.png')
        passed('N opens an offline presenter window with the current script')

        box='(s=>{const b=document.querySelector(s).getBoundingClientRect();return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)}})'
        def boxes():return [p.evaluate(f'{box}({json.dumps(s)})') for s in ('.current-pane .preview-box','.next-pane .preview-box','#notes')]
        cur,nxt,notes=boxes()
        assert cur['w']>=.55*1280 and nxt['w']<.5*cur['w'] and nxt['x']>=cur['x']+cur['w'] and nxt['y']+nxt['h']<=notes['y']
        assert notes['x']>=cur['x']+cur['w'] and notes['h']>=480 and p.evaluate("getComputedStyle(document.querySelector('#notes')).fontSize")=='32px'
        assert p.evaluate('getComputedStyle(document.body).backgroundColor')=='rgb(11, 17, 32)'
        assert p.evaluate('[...document.querySelectorAll("iframe")].every(f=>getComputedStyle(f.contentDocument.body).backgroundColor==="rgb(255, 255, 255)")')
        toggle="(b=>b.getAttribute('aria-pressed')+' '+b.textContent)(document.querySelector('#reading-toggle'))"
        assert p.evaluate(toggle)=='false 대본 중심'
        point=p.evaluate("(()=>{const r=document.querySelector('#reading-toggle').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        for kind in ('mousePressed','mouseReleased'):
            p.call('Input.dispatchMouseEvent',dict(type=kind,**point,button='left',clickCount=1))
        assert p.evaluate(toggle)=='true 슬라이드 중심'
        assert p.evaluate('document.activeElement.id')=='notes'
        cur2,nxt2,notes2=boxes()
        assert notes2['w']>=.58*1280 and notes2['h']>notes['h'] and cur2['w']<cur['w'] and nxt2['y']>=cur2['y']+cur2['h'] and nxt2['x']+nxt2['w']<=notes2['x']
        assert p.evaluate("[...document.querySelectorAll('iframe')].every(f=>Math.abs(new DOMMatrix(f.style.transform).a*Number(f.dataset.width)-f.parentNode.clientWidth)<1)")
        p.screenshot(out/'presenter_reading.png')
        p.evaluate("document.querySelector('#reading-toggle').focus()");p.key('Enter')
        assert p.evaluate(toggle)=='false 대본 중심'
        assert p.evaluate('document.activeElement.id')=='reading-toggle' and c.evaluate('SUVPresent.currentIndex()')==0
        assert boxes()[2]==notes
        p.evaluate("document.querySelector('#notes').focus()")
        passed('Presenter view: large current slide, small next slide and tall script; 대본 중심/슬라이드 중심 switch the layout')

        c.call('Page.bringToFront');c.key('Home')  # Clear the openNotes focus-click guard.
        p.call('Page.bringToFront')
        if headless:
            # Headless Chrome treats both popup windows as focused. Exercise the
            # handler explicitly here; --headed verifies native window focus.
            c.evaluate('window.dispatchEvent(new Event("blur"))')
        else:wait_for(c,'!document.hasFocus()')
        c.call('Page.bringToFront')
        for kind in ['mousePressed','mouseReleased']:
            c.call('Input.dispatchMouseEvent',dict(type=kind,x=800,y=600,button='left',clickCount=1))
        assert c.evaluate('SUVPresent.currentIndex()')==0
        for kind in ['mousePressed','mouseReleased']:
            c.call('Input.dispatchMouseEvent',dict(type=kind,x=800,y=600,button='left',clickCount=1))
        assert c.evaluate('SUVPresent.currentIndex()')==1
        c.key('f');wait_for(c,'!!document.fullscreenElement')
        c.key('Escape');wait_for(c,'!SUVPresent.getState().presenting')
        c.evaluate('SUVPresent.show(0)')
        passed('F→N keeps slide mode; returning focus does not advance; F/Escape still work')

        # N reuses the same window, rather than opening another one for this deck.
        assert c.evaluate('SUVPresent.openNotes()===testNotes')
        assert len(targets(c))==2
        c.evaluate('SUVPresent.show(1)')
        wait_for(p,'document.body.innerText.includes("This is a longer script")')
        click_text(p,'다음')
        assert c.evaluate('SUVPresent.currentIndex()')==2
        wait_for(p,'document.body.innerText.includes("The blue dot now moves")')
        p.key('ArrowLeft')
        assert c.evaluate('SUVPresent.currentIndex()')==1
        p.key('PageDown');assert c.evaluate('SUVPresent.currentIndex()')==2
        p.key('PageUp');assert c.evaluate('SUVPresent.currentIndex()')==1
        passed('Navigation synchronizes in both directions and reuses the popup')

        c.evaluate('SUVPresent.show(2)')
        point=p.evaluate("(()=>{const r=document.querySelector('#prev').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        for kind in ('mousePressed','mouseReleased'):
            p.call('Input.dispatchMouseEvent',dict(type=kind,**point,button='left',clickCount=1))
        assert c.evaluate('SUVPresent.currentIndex()')==1
        assert p.evaluate('document.activeElement.id')=='notes'
        p.key(' ');assert c.evaluate('SUVPresent.currentIndex()')==2
        p.evaluate("document.querySelector('#jump').value='';document.querySelector('#jump').focus()")
        p.call('Input.insertText',{'text':'2'});p.key('Enter')
        assert c.evaluate('SUVPresent.currentIndex()')==1
        assert p.evaluate('document.activeElement.id')=='notes'
        p.key('PageDown');assert c.evaluate('SUVPresent.currentIndex()')==2
        p.evaluate("document.querySelector('#prev').focus()")
        p.key('Enter');assert c.evaluate('SUVPresent.currentIndex()')==1
        assert p.evaluate('document.activeElement.id')=='prev'
        p.evaluate("document.querySelector('#notes').focus()")
        passed('Mouse controls return to notes while keyboard button activation retains focus')

        # A script can overflow the default panel but fit entirely in reading mode.
        original_notes=c.evaluate("[1,2].map(i=>document.querySelectorAll('.speaker-notes')[i].innerHTML)")
        c.evaluate("[1,2].forEach(i=>document.querySelectorAll('.speaker-notes')[i].innerHTML='<p>Reading position should survive layout changes.</p>'.repeat(6));SUVPresent.show(1)")
        scroll="document.querySelector('#notes').scrollTop"
        overflow="(n=>n.scrollHeight>n.clientHeight)(document.querySelector('#notes'))"
        assert p.evaluate(overflow)
        p.evaluate("document.querySelector('#notes').scrollTop=120")
        saved_scroll=p.evaluate(scroll)
        assert saved_scroll>0
        p.evaluate("document.querySelector('#reading-toggle').click()")
        assert not p.evaluate(overflow) and p.evaluate(scroll)==0
        p.evaluate("document.querySelector('#reading-toggle').click()")
        assert abs(p.evaluate(scroll)-saved_scroll)<1
        assert c.evaluate('SUVPresent.currentIndex()')==1
        assert p.evaluate("getComputedStyle(document.querySelector('#notes')).fontSize")=='32px'
        # Switching slides in the wide mode must not share remembered positions.
        p.evaluate("document.querySelector('#reading-toggle').click();document.querySelector('#next').click();document.querySelector('#reading-toggle').click()")
        assert c.evaluate('SUVPresent.currentIndex()')==2 and p.evaluate(scroll)==0
        p.evaluate("document.querySelector('#notes').scrollTop=60;document.querySelector('#reading-toggle').click();document.querySelector('#prev').click();document.querySelector('#reading-toggle').click()")
        assert c.evaluate('SUVPresent.currentIndex()')==1 and abs(p.evaluate(scroll)-saved_scroll)<1
        c.evaluate("[1,2].forEach((i,j)=>document.querySelectorAll('.speaker-notes')[i].innerHTML="+json.dumps(original_notes)+"[j]);SUVPresent.show(1)")
        passed('Reading layout preserves per-slide scroll positions when the wider script fits without scrolling')

        # Long scripts keep their reading position across status updates and slide changes.
        c.evaluate('''document.querySelectorAll('.speaker-notes')[1].insertAdjacentHTML('beforeend','<p>Long script paragraph.</p>'.repeat(20));SUVPresent.show(1)''')
        p.evaluate("document.querySelector('#font-larger').click();document.querySelector('#notes').scrollTop=200")
        assert p.evaluate("getComputedStyle(document.querySelector('#notes')).fontSize")=='34px'
        p.evaluate("document.querySelector('#blank').click()")
        assert p.evaluate("document.querySelector('#notes').scrollTop")==200
        p.evaluate("document.querySelector('#blank').click();document.querySelector('#next').click();document.querySelector('#prev').click()")
        assert p.evaluate("document.querySelector('#notes').scrollTop")==200
        p.evaluate("document.querySelector('#font-smaller').click();document.querySelector('#timer-toggle').click()")
        wait_for(p,"document.querySelector('#elapsed').textContent!=='00:00'")
        p.evaluate("document.querySelector('#timer-toggle').click()")
        paused=p.evaluate("document.querySelector('#elapsed').textContent")
        time.sleep(1.05)
        assert p.evaluate("document.querySelector('#elapsed').textContent")==paused
        p.evaluate("document.querySelector('#timer-reset').click()")
        assert p.evaluate("document.querySelector('#elapsed').textContent")=='00:00'
        ratio="(n=>n.scrollTop/(n.scrollHeight-n.clientHeight))(document.querySelector('#notes'))"
        before=p.evaluate(ratio);p.evaluate("document.querySelector('#reading-toggle').click()")
        assert before>0 and abs(p.evaluate(ratio)-before)<.05
        p.evaluate("document.querySelector('#reading-toggle').click()")
        p.call('Emulation.setDeviceMetricsOverride',dict(width=800,height=700,deviceScaleFactor=1,mobile=False))
        assert p.evaluate("document.documentElement.scrollWidth<=innerWidth && document.querySelector('#notes').clientHeight>200")
        assert p.evaluate("getComputedStyle(document.querySelector('#reading-toggle')).display")=='none'
        cur3,nxt3,notes3=boxes()
        assert notes3['w']>cur3['w'] and nxt3['y']>=cur3['y']+cur3['h']
        p.width=800;p.height=700;p.screenshot(out/'presenter_compact.png')
        p.call('Emulation.setDeviceMetricsOverride',dict(width=1280,height=850,deviceScaleFactor=1,mobile=False))
        p.width=1280;p.height=850
        passed('Long scripts, text size, timer and compact layout remain usable')

        # Form controls must retain their editing keys and must not navigate the deck.
        c.evaluate("let input=document.createElement('input');input.id='test-input';document.body.append(input);input.focus()")
        c.key('ArrowRight');c.key('n')
        assert c.evaluate('SUVPresent.currentIndex()')==1
        assert len(targets(c))==2
        c.evaluate("document.querySelector('#test-input').remove()")
        p.evaluate("let input=document.createElement('textarea');input.id='test-input';document.body.append(input);input.focus()")
        p.key('ArrowRight');p.key(' ')
        assert c.evaluate('SUVPresent.currentIndex()')==1
        p.evaluate("document.querySelector('#test-input').remove()")
        passed('Input fields retain their keys without changing slides')

        p.key('End')
        assert c.evaluate('SUVPresent.currentIndex()')==3
        assert c.evaluate('SUVPresent.getState().notesHTML')==''
        assert p.evaluate('document.body.innerText.includes("노트")')
        p.key('Home')
        assert c.evaluate('SUVPresent.currentIndex()')==0
        c.evaluate('SUVPresent.show(NaN);SUVPresent.show(Infinity);SUVPresent.show("bad")')
        assert c.evaluate('SUVPresent.currentIndex()')==0
        passed('First/last navigation, invalid indices and slides without notes are handled')

        # Source scripts and speaker notes must never be copied into preview HTML.
        c.evaluate('''(()=>{let n=document.querySelector('.speaker-notes');n.insertAdjacentHTML('beforeend','<p onclick="window.__noteRan=1">PRIVATE_NOTE_SENTINEL</p><img src="bad" onerror="window.__noteRan=2"><script>window.__noteRan=3</script>');SUVPresent.show(0)})()''')
        state=c.evaluate('SUVPresent.getState()')
        preview=c.evaluate('SUVPresent.preview(0)')
        assert 'onclick' not in state['notesHTML'] and '<script' not in state['notesHTML'] and '<img' not in state['notesHTML']
        assert 'PRIVATE_NOTE_SENTINEL' not in preview['html'] and 'speaker-notes' not in preview['html']
        assert p.evaluate('[...document.querySelectorAll("iframe")].every(f=>f.sandbox.contains("allow-same-origin")) && document.querySelector("#current-preview").sandbox.contains("allow-scripts") && !document.querySelector("#next-preview").sandbox.contains("allow-scripts")')
        wait_for(p,current_preview('d?.readyState==="complete" && !!d.querySelector("meta[http-equiv=\\"Content-Security-Policy\\"]")'))
        csp_result=p.evaluate(current_preview('''(()=>{
          const policy=d.querySelector('meta[http-equiv="Content-Security-Policy"]');
          const script=d.createElement('script');script.textContent='window.__liveScriptCanary=true';d.body.append(script);script.remove();
          const button=d.createElement('button');button.setAttribute('onclick','window.__liveHandlerCanary=true');d.body.append(button);button.click();button.remove();
          return {policy:policy.content,scriptRan:!!d.defaultView.__liveScriptCanary,handlerRan:!!d.defaultView.__liveHandlerCanary};
        })()'''))
        assert "script-src 'none'" in csp_result['policy'] and not csp_result['scriptRan'] and not csp_result['handlerRan'],csp_result
        passed('Notes are excluded; preview CSP blocks injected scripts and handlers while current canvas rendering is enabled')

        # No duplicate source animation is started by the previews.
        c.evaluate('SUVPresent.show(2);window.mediaActions=[];document.addEventListener("suv:media",e=>mediaActions.push(e.detail.action))')
        p.key('p');p.key('r')
        assert c.evaluate('mediaActions')==['toggle','reset']
        p.key('b');assert c.evaluate('SUVPresent.getState().blank')
        assert p.evaluate('getComputedStyle(document.body).visibility')=='visible'
        p.key('b');assert not c.evaluate('SUVPresent.getState().blank')
        passed('Presenter media keys and blackout control the audience only')

        live_canvas_checks(c,p,out,passed)

        # A real HTMLVideoElement exercises play/pause/reset and slide-leave pausing.
        c.evaluate('''(()=>{let v=document.createElement('video');v.id='test-video';v.muted=true;v.setAttribute('data-noautoplay','');let can=document.createElement('canvas');can.width=64;can.height=64;let ctx=can.getContext('2d');ctx.fillStyle='rgb(255,0,0)';ctx.fillRect(0,0,64,64);v.srcObject=can.captureStream(30);window.testStream=v.srcObject;window.testVideoCanvas=can;document.querySelectorAll('.slide')[3].append(v);SUVPresent.show(3)})()''')
        p.key('p');wait_for(c,'!document.querySelector("#test-video").paused')
        video_pixel=current_preview('(()=>{const v=d.querySelector("canvas#test-video");return v&&[...v.getContext("2d").getImageData(10,10,1,1).data]})()')
        wait_for(p,'(x=>x&&x[0]>245&&x[1]<10&&x[2]<10&&x[3]===255)('+video_pixel+')')
        c.evaluate('''(()=>{const x=testVideoCanvas.getContext('2d');x.fillStyle='rgb(0,255,0)';x.fillRect(0,0,64,64);testStream.getVideoTracks()[0].requestFrame()})()''')
        wait_for(c,'(()=>{const v=document.querySelector("#test-video"),a=document.createElement("canvas");a.width=a.height=64;const x=a.getContext("2d");x.drawImage(v,0,0);return x.getImageData(10,10,1,1).data[1]>245})()')
        wait_for(p,'(x=>x&&x[0]<10&&x[1]>245&&x[2]<10&&x[3]===255)('+video_pixel+')')
        assert p.evaluate(current_preview('!d.querySelector("video,audio,script")'))
        assert screenshot_color_count(p,'#test-video',out/'live_video_green.png',1)>20,'Video frame exists in readback but is not visibly composited'
        p.key('p');assert c.evaluate('document.querySelector("#test-video").paused')
        paused_video=p.evaluate(video_pixel)
        time.sleep(.15);assert p.evaluate(video_pixel)==paused_video
        p.key('p');wait_for(c,'!document.querySelector("#test-video").paused')
        p.key('r');assert c.evaluate('document.querySelector("#test-video").paused')
        p.key('p');wait_for(c,'!document.querySelector("#test-video").paused')
        c.evaluate('SUVPresent.show(2)')
        assert c.evaluate('document.querySelector("#test-video").paused')
        c.evaluate('testStream.getTracks().forEach(t=>t.stop());document.querySelector("#test-video").remove()')
        passed('Native video pixels update in the inert current preview; controls and slide-leave pausing use the audience player only')

        # Printing while blacked out still exports all audience slides, never notes.
        c.evaluate('SUVPresent.toggleBlank()')
        pdf=c.call('Page.printToPDF',dict(printBackground=True,preferCSSPageSize=True))
        (out/'audience.pdf').write_bytes(base64.b64decode(pdf['data']))
        exported=subprocess.check_output(['pdftotext',str(out/'audience.pdf'),'-'],text=True)
        assert 'PRIVATE_NOTE_SENTINEL' not in exported and 'Thank you for the introduction.' not in exported
        assert all(t in exported for t in ['Read the script','Animation controls','Notes are optional'])
        assert len([s for s in exported.split('\f') if s.strip()])==4
        c.evaluate('SUVPresent.toggleBlank()')
        passed('PDF has all four slides and no speaker notes or blackout overlay')

        p.ws.close();c.evaluate('testNotes.close()')
        wait_for(c,'testNotes.closed')
        c.key('n');c.evaluate('window.testNotes=SUVPresent.openNotes();true')
        wait_for(c,'testNotes.document.body.innerText.includes("The blue dot now moves")')
        p=attach(c,next(t for t in targets(c) if t['id']!=original_id))
        assert c.evaluate('SUVPresent.currentIndex()')==2
        wait_for(p,current_preview('!!d?.querySelector("canvas#demo-animation")'))
        reopened=current_preview('d.querySelector("#demo-animation").toDataURL()')
        before=p.evaluate(reopened)
        p.key('p');wait_for(p,reopened+'!=='+json.dumps(before));p.key('r')
        passed('Closing and reopening notes keeps the current slide and restores live canvas mirroring')

        p.call('Page.reload')
        wait_for(p,'!document.querySelector("#notes")')
        p.ws.close()
        c.key('n')
        c.evaluate('window.testNotes=SUVPresent.openNotes();true')
        wait_for(c,'!!testNotes.document.querySelector("#notes")')
        p=attach(c,next(t for t in targets(c) if t['id']!=original_id))
        wait_for(p,'document.querySelector("#notes")?.textContent.includes("The blue dot now moves")')
        assert len(targets(c))==2
        c.evaluate('document.querySelector("#demo-toggle").focus()')
        c.key('PageDown');assert c.evaluate('SUVPresent.currentIndex()')==3
        c.evaluate('SUVPresent.show(2);window.buttonMedia=[];document.addEventListener("suv:media",e=>buttonMedia.push(e.detail.action));document.querySelector("#demo-toggle").focus()')
        c.key('p');c.key('r');assert c.evaluate('buttonMedia')==['toggle','reset']
        c.key('b');assert c.evaluate('SUVPresent.getState().blank')
        c.key('b');assert not c.evaluate('SUVPresent.getState().blank')
        c.key(' ');assert c.evaluate('SUVPresent.currentIndex()')==2
        passed('N restores a refreshed popup; focused slide buttons keep navigation and media keys')

        # A reload must disconnect the old UI, so it cannot control a stale document.
        c.call('Page.reload')
        wait_for(c,'typeof SUVPresent!=="undefined" && SUVPresent.getState().connected && SUVPresent.currentIndex()===0')
        wait_for(p,'[...document.querySelectorAll("button")].some(b=>b.textContent.includes("다음")&&b.disabled)')
        before=c.evaluate('SUVPresent.currentIndex()')
        p.key('ArrowRight')
        assert c.evaluate('SUVPresent.currentIndex()')==before
        p.screenshot(out/'disconnected.png');p.ws.close()
        passed('An old presenter cannot control the deck after it reloads')

        # A denied popup gives an explicit, recoverable message without breaking slides.
        c.evaluate('window.realOpen=window.open;window.open=()=>null;window.alert=t=>window.popupMessage=t')
        c.key('n')
        assert c.evaluate('popupMessage.includes("차단")')
        c.evaluate('window.open=realOpen;SUVPresent.show(1)')
        assert c.evaluate('SUVPresent.currentIndex()')==1
        passed('A blocked popup reports the issue and leaves navigation usable')
        errors=[e for e in c.events if e.get('method')=='Runtime.exceptionThrown']
        assert not errors,errors
    # A hand-copied old deck may be missing the new companion asset.
    with tempfile.TemporaryDirectory(prefix='suvlab-missing-') as temp:
        folder=Path(temp)
        shutil.copy2(ROOT/'design/present.js',folder/'present.js')
        (folder/'deck.html').write_text('<!doctype html><meta charset="utf-8"><title>Missing companion</title><section class="slide"><h1>Test</h1></section><script src="present.js"></script>')
        with ChromeSession(width=1280,height=850,headless=headless) as c:
            c.navigate((folder/'deck.html').as_uri())
            c.evaluate('window.failedPopup=SUVPresent.openNotes();true')
            wait_for(c,'failedPopup.document.body.textContent.includes("presenter.js")')
            assert c.evaluate('failedPopup.document.body.textContent.includes("같은 폴더")')
            assert c.evaluate('SUVPresent.getState().count')==1
    passed('Missing presenter.js gives a useful recovery message')
    with ChromeSession(width=1280,height=850,headless=headless) as c:
        c.navigate((ROOT/'examples/presenter-notes.html').as_uri())
        source=targets(c)[0]['id']
        c.key('n');wait_for(c,'!!window.SUVPresenter')
        c.evaluate('window.testNotes=SUVPresent.openNotes();true')
        wait_for(c,'!!testNotes.document.querySelector("#notes")')
        p=attach(c,next(t for t in targets(c) if t['id']!=source))
        p.call('Target.closeTarget',{'targetId':source})
        wait_for(p,'document.querySelector("#next").disabled && !document.querySelector("#disconnect-message").hidden')
        p.ws.close()
    passed('Closing the audience window disables the remaining presenter')
    report={'passed':len(checks),'checks':checks,'browserSecurity':'default; no allow-file-access-from-files or disable-web-security','transport':'offline file://','result':'PASS'}
    report['focusEvidence']='synthetic blur event; use --headed for native focus' if headless else 'native window focus verified'
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Save screenshots, PDF and report here.')
    parser.add_argument('--headed',action='store_true',help='Open isolated visible Chrome windows to check native focus (requires a desktop).')
    args=parser.parse_args()
    if args.output:report=run(args.output.resolve(),headless=not args.headed)
    else:
        with tempfile.TemporaryDirectory(prefix='suvlab-test-') as temp:report=run(Path(temp),headless=not args.headed)
    print(json.dumps(report,ensure_ascii=False,indent=2))
