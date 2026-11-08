#!/usr/bin/env python3
"""Capture presenter-view screenshots of a deck. Offline file://, default browser security."""
import argparse,json
from pathlib import Path
from chrome_driver import ChromeSession
from test_presenter import wait_for,targets,attach

ROOT=Path(__file__).resolve().parents[1]
READY='''[...document.querySelectorAll('iframe')].every(f=>f.contentDocument&&f.contentDocument.readyState==='complete'&&f.contentDocument.body&&f.contentDocument.body.firstChild!==null)'''
GEOMETRY='''(()=>{const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)}};
const n=document.querySelector('#notes');
return {reading:document.querySelector('main').classList.contains('reading'),current:r('.current-pane .preview-box'),next:r('.next-pane .preview-box'),notes:r('#notes'),
notesFont:getComputedStyle(n).fontSize,notesScrollable:n.scrollHeight>n.clientHeight,horizontalScroll:document.documentElement.scrollWidth>innerWidth,
scales:[...document.querySelectorAll('iframe')].map(f=>f.style.transform)}})()'''

def capture(deck,out,slides,sizes,prefix,headless=True):
    out.mkdir(parents=True,exist_ok=True);shots=[]
    with ChromeSession(width=1280,height=850,headless=headless) as c:
        c.call('Network.emulateNetworkConditions',dict(offline=True,latency=0,downloadThroughput=0,uploadThroughput=0))
        c.navigate(deck.resolve().as_uri())
        source=targets(c)[0]['id']
        c.key('n');wait_for(c,'!!window.SUVPresenter',20)
        c.evaluate('window.notesWindow=SUVPresent.openNotes();true')
        wait_for(c,'!!notesWindow.document.querySelector("#notes")',20)
        p=attach(c,next(t for t in targets(c) if t['id']!=source))
        for width,height in sizes:
            p.call('Emulation.setDeviceMetricsOverride',dict(width=width,height=height,deviceScaleFactor=1,mobile=False))
            p.width=width;p.height=height
            # The toggle is hidden below 900 px, where the script always gets the wide column.
            modes=('default','reading') if width>900 else ('default',)
            for number in slides:
                c.evaluate(f'SUVPresent.show({number-1})')
                wait_for(p,f'document.querySelector("#jump").value==="{number}"')
                wait_for(p,READY,20)
                for mode in modes:
                    p.evaluate(f'''(()=>{{const on={'true' if mode=='reading' else 'false'};if(document.querySelector('main').classList.contains('reading')!==on)document.querySelector('#reading-toggle').click();return true}})()''')
                    name=f'{prefix}_s{number:02d}_{width}x{height}_{mode}.png'
                    p.screenshot(out/name)
                    shots.append(dict(file=name,slide=number,size=f'{width}x{height}',**p.evaluate(GEOMETRY)))
                p.evaluate("document.querySelector('main').classList.contains('reading')&&document.querySelector('#reading-toggle').click();true")
        errors=[e for e in c.events+p.events if e.get('method')=='Runtime.exceptionThrown']
        assert not errors,errors
    return shots

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deck',type=Path,default=ROOT/'examples/presenter-notes.html')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--slides',default='1',help='1-based slide numbers, e.g. 1,13,15')
    parser.add_argument('--sizes',default='1280x850',help='e.g. 1280x850,800x700')
    parser.add_argument('--prefix',default='presenter')
    parser.add_argument('--headed',action='store_true')
    args=parser.parse_args()
    slides=[int(s) for s in args.slides.split(',')]
    sizes=[tuple(int(v) for v in s.split('x')) for s in args.sizes.split(',')]
    print(json.dumps(capture(args.deck,args.output.resolve(),slides,sizes,args.prefix,not args.headed),ensure_ascii=False,indent=1))
