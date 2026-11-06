#!/usr/bin/env python3
"""Real-browser checks on the built portal (Playwright, Chromium, axe-core 4.14 from node_modules).

    python3 -I tools/check_browser.py [--site site] [--break NAME]

Checks, on every page: axe-core with no serious or critical issues in light and dark; no horizontal overflow at
320, 390, 768, 1024, 1440 and 1920 pixels; no console errors; the skip link is the first thing focused. And on the tools:
the record builder conforms after loading an example, the validator converts the xGov MEM sample, Escape closes the palette,
and pages still render their content with app.js blocked.

--break NAME damages a copy of the site and must make the run fail (vaccination). Names are in BREAKS.
"""
import argparse
import functools
import http.server
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIDTHS = [320, 390, 768, 1024, 1440, 1920]
AXE = (ROOT / 'node_modules' / 'axe-core' / 'axe.min.js')


def serve(site):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=str(site))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/'


def run(site, verbose=True):
    from playwright.sync_api import sync_playwright
    if not AXE.exists():
        print('FAIL axe-core is missing: run npm ci (a check that cannot run fails)')
        return 1
    axe_src = AXE.read_text()
    srv, base = serve(site)
    fails = []
    pages = sorted(p.name for p in site.glob('*.html'))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for scheme in ('light', 'dark'):
            ctx = b.new_context(color_scheme=scheme, viewport={'width': 1280, 'height': 900}, bypass_csp=True)  # only so axe can be injected
            for name in pages:
                pg = ctx.new_page()
                errs = []
                pg.on('console', lambda m, errs=errs: errs.append(m.text) if m.type == 'error' else None)
                pg.on('pageerror', lambda e, errs=errs: errs.append(str(e)))
                pg.goto(base + name, wait_until='load')
                pg.add_script_tag(content=axe_src)
                res = pg.evaluate("""async () => { const r = await axe.run(document, {resultTypes: ['violations'],
                    runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']}});
                    return r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical').map(v => v.id + ': ' + v.nodes.length + ' ' + v.nodes.slice(0,2).map(n => n.target.join(' ')).join(' | ')); }""")
                for v in res:
                    fails.append(f'axe {scheme} {name}: {v}')
                if scheme == 'light':
                    for w in WIDTHS:
                        pg.set_viewport_size({'width': w, 'height': 900})
                        over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                        if over > 1:
                            wide = pg.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !e.closest('.table-wrap,pre,.graph')).slice(0,3).map(e => e.tagName + '.' + e.className)""")
                            fails.append(f'overflow {w}px {name}: {over}px {wide}')
                    pg.set_viewport_size({'width': 1280, 'height': 900})
                    pg.keyboard.press('Tab')
                    first = pg.evaluate("document.activeElement && document.activeElement.getAttribute('href')")
                    if first != '#main':
                        fails.append(f'keyboard {name}: first focus is {first}, not the skip link')
                if errs:
                    fails.append(f'console {scheme} {name}: {errs[:2]}')
                pg.close()
            ctx.close()
        # tools
        ctx = b.new_context(viewport={'width': 1280, 'height': 900})
        pg = ctx.new_page()
        pg.goto(base + 'builder.html')
        pg.select_option('#b-example', 'dataset-postcodes')
        status = pg.inner_text('#b-status')
        if 'Conforms' not in status:
            fails.append(f'builder: example does not conform: {status} {pg.inner_text("#b-issues")[:300]}')
        pg.select_option('#b-example', 'dataset-critical-asset')
        if 'Conforms' not in pg.inner_text('#b-status'):
            fails.append(f'builder: critical asset example does not conform: {pg.inner_text("#b-issues")[:300]}')
        pg.fill('#f-title', '')
        if 'to fix' not in pg.inner_text('#b-status'):
            fails.append('builder: clearing the title did not raise an error')
        pg.goto(base + 'validate.html')
        pg.click('button[data-sample="s-mem"]')
        out = pg.inner_text('#v-out')
        if 'Conforms to DCAT-UK AP' not in out or 'Converted from the xGov MEM' not in out:
            fails.append(f'validator: MEM sample did not convert and conform: {out[:300]}')
        pg.keyboard.press('/')
        if not pg.evaluate("document.getElementById('palette').open"):
            fails.append('palette: / did not open search')
        pg.keyboard.type('licence')
        if pg.evaluate("document.querySelectorAll('#pal-list a').length") == 0:
            fails.append('palette: no results for "licence"')
        pg.keyboard.press('Escape')
        if pg.evaluate("document.getElementById('palette').open"):
            fails.append('palette: Escape did not close it')
        pg.close()
        # degraded: scripts blocked, content still there
        ctx2 = b.new_context(java_script_enabled=False)
        pg = ctx2.new_page()
        for name in ('index.html', 'profile.html', 'properties.html', 'changes.html'):
            pg.goto(base + name)
            if len(pg.inner_text('main')) < 500:
                fails.append(f'no-script {name}: main content missing')
        pg.goto(base + 'builder.html')
        if 'needs JavaScript' not in pg.inner_text('main'):
            fails.append('no-script builder.html: no message saying it needs JavaScript')
        b.close()
    srv.shutdown()
    for f in fails:
        print('FAIL', f)
    print(f'{"FAIL" if fails else "pass"}: {len(pages)} pages, light and dark, {len(WIDTHS)} widths, tools and no-script ({len(fails)} problems)')
    return 1 if fails else 0


def _sub(f, a, b):
    t = f.read_text(encoding='utf-8')
    assert a in t, f'break could not find {a!r}'
    f.write_text(t.replace(a, b, 1), encoding='utf-8')


BREAKS = {
    'contrast': lambda s: (s / 'style.css').write_text((s / 'style.css').read_text() + '\n.lede{color:#c8c8c8!important}\n'),
    'overflow': lambda s: (s / 'style.css').write_text((s / 'style.css').read_text() + '\n.lede{width:2400px}\n'),
    'label': lambda s: _sub(s / 'builder.html', '<label for="b-class">What are you describing?</label>', ''),
    'console': lambda s: (s / 'app.js').write_text((s / 'app.js').read_text() + '\nthrow new Error("deliberate");\n'),
    'skip': lambda s: _sub(s / 'index.html', '<a class="skip" href="#main">Skip to main content</a>', ''),
    'validator': lambda s: _sub(s / 'validator.js', "if (ob === 'M') add('error'", "if (false) add('error'"),
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default=str(ROOT / 'site'))
    ap.add_argument('--break', dest='brk', choices=sorted(BREAKS))
    a = ap.parse_args(argv)
    site = Path(a.site)
    if a.brk:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'site'
            shutil.copytree(site, copy)
            BREAKS[a.brk](copy)
            code = run(copy, verbose=False)
        print(('pass' if code else 'FAIL') + f' the browser checks catch the "{a.brk}" break')
        sys.exit(0 if code else 1)
    sys.exit(run(site))


if __name__ == '__main__':
    main()
