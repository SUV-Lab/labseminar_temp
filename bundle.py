#!/usr/bin/env python3
"""Bundle a deck HTML into one self-contained file.

    python3 bundle.py build/<deck>.html output/<deck>.html

Inlines local and remote stylesheets, scripts, images, videos, the lab logo
and Google web fonts. present.js is followed by presenter.js so the presenter
view (N) works without a sibling file. Equations (data-tex) are typeset with
latex + dvisvgm into path-only SVG images, so the bundle needs neither KaTeX
nor math fonts; KaTeX stays inlined only as a fallback when that fails.
Only the Python stdlib is used. Remote resources need network access at build
time, not at viewing time.
"""
import base64
import html as htmllib
import mimetypes
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# Google Fonts serves woff2 only to browsers it recognizes.
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
MIME = {'.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf',
        '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.webm': 'video/webm'}
missing = []


def is_remote(ref):
    return ref.startswith(('http://', 'https://', '//'))


def resolve(ref, base):
    """base is a directory Path for local files or a URL string for remote ones."""
    if isinstance(base, str) or is_remote(ref):
        return urllib.parse.urljoin(base if isinstance(base, str) else '', ref)
    return base / urllib.parse.unquote(ref.split('#')[0].split('?')[0])


def fetch(loc):
    if isinstance(loc, Path):
        return loc.read_bytes()
    url = 'https:' + loc if loc.startswith('//') else loc
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def child_base(loc):
    return loc.parent if isinstance(loc, Path) else loc


def data_uri(ref, base):
    if ref.startswith(('data:', '#', 'blob:')) or not ref:
        return ref
    loc = resolve(ref, base)
    try:
        raw = fetch(loc)
    except Exception as e:  # keep the reference, report it at the end
        missing.append(f'{loc} ({e})')
        return ref
    path = urllib.parse.urlparse(str(loc)).path
    ext = Path(path).suffix.lower()
    mime = MIME.get(ext) or mimetypes.guess_type(path)[0] or 'application/octet-stream'
    # ponytail: base64 grows media by 4/3 and loads it all in memory; fine for
    # seminar-size clips, switch large videos to Blob URLs if decks get slow.
    return f'data:{mime};base64,{base64.b64encode(raw).decode()}'


def parse_ranges(text):
    out = []
    for part in text.split(','):
        part = part.strip().upper().removeprefix('U+')
        if '?' in part:
            lo, hi = part.replace('?', '0'), part.replace('?', 'F')
        else:
            lo, _, hi = part.partition('-')
        out.append((int(lo, 16), int(hi or lo, 16)))
    return out


def needed(block, used):
    """Drop @font-face subsets (Noto Sans KR has ~100) whose glyphs the deck never uses."""
    m = re.search(r'unicode-range:\s*([^;}]+)', block)
    if not m:
        return True
    return any(lo <= c <= hi for lo, hi in parse_ranges(m.group(1)) for c in used)


def woff2_only(src):
    """Keep just the woff2 entry of a multi-format src list (KaTeX ships three)."""
    items = re.findall(r'url\([^)]*\)\s*format\(["\']?woff2["\']?\)', src)
    return items[0] if items else src


def inline_css(css, base, used):
    def imp(m):
        loc = resolve(m.group(1), base)
        try:
            text = fetch(loc).decode('utf-8')
        except Exception as e:
            missing.append(f'{loc} ({e})')
            return m.group(0)
        return inline_css(text, child_base(loc), used)
    css = re.sub(r'@import\s+url\(\s*["\']?([^"\')]+)["\']?\s*\)[^;]*;', imp, css)
    css = re.sub(r'@font-face\s*{[^}]*}',
                 lambda m: m.group(0) if needed(m.group(0), used) else '', css)
    css = re.sub(r'(src:\s*)([^;}]+)', lambda m: m.group(1) + woff2_only(m.group(2)), css)
    return re.sub(r'url\(\s*(["\']?)([^"\')]+)\1\s*\)',
                  lambda m: f'url("{data_uri(m.group(2), base)}")', css)


TEX_DOC = (r'\documentclass{article}\usepackage{amsmath,amssymb,bm}'
           r'\pagestyle{empty}\begin{document}$\displaystyle %s$\end{document}')
LINK = r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*/?>'


