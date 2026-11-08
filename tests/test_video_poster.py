#!/usr/bin/env python3
"""Check poster/frame parity using visible pixels in the audience and previews.

Chrome records a blue fixture video locally; no external video file, ffmpeg,
network service, or Python imaging package is needed.
"""
import argparse
import json
from pathlib import Path
import tempfile

from chrome_driver import ChromeSession
from test_presenter import attach, screenshot_color_count, targets, wait_for

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    return '''<!doctype html><meta charset="utf-8"><title>Video poster parity</title>
<base href="'''+(ROOT/'design').as_uri()+'''/"><link rel="stylesheet" href="deck.css">
<style>html,body{margin:0}deck-stage{display:block}.slide{width:1920px;height:1080px}
#poster-video{display:block;width:1200px;height:675px;margin:60px auto;object-fit:contain}</style>
<deck-stage>
<section class="slide"><h1 class="title">Start</h1><aside class="speaker-notes" hidden>Advance to the video.</aside></section>
<section class="slide"><h1 class="title">Poster and video</h1>
<video id="poster-video" data-noautoplay muted loop preload="auto" playsinline></video>
<aside class="speaker-notes" hidden>Play, pause, and reset the video.</aside></section>
</deck-stage><script src="present.js"></script>'''


CREATE_VIDEO='''(async()=>{
  const poster=document.createElement('canvas');poster.width=320;poster.height=180;
  const pc=poster.getContext('2d');pc.fillStyle='red';pc.fillRect(0,0,320,180);
  const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;
  const context=canvas.getContext('2d');context.fillStyle='blue';context.fillRect(0,0,320,180);
  const stream=canvas.captureStream(24),track=stream.getVideoTracks()[0];
  const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'}),chunks=[];
  recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data)};
  const stopped=new Promise(resolve=>recorder.onstop=resolve);
  recorder.start();
  const refresh=setInterval(()=>{context.fillRect(0,0,320,180);track.requestFrame()},40);
  await new Promise(resolve=>setTimeout(resolve,500));
  clearInterval(refresh);recorder.stop();await stopped;stream.getTracks().forEach(t=>t.stop());
  const video=document.querySelector('#poster-video');video.poster=poster.toDataURL();
  video.src=URL.createObjectURL(new Blob(chunks,{type:recorder.mimeType}));video.load();
  return true;
})()'''


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    checks=[]
    pixels={}
    def passed(name):
        checks.append(name);print('PASS '+name,flush=True)
    with tempfile.TemporaryDirectory(prefix='suv-poster-test-') as temp:
        deck=Path(temp)/'poster.html';deck.write_text(fixture())
        with ChromeSession(width=1280,height=850) as c:
            c.call('Network.emulateNetworkConditions',dict(offline=True,latency=0,downloadThroughput=0,uploadThroughput=0))
            c.navigate(deck.as_uri());c.evaluate(CREATE_VIDEO)
            wait_for(c,'document.querySelector("#poster-video").readyState>=2')
            assert c.evaluate('(()=>{const v=document.querySelector("#poster-video");return v.paused&&v.currentTime===0&&v.played.length===0})()')
            source=targets(c)[0]['id']
            c.key('n');wait_for(c,'!!window.SUVPresenter')
            c.evaluate('window.posterNotes=SUVPresent.openNotes();true')
            wait_for(c,'!!posterNotes.document.querySelector("#notes")')
            p=attach(c,next(t for t in targets(c) if t['id']!=source))
            wait_for(p,"[...document.querySelectorAll('iframe')].every(f=>f.contentDocument?.readyState==='complete' && f.contentDocument.querySelector('.slide'))")
            next_image="document.querySelector('#next-preview').contentDocument?.querySelector('img[alt=\"Media preview\"]')"
            wait_for(p,'!!'+next_image+' && '+next_image+'.complete && '+next_image+'.naturalWidth>0')
            pixels['nextInitialRed']=screenshot_color_count(p,'img[alt="Media preview"]',out/'next_initial_poster.png',0,'next-preview')
            assert pixels['nextInitialRed']>100,pixels
            passed('Preloaded, unplayed video uses the poster in the static next preview')

            p.key('ArrowRight');wait_for(c,'SUVPresent.currentIndex()===1')
            wait_for(p,'!!document.querySelector("#current-preview").contentDocument?.querySelector("canvas#poster-video")')
            red="(()=>{const x=document.querySelector('#current-preview').contentDocument.querySelector('canvas#poster-video');const p=x.getContext('2d').getImageData(10,10,1,1).data;return p[0]>240&&p[1]<15&&p[2]<15})()"
            blue=red.replace('p[0]>240&&p[1]<15&&p[2]<15','p[2]>240&&p[0]<15&&p[1]<15')
            wait_for(p,red)
            pixels['audienceInitialRed']=screenshot_color_count(c,'#poster-video',out/'audience_initial_poster.png',0,None)
            pixels['currentInitialRed']=screenshot_color_count(p,'#poster-video',out/'current_initial_poster.png',0)
            assert pixels['audienceInitialRed']>100 and pixels['currentInitialRed']>100,pixels
            passed('Current preview visibly matches the audience poster before first playback')

            p.key('p');wait_for(c,'!document.querySelector("#poster-video").paused')
            wait_for(p,blue)
            pixels['audiencePlayingBlue']=screenshot_color_count(c,'#poster-video',out/'audience_playing_frame.png',2,None)
            pixels['currentPlayingBlue']=screenshot_color_count(p,'#poster-video',out/'current_playing_frame.png',2)
            assert pixels['audiencePlayingBlue']>100 and pixels['currentPlayingBlue']>100,pixels
            p.key('p');wait_for(c,'document.querySelector("#poster-video").paused')
            wait_for(p,blue)
            p.key('r');wait_for(c,'document.querySelector("#poster-video").paused && document.querySelector("#poster-video").currentTime===0 && !document.querySelector("#poster-video").seeking')
            wait_for(p,blue)
            pixels['audienceResetBlue']=screenshot_color_count(c,'#poster-video',out/'audience_reset_frame.png',2,None)
            pixels['currentResetBlue']=screenshot_color_count(p,'#poster-video',out/'current_reset_frame.png',2)
            assert pixels['audienceResetBlue']>100 and pixels['currentResetBlue']>100,pixels
            passed('First playback shows video frames; pause and reset to zero do not restore the poster')

            c.evaluate('document.querySelector("#poster-video").load()')
            wait_for(c,'document.querySelector("#poster-video").readyState>=2 && document.querySelector("#poster-video").paused')
            wait_for(p,red)
            pixels['audienceReloadRed']=screenshot_color_count(c,'#poster-video',out/'audience_reloaded_poster.png',0,None)
            pixels['currentReloadRed']=screenshot_color_count(p,'#poster-video',out/'current_reloaded_poster.png',0)
            assert pixels['audienceReloadRed']>100 and pixels['currentReloadRed']>100,pixels
            p.key('ArrowLeft');wait_for(c,'SUVPresent.currentIndex()===0')
            wait_for(p,"[...document.querySelectorAll('iframe')].every(f=>f.contentDocument?.readyState==='complete' && f.contentDocument.querySelector('.slide'))")
            wait_for(p,'!!'+next_image+' && '+next_image+'.complete && '+next_image+'.naturalWidth>0')
            pixels['nextReloadRed']=screenshot_color_count(p,'img[alt="Media preview"]',out/'next_reloaded_poster.png',0,'next-preview')
            assert pixels['nextReloadRed']>100,pixels
            passed('Reloading the resource restores the poster in the audience and both previews')
            errors=[e for e in c.events+p.events if e.get('method')=='Runtime.exceptionThrown']
            assert not errors,errors
            p.ws.close()
    report={'result':'PASS','passed':len(checks),'checks':checks,'visibleColorPixels':pixels,
        'transport':'offline file://','browser':'headless Chrome','fixture':'Local blue WebM recorded in browser; red poster',
        'browserSecurity':'default; no allow-file-access-from-files or disable-web-security'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.output.resolve()),ensure_ascii=False,indent=2))
