/* In-deck editor for the single-file deck.
 *
 * bundle.py embeds the editor app (editor/app) as window.SUVEditorApp together
 * with this file. The "에디터" button opens that app over the current page (a
 * full-window frame, no new window) and this file answers the requests it
 * normally sends to editor.py, so no server is needed:
 *
 *   /_config, /_files, /_stat   fixed answers for this one deck
 *   iframe src /deck/<name>     the current deck HTML, as srcdoc
 *   /_upload                    the picked image as a data URI (stays in the file)
 *   PUT /deck/<name>            written to the opened HTML file. A page cannot
 *                               write its own file:// path until the user picks
 *                               it once (Chrome/Edge open dialog). The pick is
 *                               checked against this page's suv-deck-id (set by
 *                               bundle.py) and kept in IndexedDB, so later saves,
 *                               also after reopening or rebuilding, go straight to it
 *   /_saveas                    written to a new file the user picks
 *   (other browsers download a copy instead)
 *
 * Closing the editor (저장 or 닫기) rewrites the current page with the edited
 * deck, so the edits show at once without a reload. Edits not yet written to
 * the file make the page warn before it is left. Ctrl+S on the deck page saves
 * the deck the same way instead of the browser's "Save page as".
 *
 * File handles and the file-save dialog live in this page, not in the editor
 * frame: a handle dies with the frame that created it, and the frame is
 * removed after every save.
 */
