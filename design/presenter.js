/* Separate presenter view. Loaded by present.js only after a user opens notes.
 * The popup starts at about:blank and inherits the opener's origin, including file://.
 * Sandboxed previews run no slide scripts. The current preview mirrors source
 * canvas/video frames and DOM; the next preview remains a still image.
 * Layout follows a slide-show presenter view: current slide left, next slide and script right.
 */
(function () {
  'use strict';

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  // Dark application chrome; slide previews keep the deck's own colours.
  var CSS = [
    ':root { color-scheme: dark; }',
    '* { box-sizing: border-box; }',
    'html, body { margin: 0; height: 100%; }',
    'body { background: #0b1120; color: #e2e8f0; font-family: "Atkinson Hyperlegible", "Noto Sans KR", system-ui, sans-serif; display: flex; flex-direction: column; }',
    '[hidden] { display: none !important; }',
    'button, input { font: inherit; font-size: 14px; }',
    'button { border: 1px solid #334155; background: #1e293b; color: #e2e8f0; padding: 7px 12px; border-radius: 7px; cursor: pointer; white-space: nowrap; }',
    'button:hover:not(:disabled) { background: #273449; border-color: #60a5fa; }',
    'button:focus-visible, input:focus-visible { outline: 2px solid #93c5fd; outline-offset: 2px; }',
    'button:disabled { opacity: .4; cursor: default; }',
    'header { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 8px 16px; padding: 8px 16px; background: #111827; border-bottom: 1px solid #1f2937; }',
    '.brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; }',
    'h1 { margin: 0; font-size: 16px; color: #f8fafc; white-space: nowrap; }',
    '#connection { color: #94a3b8; font-size: 13px; }',
    '#connection::before { content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 6px; border-radius: 50%; background: #22c55e; }',
    '#connection.offline { color: #fca5a5; }',
    '#connection.offline::before { background: #f87171; }',
    '.clock, .script-tools, .controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }',
    '.script-tools { justify-self: end; }',
    '.clock-label, .tool-label, #font-size, label[for="jump"], #jump-total { font-size: 12px; color: #94a3b8; }',
    '#elapsed { min-width: 72px; font-size: 24px; font-weight: 700; color: #f8fafc; font-variant-numeric: tabular-nums; text-align: center; }',
    '#font-size { min-width: 34px; text-align: center; }',
    '#reading-toggle[aria-pressed="true"] { background: #1d4ed8; border-color: #93c5fd; color: #fff; }',
    '#disconnect-message { margin: 0; padding: 10px 16px; background: #450a0a; color: #fecaca; font-size: 14px; line-height: 1.5; border-bottom: 1px solid #7f1d1d; }',
    'main { flex: 1; min-height: 0; overflow: hidden; display: grid; gap: 14px 16px; padding: 14px 16px; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); grid-template-rows: auto minmax(0, 1fr) auto; grid-template-areas: "current next" "current notes" "help notes"; }',
    'main.reading { grid-template-columns: minmax(0, 9fr) minmax(0, 16fr); grid-template-rows: auto auto minmax(0, 1fr) auto; grid-template-areas: "current notes" "next notes" ". notes" "help notes"; }',
    '.current-pane { grid-area: current; min-width: 0; min-height: 0; overflow: hidden; }',
    '.next-pane { grid-area: next; min-width: 0; display: grid; grid-template-columns: 54% minmax(0, 1fr); gap: 12px; align-items: start; }',
    '.next-pane .preview-box { order: -1; }',
    '.preview-heading { margin: 0 0 8px; color: #94a3b8; font-size: 12px; font-weight: 700; }',
    '.preview-box { position: relative; width: 100%; aspect-ratio: 16/9; background: #020617; border: 1px solid #334155; border-radius: 6px; overflow: hidden; }',
    '.preview-box iframe { border: 0; position: absolute; left: 0; top: 0; transform-origin: 0 0; pointer-events: none; background: #fff; }',
    '.slide-caption { display: flex; align-items: baseline; gap: 10px; margin-top: 10px; min-width: 0; }',
    '#slide-count { color: #93c5fd; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }',
    '#note-title { margin: 0; color: #f8fafc; font-size: 18px; font-weight: 700; line-height: 1.3; overflow-wrap: anywhere; }',
    '.preview-label { margin: 0; color: #cbd5e1; font-size: 15px; line-height: 1.4; overflow-wrap: anywhere; }',
    '.help { grid-area: help; align-self: end; margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.5; word-break: keep-all; }',
    '.notes-pane { grid-area: notes; min-width: 0; min-height: 0; display: flex; flex-direction: column; background: #111827; border: 1px solid #1f2937; border-radius: 10px; }',
    '.notes-tabs { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #1f2937; flex: none; }',
    '.notes-tabs [aria-selected="true"] { background: #1d4ed8; border-color: #60a5fa; color: #fff; }',
    '.notes-tabs .tab-hint { margin-left: auto; color: #94a3b8; font-size: 12px; }',
    '#notes { flex: 1; min-height: 0; overflow-y: auto; padding: 20px 24px 32px; border-radius: 10px; color: #f8fafc; font-size: 32px; line-height: 1.5; word-break: keep-all; overflow-wrap: anywhere; }',
    '#notes:focus-visible { outline: 2px solid rgba(147, 197, 253, .55); outline-offset: -2px; }',
    '#notes p { margin: 0 0 .7em; }',
    '#notes p:last-child { margin-bottom: 0; }',
    '#notes ul, #notes ol { padding-left: 1.25em; }',
    '#notes pre { white-space: pre-wrap; }',
    '#notes.empty { color: #94a3b8; font-size: 24px; }',
    '#notes strong { color: #93c5fd; }',
    '#qa-panel { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }',
    '.qa-tools { padding: 10px 16px; display: grid; gap: 8px; flex: none; border-bottom: 1px solid #334155; }',
    '.qa-search-row { display: flex; align-items: center; gap: 10px; min-width: 0; }',
    '#qa-back { flex: none; color: #dbeafe; border-color: #60a5fa; }',
    '#qa-search { box-sizing: border-box; width: 100%; min-width: 0; padding: 9px 11px; border: 1px solid #475569; border-radius: 7px; background: #0b1120; color: #f8fafc; font-size: 16px; }',
    '.qa-filter { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px 12px; color: #94a3b8; font-size: 13px; }',
    '.qa-filter label { display: flex; align-items: center; gap: 5px; }',
    '#qa-current-only { accent-color: #60a5fa; }',
    '#qa-categories { display: flex; flex-wrap: wrap; gap: 5px; }',
    '#qa-categories button { padding: 5px 10px; font-size: 13px; white-space: normal; overflow-wrap: anywhere; }',
    '#qa-categories button[aria-pressed="true"] { background: #1d4ed8; border-color: #60a5fa; color: #fff; }',
    '#qa-slide-context { min-width: 0; max-width: 45%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #94a3b8; font-size: 12px; margin-left: 8px; }',
    '.qa-workspace { flex: 1; min-height: 0; min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); overflow: hidden; }',
    '#qa-list { min-height: 0; min-width: 0; overflow-y: auto; list-style: none; padding: 12px 16px 18px; margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-content: start; align-items: start; gap: 14px 18px; scrollbar-gutter: stable; }',
    '.qa-group { min-width: 0; }',
    '.qa-group h3 { margin: 0 0 7px; padding: 0 2px; color: #93c5fd; font-size: 14px; line-height: 1.4; overflow-wrap: anywhere; }',
    '.qa-group ul { list-style: none; padding: 0; margin: 0; }',
    '.qa-group li + li { margin-top: 4px; }',
    '#qa-list button { width: 100%; text-align: left; white-space: normal; overflow-wrap: anywhere; word-break: keep-all; line-height: 1.4; font-size: 15px; padding: 7px 10px; }',
    '#qa-list button[aria-pressed="true"] { border-color: #60a5fa; background: #172e52; color: #dbeafe; }',
    '#qa-empty { padding: 12px 16px; margin: 0; color: #94a3b8; font-size: 14px; line-height: 1.5; }',
    '#qa-answer-panel { min-height: 0; min-width: 0; overflow-y: auto; padding: 18px 24px 28px; border-left: 1px solid #334155; overflow-wrap: anywhere; word-break: keep-all; }',
    '.qa-detail .qa-workspace { grid-template-columns: minmax(280px, 2fr) minmax(0, 3fr); }',
    '.qa-detail #qa-list { grid-template-columns: minmax(0, 1fr); }',
    '#qa-answer-panel:focus-visible { outline: 2px solid rgba(147,197,253,.55); outline-offset: -2px; }',
    '#qa-question { margin: 0 0 5px; font-size: 18px; line-height: 1.4; color: #93c5fd; }',
    '#qa-question-en { margin: 0 0 14px; font-size: 15px; line-height: 1.45; color: #cbd5e1; }',
    '.qa-answer-label { margin: 0 0 7px; font-size: 12px; color: #94a3b8; }',
    '#qa-answer { margin: 0; font-size: 32px; line-height: 1.5; color: #f8fafc; white-space: pre-line; }',
    '#qa-answer.empty { font-size: 20px !important; color: #94a3b8; }',
    '#qa-note { margin: 18px 0 0; padding: 12px; border-left: 3px solid #64748b; background: #1e293b; color: #cbd5e1; font-size: 15px; line-height: 1.6; white-space: pre-line; }',
    'footer { display: flex; align-items: center; justify-content: space-between; gap: 8px 16px; flex-wrap: wrap; padding: 8px 16px; background: #111827; border-top: 1px solid #1f2937; }',
    '.nav { min-width: 92px; font-weight: 700; }',
    '#next { color: #fff; background: #2563eb; border-color: #2563eb; }',
    '#next:hover:not(:disabled) { background: #1d4ed8; border-color: #93c5fd; }',
    '#jump { width: 64px; padding: 6px 8px; border: 1px solid #334155; border-radius: 6px; background: #0b1120; color: #f8fafc; }',
    '#blank[aria-pressed="true"] { background: #fbbf24; border-color: #fbbf24; color: #0f172a; }',
    // Narrow windows always give the script the wide column.
    '@media (max-width: 900px) { header { display: flex; flex-wrap: wrap; } .script-tools { margin-left: auto; } #reading-toggle, .help { display: none; } main, main.reading { grid-template-columns: minmax(0, 9fr) minmax(0, 16fr); grid-template-rows: auto auto minmax(0, 1fr); grid-template-areas: "current notes" "next notes" ". notes"; gap: 10px 12px; padding: 10px 12px; } .next-pane { grid-template-columns: minmax(0, 1fr); gap: 6px; } #notes { padding: 16px 18px 24px; } }',
    '@media (max-width: 620px) { main, main.reading { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); grid-template-areas: "notes"; } .current-pane, .next-pane { display: none; } #notes { padding: 14px; } }',
    '@media (max-height: 760px) { .qa-tools { padding-top: 8px; } #qa-answer-panel { padding: 12px 16px 20px; } }',
    // Keep the existing live iframe beside the Q&A tools, with the question grid
    // across the full width below. display:contents changes layout, not iframe ownership.
    'main.qa-mode, main.qa-mode.reading { grid-template-columns: clamp(220px, 25vw, 340px) minmax(0, 1fr); grid-template-rows: auto auto auto minmax(0, 1fr); grid-template-areas: "current qa-tabs" "current qa-tools" "qa-empty qa-empty" "qa-body qa-body"; gap: 8px 16px; }',
    'main.qa-mode .current-pane { display: block; align-self: start; }',
    'main.qa-mode .current-pane .preview-heading { margin-bottom: 5px; }',
    'main.qa-mode .slide-caption { margin-top: 5px; gap: 8px; }',
    'main.qa-mode #slide-count { font-size: 12px; }',
    'main.qa-mode #note-title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
    'main.qa-mode .next-pane, main.qa-mode .help { display: none; }',
    'main.qa-mode .notes-pane, main.qa-mode #qa-panel:not([hidden]) { display: contents; }',
    'main.qa-mode .notes-tabs { grid-area: qa-tabs; align-self: start; background: #111827; border: 1px solid #1f2937; border-radius: 8px; }',
    'main.qa-mode .qa-tools { grid-area: qa-tools; align-self: start; min-width: 0; background: #111827; border: 1px solid #1f2937; border-radius: 8px; }',
    'main.qa-mode #qa-empty { grid-area: qa-empty; }',
    'main.qa-mode .qa-workspace { grid-area: qa-body; background: #111827; border: 1px solid #1f2937; border-radius: 10px; }',
    '@media (min-width: 1450px) { #qa-panel:not(.qa-detail) #qa-list { grid-template-columns: repeat(3, minmax(0, 1fr)); } }',
    '@media (max-width: 900px) { main.qa-mode, main.qa-mode.reading { grid-template-columns: clamp(160px, 28vw, 240px) minmax(0, 1fr); gap: 6px 12px; } body.qa-active header { flex-wrap: nowrap; gap: 10px; } body.qa-active #connection, body.qa-active .clock-label, body.qa-active .tool-label, body.qa-active #font-size { display: none; } body.qa-active .clock { margin-left: auto; flex-wrap: nowrap; } body.qa-active .script-tools { flex-wrap: nowrap; margin-left: 0; } body.qa-active footer #display-setup, body.qa-active footer #media-toggle, body.qa-active footer #media-reset { display: none; } }',
    '@media (max-width: 800px) { .qa-detail .qa-workspace { grid-template-columns: minmax(0, 1fr); } .qa-detail #qa-list { display: none; } #qa-answer-panel { border-left: 0; } .qa-tools { padding: 8px 12px; } #qa-list { padding: 10px 12px 14px; gap: 12px; } #qa-list button { font-size: 14px; line-height: 1.35; padding: 5px 9px; } #qa-slide-context { display: none; } }',
    '@media (max-width: 620px) { body.qa-active #timer-toggle, body.qa-active #timer-reset { display: none; } body.qa-active .script-tools { margin-left: auto; } }',
    '@media (max-width: 620px) { #qa-list { grid-template-columns: minmax(0, 1fr); } .notes-tabs .tab-hint { font-size: 11px; } main.qa-mode .notes-tabs .tab-hint { display: none; } #qa-categories { max-height: 74px; overflow-y: auto; } #qa-back { padding: 7px 8px; } }'
  ].join('\n');

  function mount(win, api) {
    if (win.closed) return;
    if (win.__SUVPresenterCleanup) win.__SUVPresenterCleanup();
    var doc = win.document;
    doc.open();
    doc.write('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>발표자 노트 · SUV Lab</title></head><body></body></html>');
    doc.close();
    var style = doc.createElement('style'); style.textContent = CSS; doc.head.appendChild(style);
    doc.body.innerHTML =
      '<header><div class="brand"><h1>발표자 노트</h1><div id="connection" role="status">슬라이드 창에 연결됨</div></div>' +
      '<div class="clock"><span class="clock-label">경과 시간</span><output id="elapsed">00:00</output><button id="timer-toggle" type="button">타이머 시작</button><button id="timer-reset" type="button">타이머 초기화</button></div>' +
      '<div class="script-tools"><span class="tool-label">읽기 글씨</span><button id="font-smaller" type="button" aria-label="대본과 답변 글씨 줄이기">A−</button><span id="font-size">32px</span><button id="font-larger" type="button" aria-label="대본과 답변 글씨 키우기">A＋</button>' +
      '<button id="reading-toggle" type="button" aria-pressed="false">대본 중심</button></div></header>' +
      '<p id="disconnect-message" role="alert" hidden>슬라이드 창 연결이 끊겼습니다. 슬라이드 창에서 N을 눌러 새 발표자 창을 여세요.</p>' +
      '<main><section class="current-pane" aria-label="현재 슬라이드"><h2 class="preview-heading">현재 슬라이드 · 실시간 미리보기</h2>' +
      '<div class="preview-box"><iframe id="current-preview" title="현재 슬라이드 미리보기" sandbox="allow-same-origin allow-scripts" tabindex="-1"></iframe></div>' +
      '<p id="current-label" hidden></p><div class="slide-caption"><span id="slide-count"></span><p id="note-title"></p></div></section>' +
      '<section class="next-pane" aria-label="다음 슬라이드"><div><h2 class="preview-heading">다음 슬라이드 · 정지 미리보기</h2><p id="next-label" class="preview-label"></p></div>' +
      '<div class="preview-box"><iframe id="next-preview" title="다음 슬라이드 미리보기" sandbox="allow-same-origin" tabindex="-1"></iframe></div></section>' +
      '<section class="notes-pane" aria-label="발표자 전용 메모"><div class="notes-tabs" role="tablist" aria-label="발표자 메모 전환">' +
      '<button id="notes-tab" type="button" role="tab" aria-controls="notes" aria-selected="true">대본</button>' +
      '<button id="qa-tab" type="button" role="tab" aria-controls="qa-panel" aria-selected="false" tabindex="-1">Q&amp;A</button><span id="qa-slide-context" hidden></span><span id="qa-hint" class="tab-hint">Q: 전환 · Esc: 대본</span></div>' +
      '<div id="notes" tabindex="0" role="tabpanel" aria-labelledby="notes-tab"></div>' +
      '<div id="qa-panel" role="tabpanel" aria-labelledby="qa-tab" hidden><div class="qa-tools">' +
      '<div class="qa-search-row"><button id="qa-back" type="button" hidden>← 질문 목록</button><input id="qa-search" type="search" placeholder="질문·키워드 검색" aria-label="질의응답 검색" autocomplete="off"></div>' +
      '<div id="qa-categories" aria-label="질문 분류"></div>' +
      '<div class="qa-filter"><label><input id="qa-current-only" type="checkbox">현재 장 + 공통</label><span id="qa-count" role="status"></span></div></div>' +
      '<p id="qa-empty" hidden></p><div class="qa-workspace"><ul id="qa-list" aria-label="준비한 질문"></ul>' +
      '<div id="qa-answer-panel" tabindex="0" aria-label="선택한 질문의 답변" hidden><h2 id="qa-question"></h2><p id="qa-question-en"></p>' +
      '<p id="qa-answer-label" class="qa-answer-label">영어 답변 · 그대로 읽기</p><p id="qa-answer"></p><p id="qa-note"></p></div></div></div></section>' +
      '<p class="help">화면 설정에서 청중 화면과 발표자 화면을 선택할 수 있습니다. 수동 배치는 슬라이드 창을 외부 화면에 옮긴 뒤 F를 누르세요. 현재 미리보기는 청중 화면의 재생 상태를 반영합니다.</p></main>' +
      '<footer><div class="controls"><button id="prev" class="nav" type="button">← 이전</button><button id="next" class="nav" type="button">다음 →</button>' +
      '<label for="jump">장 이동</label><input id="jump" type="number" min="1" step="1" aria-label="이동할 슬라이드 번호"><span id="jump-total"></span></div>' +
      '<div class="controls"><button id="display-setup" type="button">화면 설정</button><button id="media-toggle" type="button">재생 / 일시정지 (P)</button><button id="media-reset" type="button">처음으로 (R)</button><button id="blank" type="button" aria-pressed="false">청중 화면 끄기 (B)</button></div></footer>';

    function el(id) { return doc.getElementById(id); }
    var layout = doc.querySelector('main');
    var notes = el('notes');
    var current = null;
    var lastNotes = null;
    var fontSize = 32;
    var reading = false;
    var qaMode = false, qaSelected = null, qaCards = [], qaDetail = false, qaCategory = '';
    var qaBrowseScroll = 0, qaDetailListScroll = 0;
    var qaScroll = 0, qaLayoutChanged = false;
    if (api.getQA) {
      try { qaCards = api.getQA() || []; } catch (error) { qaCards = []; }
    }
    if (!Array.isArray(qaCards)) qaCards = [];
    qaCards = qaCards.map(function (card, index) {
      function plain(value) { return typeof value === 'string' ? value : ''; }
      return {id: plain(card.id) || String(index), question: plain(card.question), questionEN: plain(card.questionEN),
        answer: plain(card.answer), notes: plain(card.notes), keywords: plain(card.keywords), category: plain(card.category).trim() || '기타',
        pages: Array.isArray(card.pages) ? card.pages.filter(function (page) { return Number.isInteger(page) && page > 0; }) : []};
    });
    var scrollPositions = {};
    var scrollRatios = {};
    var timerRunning = false, elapsed = 0, startedAt = 0;
    var disconnected = false, destroyed = false;
    var interval, unsubscribe, detachAnimationWindow;
    var liveMirror = null, liveFrame = 0, previewGeneration = 0;

    function timerValue() { return elapsed + (timerRunning ? win.performance.now() - startedAt : 0); }
    function paintTimer() {
      var seconds = Math.floor(timerValue() / 1000);
      el('elapsed').textContent = String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0');
      el('timer-toggle').textContent = timerRunning ? '타이머 일시정지' : '타이머 시작';
    }
    function stopTimer() {
      if (timerRunning) { elapsed = timerValue(); timerRunning = false; }
      paintTimer();
    }
    function disconnect() {
      if (disconnected || destroyed) return;
      disconnected = true; stopTimer(); stopLivePreview();
      el('connection').textContent = '슬라이드 창 연결 끊김';
      el('connection').className = 'offline';
      el('disconnect-message').hidden = false;
      [].forEach.call(doc.querySelectorAll('button, input'), function (control) { control.disabled = true; });
    }
    function connected() {
      if (disconnected || destroyed) return false;
      try { if (api.connected()) return true; } catch (e) { /* Opener was closed/navigated. */ }
      disconnect(); return false;
    }
    function action(fn) {
      if (!connected()) return;
      try { fn(); } catch (e) { if (!api.connected()) disconnect(); else throw e; }
    }
    function sizePreview(frame) {
      var width = Number(frame.dataset.width) || 1920;
      var height = Number(frame.dataset.height) || 1080;
      frame.style.width = width + 'px'; frame.style.height = height + 'px';
      frame.style.transform = 'scale(' + (frame.parentNode.clientWidth / width) + ')';
    }
    function stopLivePreview() {
      previewGeneration++;
      if (liveFrame) win.cancelAnimationFrame(liveFrame);
      liveFrame = 0;
      if (liveMirror) liveMirror.close();
      liveMirror = null;
      el('current-preview').onload = null;
    }
    function renderPreview(frame, label, index, live) {
      if (live) stopLivePreview();
      var generation = previewGeneration;
      var data = api.preview(index, !!live);
      if (live && data && api.mirrorPreview) {
        frame.onload = function () {
          if (destroyed || disconnected || generation !== previewGeneration || !current || current.index !== index) return;
          var previewDocument = frame.contentDocument;
          // A late load from the previous srcdoc must never bind the wrong slide.
          if (!previewDocument || !previewDocument.body || previewDocument.body.getAttribute('data-suv-preview-index') !== String(index)) return;
          var slide = previewDocument.querySelector('.slide');
          if (!slide) return;
          if (liveFrame) win.cancelAnimationFrame(liveFrame);
          if (liveMirror) liveMirror.close();
          liveMirror = api.mirrorPreview(index, slide);
          if (!liveMirror) return;
          liveMirror.update();
          var last = 0;
          function tick(now) {
            liveFrame = 0;
            if (destroyed || disconnected || generation !== previewGeneration || !connected()) return;
            // Canvas pixels are copied directly, without PNG encoding, duplicate
            // playback clocks, audio, or iframe reloads. Limit work to 30 fps.
            if (now - last >= 1000 / 30) {
              last = now - ((now - last) % (1000 / 30));
              if (!liveMirror || !liveMirror.update()) { stopLivePreview(); return; }
            }
            liveFrame = win.requestAnimationFrame(tick);
          }
          liveFrame = win.requestAnimationFrame(tick);
        };
      }
      if (!data) {
        frame.srcdoc = '<!doctype html><html lang="ko"><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;font:600 34px system-ui,sans-serif;color:#94a3b8;background:#111827">다음 슬라이드가 없습니다.</body></html>';
        frame.dataset.width = '640'; frame.dataset.height = '360';
        label.textContent = '마지막 슬라이드'; sizePreview(frame); return;
      }
      frame.dataset.width = String(data.width); frame.dataset.height = String(data.height);
      var reset = 'html,body{width:' + data.width + 'px;height:' + data.height + 'px;margin:0!important;padding:0!important;overflow:hidden;background:white}' +
        'deck-stage{display:block!important;margin:0!important;padding:0!important}' +
        '.slide{position:relative!important;left:auto!important;top:auto!important;width:' + data.width + 'px!important;height:' + data.height + 'px!important;margin:0!important;transform:none!important;box-shadow:none!important}' +
        '.speaker-notes,[data-speaker-notes],.speaker-qa,[data-speaker-qa],.present-btn,.present-status{display:none!important}' +
        '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
      // Canvas displays its fallback instead of its bitmap when sandbox scripting
      // is disabled. Enable that browser capability only for the current frame,
      // while CSP still forbids every script/event handler, plugin and child frame.
      // Source scripts are also removed before constructing or patching the clone.
      var policy = "script-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'";
      frame.srcdoc = '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + escapeHTML(policy) + '"><base href="' + escapeHTML(data.baseURL) + '">' + data.styles + '<style>' + reset + '</style></head><body data-suv-preview-index="' + index + '">' + data.html + '</body></html>';
      label.textContent = data.title; sizePreview(frame);
    }
    function focusReadingPane() {
      (qaMode ? (qaDetail ? el('qa-answer-panel') : el('qa-search')) : notes).focus({preventScroll: true});
    }
    function setQADetail(show, moveFocus) {
      show = !!show && !!qaSelected;
      if (qaDetail !== show) {
        if (show) qaBrowseScroll = el('qa-list').scrollTop;
        else qaDetailListScroll = el('qa-list').scrollTop;
        qaDetail = show;
        el('qa-panel').classList.toggle('qa-detail', show);
        el('qa-answer-panel').hidden = !show;
        el('qa-back').hidden = !show;
        el('qa-hint').textContent = show ? 'Q: 대본 · Esc: 질문 목록' : 'Q: 전환 · Esc: 대본';
        el('qa-list').scrollTop = show ? qaDetailListScroll : qaBrowseScroll;
      }
      if (moveFocus) {
        if (show) el('qa-answer-panel').focus({preventScroll: true});
        else {
          var selected = [].find.call(el('qa-list').querySelectorAll('button'), function (button) {
            return qaSelected && button.dataset.qaId === qaSelected.id;
          });
          (selected || el('qa-search')).focus({preventScroll: true});
        }
      }
    }
    function renderQAAnswer(card) {
      qaSelected = card;
      el('qa-question').textContent = card ? (card.question || card.questionEN) : '질문을 선택하세요.';
      el('qa-question-en').textContent = card ? card.questionEN : '';
      el('qa-question-en').hidden = !card || !card.questionEN || card.questionEN === card.question;
      el('qa-answer-label').hidden = !card;
      el('qa-answer').textContent = card ? card.answer : '질문을 고르면 준비한 답변을 여기에서 읽을 수 있습니다.';
      el('qa-answer').classList.toggle('empty', !card);
      el('qa-note').textContent = card ? card.notes : '';
      el('qa-note').hidden = !card || !card.notes;
      el('qa-answer-panel').scrollTop = 0;
      qaScroll = 0;
    }
    function renderQACategories(matches) {
      var categories = [];
      qaCards.forEach(function (card) { if (categories.indexOf(card.category) < 0) categories.push(card.category); });
      var fragment = doc.createDocumentFragment();
      [''].concat(categories).forEach(function (category) {
        var button = doc.createElement('button');
        button.type = 'button'; button.dataset.qaCategory = category;
        var count = category ? matches.filter(function (card) { return card.category === category; }).length : matches.length;
        button.textContent = (category || '전체') + ' ' + count;
        button.setAttribute('aria-pressed', String(category === qaCategory));
        button.onclick = function () {
          if (!connected()) return;
          qaCategory = category; setQADetail(false, false); renderQAList(true);
          [].find.call(el('qa-categories').querySelectorAll('button'), function (next) {
            return next.dataset.qaCategory === category;
          }).focus({preventScroll: true});
        };
        fragment.appendChild(button);
      });
      el('qa-categories').replaceChildren(fragment);
    }
    function renderQAList(resetScroll) {
      var previousScroll = resetScroll ? 0 : el('qa-list').scrollTop;
      var query = el('qa-search').value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      var page = current ? current.index + 1 : 0;
      var matches = qaCards.filter(function (card) {
        var text = [card.question, card.questionEN, card.answer, card.notes, card.keywords, card.category].join(' ').toLocaleLowerCase();
        return (!el('qa-current-only').checked || !card.pages.length || card.pages.indexOf(page) >= 0) &&
          query.every(function (term) { return text.indexOf(term) >= 0; });
      });
      var found = matches.filter(function (card) { return !qaCategory || card.category === qaCategory; });
      var fragment = doc.createDocumentFragment();
      var groups = [];
      found.forEach(function (card) {
        var group = groups.find(function (candidate) { return candidate.category === card.category; });
        if (!group) { group = {category: card.category, cards: []}; groups.push(group); }
        group.cards.push(card);
      });
      groups.forEach(function (group) {
        // Short groups keep the overview balanced and let several topics fit on screen.
        var chunkSize = Math.ceil(group.cards.length / Math.ceil(group.cards.length / 6));
        for (var offset = 0; offset < group.cards.length; offset += chunkSize) {
          var section = doc.createElement('li'), heading = doc.createElement('h3'), list = doc.createElement('ul');
          section.className = 'qa-group';
          heading.textContent = group.category + (offset ? ' · 계속' : '');
          section.appendChild(heading); section.appendChild(list);
          group.cards.slice(offset, offset + chunkSize).forEach(function (card) {
            var item = doc.createElement('li'), button = doc.createElement('button');
            button.type = 'button'; button.dataset.qaId = card.id;
            button.textContent = card.question || card.questionEN;
            button.title = card.questionEN;
            button.setAttribute('aria-pressed', String(card === qaSelected));
            button.onclick = function () {
              if (!connected()) return;
              renderQAAnswer(card);
              // Keep the same list nodes so keyboard focus and scroll remain stable.
              [].forEach.call(el('qa-list').querySelectorAll('button'), function (other) {
                other.setAttribute('aria-pressed', String(other === button));
              });
              setQADetail(true, true);
              if (win.innerWidth > 800) button.scrollIntoView({block: 'nearest'});
            };
            item.appendChild(button); list.appendChild(item);
          });
          fragment.appendChild(section);
        }
      });
      el('qa-list').replaceChildren(fragment);
      el('qa-list').scrollTop = previousScroll;
      renderQACategories(matches);
      el('qa-count').textContent = found.length + ' / ' + qaCards.length + '개 질문';
      el('qa-empty').hidden = !!found.length;
      el('qa-empty').textContent = qaCards.length ? '검색 결과가 없습니다. 검색어, 분류 또는 현재 장 필터를 바꿔 주세요.' : '등록된 Q&A가 없습니다.';
      // Deliberately keep the selected answer when a search or slide change
      // filters its card out. Only choosing another question changes the answer.
    }
    function setPanel(showQA, moveFocus) {
      if (qaMode !== showQA) {
        if (showQA) {
          if (current) {
            scrollPositions[current.index] = notes.scrollTop;
            var range = notes.scrollHeight - notes.clientHeight;
            if (range > 0) scrollRatios[current.index] = notes.scrollTop / range;
          }
          qaLayoutChanged = false;
        } else {
          qaScroll = el('qa-answer-panel').scrollTop;
          if (qaDetail) qaDetailListScroll = el('qa-list').scrollTop;
          else qaBrowseScroll = el('qa-list').scrollTop;
        }
        qaMode = showQA;
        layout.classList.toggle('qa-mode', qaMode);
        doc.body.classList.toggle('qa-active', qaMode);
        notes.hidden = qaMode; el('qa-panel').hidden = !qaMode;
        el('qa-slide-context').hidden = !qaMode;
        el('reading-toggle').hidden = qaMode;
        el('notes-tab').setAttribute('aria-selected', String(!qaMode));
        el('qa-tab').setAttribute('aria-selected', String(qaMode));
        el('notes-tab').tabIndex = qaMode ? -1 : 0;
        el('qa-tab').tabIndex = qaMode ? 0 : -1;
        if (qaMode) {
          resize();
          renderQAList(); el('qa-answer-panel').scrollTop = qaScroll;
          el('qa-list').scrollTop = qaDetail ? qaDetailListScroll : qaBrowseScroll;
        } else if (current) {
          resize();
          notes.scrollTop = qaLayoutChanged ? (scrollRatios[current.index] || 0) * (notes.scrollHeight - notes.clientHeight) : (scrollPositions[current.index] || 0);
        }
      }
      if (moveFocus) {
        if (qaMode) el('qa-search').focus({preventScroll: true});
        else notes.focus({preventScroll: true});
      }
    }
    function render(state) {
      if (destroyed) return;
      if (!state.connected) { disconnect(); return; }
      if (!connected()) return;
      var changed = !current || state.index !== current.index;
      if (changed && current && !qaMode) scrollPositions[current.index] = notes.scrollTop;
      if (changed || state.notesHTML !== lastNotes) {
        var previousScroll = notes.scrollTop;
        notes.classList.toggle('empty', !state.notesHTML);
        if (state.notesHTML) notes.innerHTML = state.notesHTML;
        else notes.textContent = '이 슬라이드에는 발표자 노트가 없습니다.';
        notes.scrollTop = changed ? (scrollPositions[state.index] || 0) : previousScroll;
        lastNotes = state.notesHTML;
      }
      current = state;
      el('slide-count').textContent = (state.index + 1) + ' / ' + state.count;
      el('qa-slide-context').textContent = '청중 화면 ' + (state.index + 1) + ' / ' + state.count + ' · ' + state.title;
      el('note-title').textContent = state.title;
      el('prev').disabled = state.index <= 0;
      el('next').disabled = state.index >= state.count - 1;
      el('jump').max = String(state.count); el('jump').value = String(state.index + 1);
      el('jump-total').textContent = '/ ' + state.count;
      el('blank').textContent = state.blank ? '청중 화면 켜기 (B)' : '청중 화면 끄기 (B)';
      el('blank').setAttribute('aria-pressed', String(state.blank));
      el('connection').textContent = state.blank ? '연결됨 · 청중 화면 꺼짐' : '슬라이드 창에 연결됨';
      if (changed) {
        renderPreview(el('current-preview'), el('current-label'), state.index, true);
        renderPreview(el('next-preview'), el('next-label'), state.index + 1);
        if (el('qa-current-only').checked) renderQAList();
      }
    }
    function setFont(value) {
      fontSize = Math.max(20, Math.min(64, value));
      notes.style.fontSize = fontSize + 'px'; el('qa-answer').style.fontSize = fontSize + 'px';
      el('font-size').textContent = fontSize + 'px';
      el('font-smaller').disabled = fontSize <= 20; el('font-larger').disabled = fontSize >= 64;
    }
    function setReading(on) {
      // Keep the same part of a long script in view while the text reflows.
      var range = notes.scrollHeight - notes.clientHeight;
      // A script may fit entirely in reading mode. Retain this slide's last
      // scrollable position so returning to the narrower layout restores it.
      if (!qaMode && range > 0) scrollRatios[current.index] = notes.scrollTop / range;
      var ratio = scrollRatios[current.index] || 0;
      reading = on;
      layout.classList.toggle('reading', on);
      el('reading-toggle').setAttribute('aria-pressed', String(on));
      el('reading-toggle').textContent = on ? '슬라이드 중심' : '대본 중심';
      resize();
      if (qaMode) qaLayoutChanged = true;
      else notes.scrollTop = ratio * (notes.scrollHeight - notes.clientHeight);
    }
    el('notes-tab').onclick = function (event) { if (connected()) setPanel(false, event.detail > 0); };
    el('qa-tab').onclick = function (event) { if (connected()) setPanel(true, event.detail > 0); };
    el('qa-search').oninput = function () { if (connected()) { setQADetail(false, false); renderQAList(true); } };
    el('qa-current-only').onchange = function () { if (connected()) { setQADetail(false, false); renderQAList(true); } };
    el('qa-back').onclick = function () { if (connected()) setQADetail(false, true); };
    el('prev').onclick = function () { action(api.prev); };
    el('next').onclick = function () { action(api.next); };
    function jumpToSlide() {
      action(function () {
        var index = Number(el('jump').value) - 1;
        if (Number.isInteger(index) && index >= 0 && index < current.count) api.show(index);
        else el('jump').value = String(current.index + 1);
        focusReadingPane();
      });
    }
    el('jump').onchange = jumpToSlide;
    el('jump').onkeydown = function (event) {
      if (event.key === 'Enter' && !event.isComposing) {
        event.preventDefault(); event.stopPropagation(); jumpToSlide();
      }
    };
    el('media-toggle').onclick = function () { action(function () { api.media('toggle'); }); };
    el('display-setup').onclick = function () { action(api.openDisplaySetup); };
    el('media-reset').onclick = function () { action(function () { api.media('reset'); }); };
    el('blank').onclick = function () { action(api.toggleBlank); };
    el('font-smaller').onclick = function () { if (connected()) setFont(fontSize - 2); };
    el('font-larger').onclick = function () { if (connected()) setFont(fontSize + 2); };
    el('reading-toggle').onclick = function () { if (connected()) setReading(!reading); };
    el('timer-toggle').onclick = function () {
      if (!connected()) return;
      if (timerRunning) stopTimer();
      else { startedAt = win.performance.now(); timerRunning = true; paintTimer(); }
    };
    el('timer-reset').onclick = function () { if (connected()) { elapsed = 0; startedAt = win.performance.now(); paintTimer(); } };

    function keydown(event) {
      if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;
      var target = event.target;
      if (!connected()) return;
      var key = event.key.toLowerCase();
      if (qaMode && key === 'escape') {
        event.preventDefault();
        if (qaDetail) setQADetail(false, true);
        else setPanel(false, true);
        return;
      }
      if (target && (target.isContentEditable || (target.closest && target.closest('input, textarea, select')))) return;
      if (target && target.closest && target.closest('.notes-tabs')) {
        if (['arrowleft', 'arrowright', 'home', 'end'].indexOf(key) >= 0) {
          event.preventDefault();
          var nextQA = key === 'end' || (key !== 'home' && !qaMode);
          setPanel(nextQA, false); (nextQA ? el('qa-tab') : el('notes-tab')).focus(); return;
        }
        if (['arrowup', 'arrowdown', 'pageup', 'pagedown'].indexOf(key) >= 0) return;
      }
      if (target && target.closest && target.closest('#qa-list')) {
        if (['arrowleft', 'arrowright', 'arrowup', 'arrowdown', 'home', 'end', 'pageup', 'pagedown'].indexOf(key) >= 0) {
          event.preventDefault();
          var buttons = [].slice.call(el('qa-list').querySelectorAll('button'));
          var index = buttons.indexOf(target.closest('button'));
          if (key === 'home') index = 0;
          else if (key === 'end') index = buttons.length - 1;
          else if (key === 'arrowup' || key === 'arrowleft' || key === 'pageup') index--;
          else index++;
          if (buttons.length) buttons[Math.max(0, Math.min(buttons.length - 1, index))].focus();
          return;
        }
      }
      if (qaMode && target && target.closest && target.closest('#qa-answer-panel') &&
          ['arrowup', 'arrowdown', 'pageup', 'pagedown', 'home', 'end', ' '].indexOf(key) >= 0) return;
      if (target && target.closest && target.closest('button') && (event.key === ' ' || event.key === 'Enter')) return;
      // Q&A navigation keys must never advance the audience slide. Slide changes
      // remain available through the explicit footer controls.
      if (qaMode && ['arrowleft', 'arrowright', 'arrowup', 'arrowdown', 'pageup', 'pagedown', 'home', 'end', 'backspace', ' ', 'enter'].indexOf(key) >= 0) {
        event.preventDefault();
        if (!qaDetail) {
          var first = el('qa-list').querySelector('button');
          if (first) first.focus();
        }
        return;
      }
      var handled = true;
      if (['arrowright', 'arrowdown', 'pagedown', ' ', 'enter'].indexOf(key) >= 0) action(api.next);
      else if (['arrowleft', 'arrowup', 'pageup', 'backspace'].indexOf(key) >= 0) action(api.prev);
      else if (key === 'home') action(function () { api.show(0); });
      else if (key === 'end') action(function () { api.show(current.count - 1); });
      else if (key === 'p') action(function () { api.media('toggle'); });
      else if (key === 'r') action(function () { api.media('reset'); });
      else if (key === 'b') action(api.toggleBlank);
      else if (key === 'q') setPanel(!qaMode, true);
      else handled = false;
      if (handled) event.preventDefault();
    }
    function pointerControl(event) {
      // Mouse users return to reading/navigation. Keyboard users retain button
      // focus, so Tab and native Space/Enter activation continue to work.
      if (event.detail > 0 && event.target.closest && event.target.closest('button') && event.target.id !== 'display-setup' &&
          !event.target.closest('.notes-tabs, #qa-panel') && connected()) {
        focusReadingPane();
      }
    }
    function resize() { sizePreview(el('current-preview')); sizePreview(el('next-preview')); }
    function cleanup() {
      if (destroyed) return;
      destroyed = true;
      stopLivePreview();
      if (detachAnimationWindow) detachAnimationWindow();
      win.clearInterval(interval);
      if (unsubscribe) unsubscribe();
      doc.removeEventListener('keydown', keydown);
      doc.removeEventListener('click', pointerControl);
      win.removeEventListener('resize', resize);
      win.removeEventListener('pagehide', cleanup);
      win.removeEventListener('beforeunload', cleanup);
      delete win.__SUVPresenterCleanup;
    }
    win.__SUVPresenterCleanup = cleanup;
    doc.addEventListener('keydown', keydown);
    doc.addEventListener('click', pointerControl);
    win.addEventListener('resize', resize);
    win.addEventListener('pagehide', cleanup);
    win.addEventListener('beforeunload', cleanup);
    if (api.attachAnimationWindow) detachAnimationWindow = api.attachAnimationWindow(win);
    unsubscribe = api.subscribe(render);
    render(api.getState()); paintTimer();
    renderQAAnswer(null); renderQAList();
    interval = win.setInterval(function () { if (connected()) paintTimer(); }, 250);
    notes.focus();
    return cleanup;
  }

  window.SUVPresenter = {mount: mount};
})();
