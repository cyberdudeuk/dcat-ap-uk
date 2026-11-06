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
        # D-018: the axe pass bypasses the CSP, so a separate pass with the CSP on catches anything it blocks
        cctx = b.new_context(viewport={'width': 1280, 'height': 900})
        for name in pages:
            pg = cctx.new_page()
            cerrs = []
            pg.on('console', lambda m, cerrs=cerrs: cerrs.append(m.text) if m.type == 'error' else None)
            pg.on('pageerror', lambda e, cerrs=cerrs: cerrs.append(str(e)))
            pg.goto(base + name, wait_until='load')
            pg.wait_for_timeout(50)
            if cerrs:
                fails.append(f'csp {name}: {cerrs[:2]}')
            pg.close()
        cctx.close()
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
                        # let resize handlers (the global bar folds into More) run before measuring (D-012)
                        pg.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
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
        if 'conform' not in pg.inner_text('#b-level').lower():
            fails.append('builder: no conformance level shown')
        pg.select_option('#b-example', '')
        pg.select_option('#b-ext', 'health')
        if not pg.query_selector('#f-numberOfRecords'):
            fails.append('builder: choosing the health extension did not add its fields')
        pg.goto(base + 'bulk.html')
        pg.click('#bk-sample')
        try:
            pg.wait_for_selector('#bk-t tbody tr', timeout=5000)
        except Exception:  # a broken converter shows no table; report it rather than crash
            pass
        bt = pg.inner_text('#bk-out')
        if '1 record checked' not in bt or 'Level 1' not in bt and 'Level 2' not in bt and 'Level 3' not in bt:
            fails.append(f'bulk: the template row did not convert and conform: {bt[:300]}')
        pg.goto(base + 'openapi.html')
        pg.click('#oas-sample')
        ot = pg.inner_text('#oas-out')
        if 'Draft data service record' not in ot or 'https://api.example.org/bus-stops/v2' not in ot:
            fails.append(f'openapi: the example did not convert: {ot[:300]}')
        pg.goto(base + 'adopt.html')
        pg.check('#ck-c1')
        pg.reload()
        if not pg.is_checked('#ck-c1'):
            fails.append('checklist: a tick was not remembered')
        pg.goto(base + 'validate.html?ext=ai-ready')
        if pg.input_value('#v-ext') != 'ai-ready':
            fails.append('validator: ?ext= did not choose the extension')
        pg.goto(base + 'validate.html')
        pg.click('button[data-sample="s-mem"]')
        out = pg.inner_text('#v-out')
        if 'Conforms to DCAT-AP-UK' not in out or 'Converted from the xGov MEM' not in out:
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
        # D-024: every global menu opens at every width, including groups folded into More (and its items can be clicked)
        # also with the largest text from Display options, where menus are wider and reach the screen edge
        ctx_xl = b.new_context(viewport={'width': 1280, 'height': 900})
        ctx_xl.add_init_script("try { localStorage.setItem('ukap:dp-text', 'xl'); } catch (e) {}")
        for w, mctx in [(w, c) for c in (ctx, ctx_xl) for w in WIDTHS]:
            tag = '' if mctx is ctx else ' (largest text)'
            mp = mctx.new_page(); mp.set_viewport_size({'width': w, 'height': 900}); mp.goto(base + 'index.html')
            groups = mp.evaluate("[...document.querySelectorAll('.gbar li.grp > button')].map(b => b.textContent.trim())")
            for g in groups:
                mp.goto(base + 'index.html')
                inmore = mp.evaluate("(g) => { const b = [...document.querySelectorAll('.gbar li.grp > button')].find(x => x.textContent.trim() === g); return !!b.closest('li.more'); }", g)
                try:
                    if inmore:
                        mp.locator('.gbar li.more > button').click(timeout=3000)
                    mp.locator('.gbar li.grp > button', has_text=g).first.click(timeout=3000)
                except Exception as e:
                    fails.append(f'menu {w}px{tag} {g}: cannot be clicked{" inside More" if inmore else ""} ({type(e).__name__})')
                    continue
                ok = mp.evaluate("""(g) => { const b = [...document.querySelectorAll('.gbar li.grp > button')].find(x => x.textContent.trim() === g);
                    const a = b.parentNode.querySelector(':scope > ul > li > a'); if (!a) return 'no items';
                    const r = a.getBoundingClientRect(); if (!r.width) return 'did not open';
                    const m = b.parentNode.querySelector(':scope > ul').getBoundingClientRect();
                    if (m.left < -1 || m.right > document.documentElement.clientWidth + 1) return 'runs off the screen';
                    const h = document.elementFromPoint(r.left + 4, r.top + r.height / 2); return a.contains(h) ? '' : 'covered'; }""", g)
                if ok:
                    fails.append(f'menu {w}px{tag} {g}: {ok}')
            mp.close()
        # D-026: the bar always shows the current section, even when it is folded into More
        for w in WIDTHS:
            cp = ctx.new_page(); cp.set_viewport_size({'width': w, 'height': 900}); cp.goto(base + 'governance.html')
            shown = cp.evaluate("""() => [...document.querySelectorAll('.gbar ul.top > li.current, .gbar ul.top > li > a[aria-current="page"]')]
                .some(x => x.getBoundingClientRect().width > 0)""")
            if not shown:
                fails.append(f'current section {w}px governance.html: not shown in the bar')
            cp.close()
        # Design rule (ADR 0014): the global bar fits without folding at 1280 pixels and wider, so About is one click away on a laptop
        for w in (1280, 1440, 1920):
            fp = ctx.new_page(); fp.set_viewport_size({'width': w, 'height': 800}); fp.goto(base + 'index.html')
            if fp.evaluate("document.querySelector('.gbar').classList.contains('folding')"):
                fails.append(f'bar {w}px: folds into More; it must fit at 1280 pixels and wider')
            fp.close()
        # D-025: pressing Enter in a form does not try to submit it (form-action 'none' would block it and hang the page)
        sp = ctx.new_page(); serrs = []
        sp.on('console', lambda m: serrs.append(m.text[:120]) if m.type == 'error' else None)
        sp.set_default_timeout(5000)
        for name, sel in (('openapi.html', '#oas-url'), ('builder.html', '#b-id'), ('lineage.html', '#tr-q')):
            sp.goto(base + name)
            try:
                sp.locator(sel).fill('acc'); sp.locator(sel).press('Enter'); sp.wait_for_timeout(150)
            except Exception as e:
                serrs.append(f'{name}: Enter hung ({type(e).__name__})')
        if serrs:
            fails.append(f'submit: {serrs[:2]}')
        sp.close()
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
    'csp': lambda s: _sub(s / 'index.html', '<main id="main"', '<main style="color:red" id="main"'),
    'bulk': lambda s: _sub(s / 'validator.js', "var rows = parseCSV(text), notes = [];", "var rows = [], notes = [];"),
    'menus': lambda s: _sub(s / 'app.js', 'if (except && li.contains(except)) return;', 'if (li === except) return;'),
    'menuedge': lambda s: _sub(s / 'style.css', '.gbar ul.top>li>.sub.flip{left:auto;right:0}', ''),
    'current': lambda s: _sub(s / 'app.js', "more.classList.toggle('current', ", "more.classList.toggle('x-current', "),
    'fold': lambda s: _sub(s / 'style.css', 'padding:.7rem .6rem;', 'padding:.7rem 1.6rem;'),
    'moreview': lambda s: _sub(s / 'app.js', "if (first) first.scrollIntoView({ block: 'nearest' });", ''),
    'submit': lambda s: _sub(s / 'app.js', "doc.addEventListener('submit', function (e) { e.preventDefault(); }, true);", ''),
    'meter': lambda s: _sub(s / 'app.js', '<span data-w="\' + Math.round(', '<span style="width:\' + Math.round('),
    'nested': lambda s: _sub(s / 'standards.html', 'id="std-svg" viewBox', 'id="std-svg" role="img" viewBox'),
    'extension': lambda s: _sub(s / 'validator.js', "Object.keys(e.props).forEach(function (k) { Q.props[k] = e.props[k]; });", ""),
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