(function () {
  'use strict';

  var app = window.SUVEditorApp;
  if (!app) return;

  // Mirrors DEFAULT_CONFIG in editor/editor.py. No autosave: a save needs a
  // click for the browser file-save dialog, and every save closes the editor.
  var CONFIG = {
    slide: 'section.slide',
    body: '.body',
    title: '.title, h1, h2',
    media: 'figure, table, .tbl, .fig-stack, img, svg, pre',
    heading: 'h1, h2, h3',
    editable: '.title, .kicker, .course, .display, .presenter, .lead, ' +
              '.foot-sec, .ul li, .tbl th, .tbl td, .card, p',
    imageDir: 'imgs',
    autosave: false
  };
  var frame = null;
  // document.write keeps this window, so this survives applying an edit.
  var state = window.__suvEditorState || (window.__suvEditorState = {handle: null, unsaved: false});

  window.addEventListener('beforeunload', function (ev) {
    if (state.unsaved) { ev.preventDefault(); ev.returnValue = ''; }
  });

  // The deck file handle, kept per page URL so a reload does not ask again.
  function db(mode, use) {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open('suv-editor', 1);
      req.onupgradeneeded = function () { req.result.createObjectStore('handles'); };
      req.onerror = function () { reject(req.error); };
      req.onsuccess = function () {
        var tx = req.result.transaction('handles', mode), op;
        try { op = use(tx.objectStore('handles')); } catch (e) { reject(e); return; }
        tx.oncomplete = function () { resolve(op.result); };
        tx.onerror = tx.onabort = function () { reject(tx.error); };
      };
    });
  }

  // Chrome opens the file picker or the permission prompt only on a real click.
  // Ctrl+S is a browser shortcut and does not count, so it can only write to a
  // file that was already picked and allowed.
  // A save that did not happen for a reason the user can act on.
  function notSaved(text, tone) {
    var err = new Error(text);
    err.name = 'NotSaved';
    err.tone = tone || 'warn';
    return err;
  }
  function needsClick() {
    return notSaved('처음 한 번은 [저장] 버튼을 눌러 이 HTML 파일을 고른다');
  }

  // The remembered deck file. One kept by an older build may be a same-named
  // file elsewhere: check it once per page load and forget it if it is not ours.
  async function savedHandle(gesture) {
    var h = state.handle;
    if (!h) {
      try { h = await db('readonly', function (s) { return s.get(location.href); }); } catch (e) { h = null; }
    }
    if (!h) return null;
    state.handle = h;
    if (h.queryPermission && await h.queryPermission({mode: 'readwrite'}) !== 'granted' && !gesture) {
      throw notSaved('[저장] 버튼을 누르면 Chrome 이 이 파일 저장을 허용할지 묻는다');
    }
    if (!state.checked) {
      var ok;
      try { ok = await isDeck(h); } catch (e) { ok = false; }   // moved or deleted
      if (!ok) { forgetHandle(); return null; }
      state.checked = true;
    }
    return h;
  }

  function forgetHandle() {
    state.handle = null;
    db('readwrite', function (s) { return s.delete(location.href); }).catch(function () {});
  }

  function keepHandle(h) {
    state.handle = h;
    db('readwrite', function (s) { return s.put(h, location.href); }).catch(function () {});
  }

  // Know early whether this file was picked before, for the editor's hint.
  db('readonly', function (s) { return s.get(location.href); })
    .then(function (h) { if (h && !state.handle) state.handle = h; }, function () {});

  function fileName() {
    return decodeURIComponent(location.pathname.split('/').pop()) || 'deck.html';
  }

  function script(code) {
    return '<script>' + code.replace(/<\/script/gi, '<\\/script') + '</script>';
  }

  // The deck as authored: drop the UI present.js added and its runtime state.
  function cleanRoot() {
    var root = document.documentElement.cloneNode(true);
    [].forEach.call(root.querySelectorAll('[data-suv-ui]'), function (el) { el.remove(); });
    [].forEach.call(root.querySelectorAll('.slide.current'), function (el) {
      el.classList.remove('current');
      if (!el.className) el.removeAttribute('class');
    });
    var body = root.querySelector('body');
    if (body) {
      body.classList.remove('presenting', 'suv-blackout');
      body.style.removeProperty('--present-scale');
      if (!body.getAttribute('class')) body.removeAttribute('class');
      if (!body.getAttribute('style')) body.removeAttribute('style');
    }
    return root;
  }

  function serialize(root) {
    return '<!DOCTYPE html>\n' + root.outerHTML;
  }

  // What the editor loads: the clean deck plus what its layouts need.
  function deckSource() {
    var root = cleanRoot();
    // Editor layouts need cde-layout.css. Keep it inside the file; the
    // placeholder link only stops the editor from adding an external one.
    var head = root.querySelector('head');
    function add(tag, attrs, text) {
      var el = document.createElement(tag);
      Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
      if (text) el.textContent = text;
      head.appendChild(el);
    }
    if (!head.querySelector('style[data-suv-cde-layout]')) add('style', {'data-suv-cde-layout': ''}, app.layout);
    add('link', {rel: 'stylesheet', href: 'cde-layout.css', 'data-cde-ui': ''});
    add('style', {'data-cde-ui': ''}, app.chrome);
    return serialize(root);
  }

  var HTML_TYPES = [{description: 'HTML', accept: {'text/html': ['.html']}}];

  // Write html to the deck file (copyName empty) or to a new file. The deck
  // file is picked once; a different file picked then counts as a copy.
  function deckId() {
    var meta = document.querySelector('meta[name="suv-deck-id"]');
    return meta && meta.getAttribute('content');
  }

  // First save: the user points at the HTML this page was opened from. An open
  // dialog, not a save dialog: it never truncates the file, and the file can be
  // checked first. Picking a same-named copy elsewhere would otherwise "save"
  // where a reload never looks.
  async function isDeck(h) {
    var id = deckId();
    if (!id) return h.name === fileName();
    return (await (await h.getFile()).text()).indexOf('name="suv-deck-id" content="' + id + '"') !== -1;
  }

  // This page's own file as a local path (Windows: C:\\...).
  function filePath() {
    var path = decodeURIComponent(location.pathname);
    return /^\/[A-Za-z]:/.test(path) ? path.slice(1).replace(/\//g, '\\') : path;
  }

  // Browsers cannot open a file dialog at a given path: only at well-known
  // folders or where a dialog with the same id was last used. So the dialog
  // remembers this deck's folder (id), and the first time the file path goes to
  // the clipboard for Ctrl+L, Ctrl+V, Enter.
  var PICK_ID = 'suv-deck';

  // say/copy come from the editor frame, which holds the focus the clipboard needs.
  async function pickDeck(say, copy) {
    // Same click as the dialog: nothing awaited before showOpenFilePicker below.
    var copied = false;
    try { if (copy) { copy(filePath()); copied = true; } } catch (e) { copied = false; }
    if (say) {
      say(copied ? '이 파일 경로를 복사했다. 창에서 Ctrl+L, Ctrl+V, Enter 로 고른다'
                 : '창에서 Ctrl+L 후 ' + filePath() + ' 을 입력해 고른다', 'warn');
    }
    var h = (await window.showOpenFilePicker({id: PICK_ID, types: HTML_TYPES}))[0];
    if (!(await isDeck(h))) {
      throw notSaved('고른 파일(' + h.name + ')은 지금 연 HTML 이 아니다. 주소창에 보이는 그 파일을 고른다', 'bad');
    }
    return h;
  }

  // Write html to the deck file (copyName empty) or to a new file.
  async function saveFile(html, copyName, gesture, say, copy) {
    var name = copyName || fileName();
    if (!window.showOpenFilePicker) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([html], {type: 'text/html'}));
      a.download = name;
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 10000);
      return {name: name, toDeck: false};
    }
    var h;
    if (copyName) {
      h = await window.showSaveFilePicker({suggestedName: name, types: HTML_TYPES, id: PICK_ID,
        startIn: state.handle || undefined});
    } else {
      h = await savedHandle(gesture);
      if (!h && !gesture) throw needsClick();
      if (!h) {
        h = await pickDeck(say, copy);
        keepHandle(h);
        state.checked = true;
      }
      // Asks "변경사항 저장?" once; Chrome needs a fresh click for it, and a
      // long stay in the dialog can use the first one up.
      if (h.requestPermission && await h.queryPermission({mode: 'readwrite'}) !== 'granted') {
        var allowed;
        try { allowed = await h.requestPermission({mode: 'readwrite'}); } catch (e) { allowed = 'retry'; }
        if (allowed === 'retry') throw notSaved('파일을 확인했다. [저장] 을 한 번 더 누르면 Chrome 이 저장 허용을 묻는다');
        if (allowed !== 'granted') throw notSaved('Chrome 이 파일 저장을 허용하지 않았다. [저장] 을 눌러 다시 허용한다');
      }
    }
    var out = await h.createWritable();
    await out.write(html);
    await out.close();
    return {name: h.name, toDeck: !copyName};
  }

  function notice(text) {
    var status = document.querySelector('.present-status');
    if (!status) return;
    status.textContent = text;
    setTimeout(function () { if (status.textContent === text) status.textContent = ''; }, 2500);
  }

  // Ctrl+S on the deck page (also with a Korean IME, where key is not "s").
  async function saveDeck() {
    var html = serialize(cleanRoot());
    try {
      if (!(await saveFile(html)).toDeck) {
        notice('다른 파일에 저장했다. 지금 연 파일은 그대로다');
        return;
      }
      state.unsaved = false;
      notice('저장됨');
    } catch (err) {
      notice(err && err.name === 'AbortError' ? '저장 취소'
        : err && err.name === 'NotSaved' ? err.message.replace('[저장] 버튼', '에디터의 [저장] 버튼')
        : '저장 실패 - ' + (err && err.message));
    }
  }

  function isSaveKey(ev) {
    return (ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.code === 'KeyS' || String(ev.key).toLowerCase() === 's');
  }

  document.addEventListener('keydown', function (ev) {
    if (!isSaveKey(ev) || frame) return;
    ev.preventDefault();
    saveDeck();
  }, true);

  // Runs inside the editor frame, before the editor app.
  function shim() {
    var ctx = window.__suvEditor;

    function json(data, status, text) {
      return new Response(JSON.stringify(data), {status: status || 200, statusText: text || 'OK',
        headers: {'Content-Type': 'application/json'}});
    }
    function selfContained(html) {
      return String(html).replace(/<link[^>]*href="cde-layout\.css"[^>]*>\n?/g, '');
    }
    // asCopy: 다른 이름으로 저장. Otherwise the deck file itself.
    async function write(html, asCopy, copyName) {
      html = selfContained(html);
      // A copy always needs the picker; let Chrome judge the click behind it.
      var gesture = asCopy || Date.now() - clickedAt < 2000;
      var done = await ctx.saveFile(html, asCopy ? copyName || ctx.name : '', gesture, say, function (text) {
        navigator.clipboard.writeText(text).catch(function () {});
      });
      // Let the editor show its status first, then hand back to the deck.
      setTimeout(function () { ctx.close(html, done.toDeck); }, 400);
      return json({name: done.name, mtime: Date.now() / 1000});
    }
    function failed(err) {
      var name = err && err.name;
      // The editor reports any non-2xx as a failure; these are not failures.
      if (name === 'AbortError') {
        setTimeout(function () { say('저장 취소 - 저장 대기', 'warn'); }, 0);
        return json({}, 499, 'cancelled');
      }
      if (name === 'NotSaved') {
        setTimeout(function () { say(err.message, err.tone); }, 0);
        return json({}, 499, 'not saved');
      }
      if (name === 'NotAllowedError') {
        setTimeout(function () { say('처음 한 번은 [저장] 버튼을 눌러 이 HTML 파일을 고른다', 'warn'); }, 0);
        return json({}, 499, 'needs click');
      }
      console.error('[editor] save failed', err);
      var why = (name || 'Error') + ': ' + (err && err.message || err);
      setTimeout(function () { say('저장 실패 - ' + why, 'bad'); }, 0);
      return json({}, 500, 'write failed');
    }
    function say(text, tone) {
      var status = document.getElementById('status');
      if (status) { status.textContent = text; status.dataset.tone = tone; }
    }
    // When the save button was really clicked (Ctrl+S is not a click for Chrome).
    var clickedAt = 0;
    document.addEventListener('click', function (ev) {
      if (ev.isTrusted && ev.target.closest && ev.target.closest('[data-act="save"]')) clickedAt = Date.now();
    }, true);
    function dataURI(file) {
      return new Promise(function (resolve, reject) {
        var reader = new FileReader();
        reader.onload = function () { resolve(reader.result); };
        reader.onerror = function () { reject(reader.error); };
        reader.readAsDataURL(file);
      });
    }

    var applyOnly = false;
    var realFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      var url = String(input && input.url || input);
      var path = url.split('?')[0];
      var method = String(init && init.method || 'GET').toUpperCase();
      if (path === '/_config') return Promise.resolve(json(Object.assign({}, ctx.config, {deck: ctx.name})));
      if (path === '/_files') return Promise.resolve(json({files: [ctx.name]}));
      if (path === '/_stat') return Promise.resolve(json({mtime: 0}));
      if (path === '/_upload') {
        return dataURI(init.body).then(function (src) { return json({src: src}); },
          function () { return json({}, 500, 'read failed'); });
      }
      if (path === '/_saveas') {
        return write(init.body, true, new URL(url, 'http://deck/').searchParams.get('name')).catch(failed);
      }
      if (path.indexOf('/deck/') === 0 && method === 'PUT' && applyOnly) {
        ctx.close(selfContained(init.body), false);
        return Promise.resolve(json({name: ctx.name, mtime: 0}));
      }
      if (path.indexOf('/deck/') === 0 && method === 'PUT') return write(init.body, false).catch(failed);
      return realFetch(input, init);
    };

    // The editor points its stage and rail iframes at /deck/<name>.
    var src = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src');
    Object.defineProperty(HTMLIFrameElement.prototype, 'src', {
      configurable: true, get: src.get,
      set: function (value) {
        if (String(value).indexOf('/deck/') === 0) this.srcdoc = ctx.deck;
        else src.set.call(this, value);
      }
    });

    // Saving closes the editor, so autosave would close it mid-edit.
    var style = document.createElement('style');
    style.textContent = 'label.chk { display: none !important; }' +
      // Keep the toolbar on one line: buttons never wrap, long status text is cut.
      '.bar { flex-wrap: wrap; row-gap: 6px; }' +
      '.bar button, .bar select { white-space: nowrap; flex-shrink: 0; }' +
      '.bar .status { flex: 0 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }' +
      '.bar .suv-hint { flex: 0 0 auto; white-space: nowrap; font-size: 12px; color: #b45309; }';
    document.head.appendChild(style);
    var auto = document.getElementById('autosave');
    if (auto) auto.checked = false;
    var bar = document.querySelector('.bar');
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = '닫기';
    close.title = '수정 내용을 발표 화면에 반영하고 돌아가기 (파일에는 저장하지 않음)';
    close.addEventListener('click', function () {
      // The editor marks unsaved changes with a warning tone on its status.
      var status = document.getElementById('status');
      if (!status || status.dataset.tone !== 'warn') { ctx.close(null); return; }
      // Reuse the editor's own serializer: its save PUT, answered without writing.
      applyOnly = true;
      document.querySelector('[data-act="save"]').click();
    });
    if (bar) bar.appendChild(close);
    var statusEl = document.getElementById('status');
    if (statusEl) {
      new MutationObserver(function () { statusEl.title = statusEl.textContent; })
        .observe(statusEl, {childList: true, characterData: true, subtree: true});
    }
    if (bar && ctx.firstSave) {
      // A page cannot write its own file until the user picks it once.
      var hint = document.createElement('span');
      hint.className = 'suv-hint';
      hint.textContent = '첫 저장: 파일 1회 선택';
      hint.title = '처음 한 번만 [저장] 버튼을 눌러, 열리는 창에서 지금 연 이 HTML 파일(' + ctx.name + ')을 고른다. ' +
        '누르는 순간 파일 경로가 복사되므로 창에서 Ctrl+L, Ctrl+V, Enter 면 된다. ' +
        '이후 저장과 Ctrl+S 는 창 없이 그 파일에 바로 기록된다';
      bar.insertBefore(hint, close);
    }

    // With a Korean IME Ctrl+S reports key "ㄴ"; the editor checks key "s" only
    // and the browser would open its own "Save page as" dialog.
    function guardSave(doc) {
      doc.addEventListener('keydown', function (ev) {
        if (!(ev.ctrlKey || ev.metaKey) || ev.altKey || ev.code !== 'KeyS' || ev.key.toLowerCase() === 's') return;
        ev.preventDefault();
        document.querySelector('[data-act="save"]').click();
      }, true);
    }
    guardSave(document);
    // Stage and rail frames: load does not bubble, but capture sees it.
    document.addEventListener('load', function (ev) {
      if (ev.target.tagName !== 'IFRAME') return;
      try { guardSave(ev.target.contentDocument); } catch (e) { /* not ours */ }
    }, true);
  }

  // html: the edited deck to show in place of this page, or null to keep it.
  // saved: whether that html is also what the deck file now holds.
  function close(html, saved) {
    if (frame) { frame.remove(); frame = null; }
    document.documentElement.style.removeProperty('overflow');
    if (!html) return;
    state.unsaved = !saved;
    // Out of the editor frame's call stack, which the rewrite tears down.
    setTimeout(function () {
      document.open();
      document.write(html);
      document.close();
    }, 0);
  }

  function open() {
    if (frame) return;
    // This runs inside the 에디터 click: renew write permission for the picked
    // file now, so later saves and Ctrl+S need no prompt.
    var h = state.handle;
    if (h && h.requestPermission) {
      h.queryPermission({mode: 'readwrite'}).then(function (p) {
        if (p !== 'granted') return h.requestPermission({mode: 'readwrite'});
      }).catch(function () {});
    }
    var deck = deckSource();
    frame = document.createElement('iframe');
    frame.setAttribute('data-suv-ui', '');
    frame.title = '슬라이드 편집';
    frame.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;border:0;' +
      'z-index:2147483000;background:#fff;';
    document.body.appendChild(frame);
    document.documentElement.style.overflow = 'hidden';
    var win = frame.contentWindow;
    win.__suvEditor = {deck: deck, name: fileName(), config: CONFIG, close: close,
      firstSave: !state.handle && !!window.showSaveFilePicker,
      saveFile: saveFile};
    var page = app.html
      .replace(/<link[^>]*editor\.css[^>]*>/, function () { return '<style>' + app.css + '</style>'; })
      .replace(/<script[^>]*editor\.js[^>]*><\/script>/, function () {
        return script('(' + shim.toString() + ')();') + script(app.js);
      });
    win.document.open();
    win.document.write(page);
    win.document.close();
    win.focus();
  }

  window.SUVEditor = {open: open};
})();