def tex_svg(tex, ink):
    """Typeset one display equation into an SVG data URI and its height in em."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, 'eq.tex').write_text(TEX_DOC % tex, encoding='utf-8')
        run = lambda *cmd: subprocess.run(cmd, cwd=d, capture_output=True, text=True, check=True)
        run('latex', '-interaction=nonstopmode', '-halt-on-error', 'eq.tex')
        # --no-fonts turns glyphs into paths: the image renders with no math font.
        svg = run('dvisvgm', '--no-fonts', '--exact-bbox', '--stdout', 'eq.dvi').stdout
    svg = svg.replace('<svg ', f"<svg fill='{ink}' ", 1)
    height_pt = float(re.search(r"height='([\d.]+)pt'", svg).group(1))
    # TeX em is 10pt here; KaTeX draws at 1.21em, so the image keeps the
    # .eq-form font-size rules (30px, 26px, 25px) and the KaTeX look.
    em = height_pt / 10 * 1.21
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode(), em


def typeset_equations(html, base):
    """Swap data-tex elements for SVG images; drop KaTeX when none are left."""
    css = ''
    for ref in re.findall(LINK, html):
        if not is_remote(ref):
            try:
                css += fetch(resolve(ref, base)).decode('utf-8')
            except OSError:
                pass
    m = re.search(r'--ink:\s*(#[0-9a-fA-F]{3,8})', css)
    ink = m.group(1) if m else '#000000'

    def eq(m):
        tex = htmllib.unescape(m.group(3))
        try:
            uri, em = tex_svg(tex, ink)
        except (OSError, subprocess.CalledProcessError) as e:
            log = getattr(e, 'stdout', '') or str(e)
            err = next((l for l in log.splitlines() if l.startswith('!')), log[-200:])
            missing.append(f'equation {tex!r}: {err.strip()} (KaTeX fallback kept)')
            return m.group(0)
        # data-tex-src keeps the source for editing but stops the KaTeX loader.
        return (f'{m.group(1)} data-tex-src="{m.group(3)}"{m.group(4)}'
                f'<img class="eq-svg" src="{uri}" alt="{m.group(3)}" '
                f'style="height:{em:.3f}em;vertical-align:middle">{m.group(6)}')
    html = re.sub(r'(<(\w+)[^>]*?)\sdata-tex="([^"]*)"([^>]*>)(.*?)(</\2>)', eq, html, flags=re.S)
    if 'data-tex="' not in html:
        html = re.sub(r'<link[^>]*href="[^"]*katex[^"]*"[^>]*/?>\n?', '', html)
        html = re.sub(r'<script[^>]*src="[^"]*katex[^"]*"[^>]*>\s*</script>\n?', '', html)
    return html


def script_tag(code):
    return '<script>' + code.replace('</script', '<\\/script') + '</script>'


def bundle(src):
    html = src.read_text(encoding='utf-8')
    base = src.parent
    html = typeset_equations(html, base)
    js = {}  # loaded later so the font subset sees every UI string
    for ref in re.findall(r'<script[^>]*\ssrc="([^"]+)"[^>]*>\s*</script>', html):
        loc = resolve(ref, base)
        try:
            js[ref] = fetch(loc).decode('utf-8')
        except Exception as e:
            missing.append(f'{loc} ({e})')
        if Path(ref).name == 'present.js' and not is_remote(ref):
            presenter = resolve('presenter.js', child_base(loc))
            if presenter.exists():
                js[ref] += '\n' + presenter.read_text(encoding='utf-8')
            else:
                missing.append(f'{presenter} (presenter view N will not open)')
    used = {ord(c) for c in html + ''.join(js.values())}

    # Markup passes run before scripts are inlined, so tags quoted in JS stay untouched.
    html = re.sub(r'<style>(.*?)</style>',
                  lambda m: '<style>' + inline_css(m.group(1), base, used) + '</style>',
                  html, flags=re.S)

    def media(m):
        return re.sub(r'(\s(?:src|poster)=")([^"]+)"',
                      lambda a: a.group(1) + data_uri(a.group(2), base) + '"', m.group(0))
    html = re.sub(r'<(?:img|video|source|audio)\b[^>]*>', media, html)
    html = re.sub(r'(\sstyle=")([^"]*url\([^"]*)"',
                  lambda m: m.group(1) + inline_css(m.group(2).replace('&quot;', '"'), base, used)
                  .replace('"', '&quot;') + '"', html)

    def link(m):
        tag, ref = m.group(0), m.group(1)
        loc = resolve(ref, base)
        try:
            text = fetch(loc).decode('utf-8')
        except Exception as e:
            missing.append(f'{loc} ({e})')
            return tag
        return '<style>' + inline_css(text, child_base(loc), used) + '</style>'
    html = re.sub(LINK, link, html)

    def script(m):
        code = js.get(m.group(1))
        return m.group(0) if code is None else script_tag(code)
    html = re.sub(r'<script[^>]*\ssrc="([^"]+)"[^>]*>\s*</script>', script, html)
    return html


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    out = bundle(src)
    dst.write_text(out, encoding='utf-8')
    print(f'{dst}  {len(out.encode()) / 1e6:.1f} MB')
    for m in missing:
        print(f'  not inlined: {m}', file=sys.stderr)
    markup = re.sub(r'<script>.*?</script>', '', out, flags=re.S)
    left = re.findall(r'\s(?:src|poster)="(?!data:)([^"]+)"', markup)
    left += re.findall(r'<link[^>]*\shref="(?!data:)([^"]+)"', markup)
    left += re.findall(r'url\(["\']?((?:https?:)?//[^"\')]+)', markup)
    for ref in left:
        print(f'  external reference left: {ref}', file=sys.stderr)
    if missing:
        sys.exit(1)


if __name__ == '__main__':
    main()
