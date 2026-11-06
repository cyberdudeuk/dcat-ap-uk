#!/usr/bin/env python3
"""Structural checks on the built portal, each proven by a deliberate break (build standard VER-05).

    python3 -I tools/check_site.py [--site site]          run every check
    python3 -I tools/check_site.py --vaccinate            break a copy of the site once per check and prove each check fails

One check per function; a failing check prints what failed and where. Exit code 1 if any check fails.
"""
import argparse
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
EMAIL = re.compile(r'(?<![\w@])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w.-]*\()')
DECK_FILM = {'.pptx', '.ppt', '.key', '.odp', '.mp4', '.mov', '.webm', '.m4v', '.avi', '.mkv'}
SCAN_ROOT = [ROOT]  # the repository the C-17 scan reads; its deliberate break points it at a planted copy
TEXT_EXT = {'.html', '.js', '.css', '.json', '.jsonld', '.ttl', '.csv', '.yaml', '.yml', '.txt', '.xml', '.svg', '.md'}


class Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.dups, self.links, self.tags = set(), [], [], []
        self.scripts, self.first_focusable, self.tables, self.in_table = [], None, [], 0
        self.metas, self.title, self._in_title, self.html_lang = {}, '', False, None
        self.handlers = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if 'id' in a:
            (self.dups.append(a['id']) if a['id'] in self.ids else self.ids.add(a['id']))
        if tag == 'html':
            self.html_lang = a.get('lang')
        if tag in ('a', 'link') and a.get('href'):
            self.links.append((tag, a['href'], a.get('rel')))
        if tag in ('img', 'script', 'iframe', 'source') and a.get('src'):
            self.links.append((tag, a['src'], None))
        if tag == 'script':
            self.scripts.append(a)
        if tag == 'meta' and a.get('name'):
            self.metas[a['name']] = a.get('content')
        if tag == 'meta' and a.get('http-equiv'):
            self.metas['http-equiv:' + a['http-equiv'].lower()] = a.get('content')
        if self.first_focusable is None and (tag == 'a' and a.get('href') or tag in ('button', 'input', 'select', 'textarea')):
            self.first_focusable = (tag, a)
        for k in a:
            if k.startswith('on'):
                self.handlers.append((tag, k))
        if tag == 'title' and not self.title:
            self._in_title = True  # the document title only, not titles inside SVG (D-004)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, d):
        if self._in_title:
            self.title += d


def parse(path):
    d = Doc()
    d.feed(path.read_text(encoding='utf-8'))
    d.text = path.read_text(encoding='utf-8')
    return d


def pages(site):
    return sorted(site.glob('*.html'))


# ---------------------------------------------------------------------------
def c_csp(site, docs):
    """C-01 every page sets a Content Security Policy with no unsafe sources."""
    bad = [p.name for p, d in docs if 'default-src' not in (d.metas.get('http-equiv:content-security-policy') or '') or 'unsafe' in (d.metas.get('http-equiv:content-security-policy') or '')]
    return bad


def c_external(site, docs):
    """C-02 no script, stylesheet, image or font loaded from another host (E2: self-contained pages)."""
    bad = []
    for p, d in docs:
        for tag, href, rel in d.links:
            if tag in ('script', 'img', 'iframe', 'source') or (tag == 'link' and rel in ('stylesheet', 'preconnect', 'preload', 'icon', 'dns-prefetch')):
                if re.match(r'^(https?:)?//', href):
                    bad.append(f'{p.name}: {tag} {href}')
    for f in site.rglob('*.css'):
        if re.search(r'url\(\s*["\']?(https?:)?//', f.read_text()) or '@import' in f.read_text():
            bad.append(f'{f.name}: external url() or @import')
    return bad


def c_email(site, docs):
    """C-03 no email address anywhere in the published files (COL-02), metadata and data included."""
    bad = []
    for f in site.rglob('*'):
        if f.is_file() and f.suffix in TEXT_EXT:
            for m in EMAIL.finditer(f.read_text(encoding='utf-8', errors='ignore')):
                bad.append(f'{f.relative_to(site)}: {m.group(0)}')
    return bad


def c_ids(site, docs):
    """C-04 ids are unique on every page."""
    return [f'{p.name}: duplicate id {i}' for p, d in docs for i in d.dups]


def c_links(site, docs):
    """C-05 every internal link resolves, to a file and, if it has one, an anchor on that page."""
    ids = {p.name: d.ids for p, d in docs}
    bad = []
    for p, d in docs:
        for tag, href, rel in d.links:
            u = urlparse(href)
            if u.scheme or href.startswith(('//', 'mailto:', 'data:')):
                continue
            target = unquote(u.path) or p.name
            fp = (p.parent / target).resolve()
            if not fp.exists():
                bad.append(f'{p.name}: {href} (no file)')
                continue
            if u.fragment and fp.suffix == '.html':
                if u.fragment not in ids.get(fp.name, set()):
                    bad.append(f'{p.name}: {href} (no anchor)')
    return bad


def c_tables(site, docs):
    """C-06 every table is captioned, has scoped headers and sits in a labelled, focusable scroll region."""
    bad = []
    for p, d in docs:
        n_tables = len(re.findall(r'<table[\s>]', d.text))
        if len(re.findall(r'<caption[\s>]', d.text)) < n_tables:  # exact tag names, not prefixes (D-006)
            bad.append(f'{p.name}: table without caption')
        for m in re.finditer(r'<th(?=[\s>])(?![^>]*scope=)[^>]*>', d.text):  # not <thead> (D-005)
            bad.append(f'{p.name}: th without scope')
            break
        for m in re.finditer(r'<table', d.text):
            before = d.text[max(0, m.start() - 200):m.start()]
            if 'class="table-wrap" role="region"' not in before or 'tabindex="0"' not in before:
                bad.append(f'{p.name}: table not in a labelled scroll region')
                break
    return bad


def c_meta(site, docs):
    """C-07 every page describes itself: artefact id, version, class, as-of, review date, and JSON-LD."""
    need = ('artefact:id', 'artefact:version', 'artefact:class', 'artefact:as-of', 'artefact:review-date')
    bad = [f'{p.name}: missing {k}' for p, d in docs for k in need if not d.metas.get(k)]
    bad += [f'{p.name}: no JSON-LD' for p, d in docs if 'application/ld+json' not in d.text]
    return bad


def c_colophon(site, docs):
    """C-08 every page carries the colophon: disclaimers, licence, version, QR code, barcode and the contact form."""
    bad = []
    for p, d in docs:
        t = d.text
        for need, why in (('class="colophon"', 'colophon'), ('aria-label="QR code', 'QR code'), ('aria-label="Barcode', 'barcode'),
                          ('Open Government Licence', 'licence'), ('Not an official GOV.UK service', 'disclaimer'), ('href="contact.html"', 'contact link')):
            if need not in t:
                bad.append(f'{p.name}: no {why}')
    return bad


def c_skip(site, docs):
    """C-09 the first focusable element on every page is the skip link to main."""
    return [p.name for p, d in docs if not d.first_focusable or d.first_focusable[1].get('href') != '#main' or 'id="main"' not in d.text]


def c_deck_film(site, docs):
    """C-10 no deck or film files in the repository or the site, unless the owner says so for that piece."""
    bad = []
    for base in (ROOT, site):
        for f in base.rglob('*'):
            if '.git' in f.parts or 'node_modules' in f.parts:
                continue
            if f.suffix.lower() in DECK_FILM or re.search(r'^(film|deck)[ _-].*\.(dc\.)?html$', f.name, re.I):
                bad.append(str(f.relative_to(base)))
    return bad


def c_inline(site, docs):
    """C-11 no inline executable scripts and no inline event handlers, so the Content Security Policy can forbid them."""
    bad = []
    for p, d in docs:
        for a in d.scripts:
            if not a.get('src') and a.get('type') not in ('application/ld+json', 'application/json'):
                bad.append(f'{p.name}: inline script')
        bad += [f'{p.name}: {t} {h}' for t, h in d.handlers]
    return bad


def c_banner(site, docs):
    """C-12 every page shows the status banner: proposed, not endorsed, not an official service."""
    return [p.name for p, d in docs if 'is a proposal for review. It is not endorsed' not in d.text]


def c_lang_title(site, docs):
    """C-13 every page has lang="en-GB" and a unique title."""
    bad = [p.name for p, d in docs if d.html_lang != 'en-GB']
    seen = {}
    for p, d in docs:
        if d.title in seen:
            bad.append(f'{p.name}: same title as {seen[d.title]}')
        seen[d.title] = p.name
    return bad


def c_weight(site, docs):
    """C-14 no page over 1,500 KB with what it loads from this site (envelope: median page 1,500 KB)."""
    bad = []
    for p, d in docs:
        size = p.stat().st_size
        for tag, href, rel in d.links:
            if tag in ('script', 'link') and not urlparse(href).scheme and (p.parent / href).exists() and (rel in (None, 'stylesheet')):
                size += (p.parent / href).stat().st_size
        if size > 1_500_000:
            bad.append(f'{p.name}: {size // 1000} KB')
    return bad


def c_svg_names(site, docs):
    """C-15 every meaningful image has an accessible name; decorative icons are hidden."""
    bad = []
    for p, d in docs:
        for tag, a in d.tags:
            if tag == 'svg' and a.get('role') in ('img', 'group') and not (a.get('aria-label') or a.get('aria-labelledby')):
                bad.append(f'{p.name}: svg {a.get("class")} without a name')
            if tag == 'svg' and not a.get('role') and a.get('aria-hidden') != 'true':
                bad.append(f'{p.name}: svg {a.get("class")} neither named nor hidden')
            if tag == 'img' and 'alt' not in a:
                bad.append(f'{p.name}: img without alt')
    return bad


def c_unrendered(site, docs):
    """C-16 no unrendered template placeholders, such as {layers} or {prov("K")}, in page text (D-007)."""
    bad = []
    for p, d in docs:
        t = re.sub(r'<script.*?</script>|<pre.*?</pre>|<code>.*?</code>', '', d.text, flags=re.S)
        for m in re.finditer(r'\{(?:[a-z_]+(?:\([^)]*\))?|E\([^)]*\)|self\.[^}]*)\}', t):
            bad.append(f'{p.name}: {m.group(0)[:40]}')
    return bad


def c_llms(site, docs):
    """C-18 llms.txt and llms-full.txt exist, every page is listed in llms.txt, and every link in it resolves to a built file."""
    bad = []
    lt, lf = site / 'llms.txt', site / 'llms-full.txt'
    if not lt.exists() or not lf.exists():
        return ['llms.txt or llms-full.txt is missing']
    text = lt.read_text(encoding='utf-8')
    base = re.search(r'https://[^/]+/[^/]+/', text)
    base = base.group(0) if base else ''
    for u in re.findall(r'\]\(([^)]+)\)', text):
        rel = u[len(base):] if base and u.startswith(base) else None
        if rel is None:
            bad.append(f'llms.txt: link outside the site {u}')
            continue
        if not (site / (rel or 'index.html')).exists():
            bad.append(f'llms.txt: {u} does not resolve')
    for p, d in docs:
        name = '' if p.name == 'index.html' else p.name
        if p.name not in ('404.html',) and not p.name.startswith('class-') and (base + name) + ')' not in text and (base + name + ':') not in text:
            if f'({base}{name})' not in text:
                bad.append(f'llms.txt does not list {p.name}')
    return bad


def c_no_style_attr(site, docs):
    """C-19 no style attributes in any page: the CSP (style-src 'self') blocks them, so they silently do nothing (D-018)."""
    bad = []
    for p, d in docs:
        n = sum(1 for t, a in d.tags if 'style' in a)
        if n:
            bad.append(f'{p.name}: {n} style attribute(s)')
    return bad


def c_tours(site, docs):
    """C-20 every guided tour stop points at something on its page, so no tour silently skips a step."""
    import yaml as _y
    tours = _y.safe_load((ROOT / 'content' / 'guide.yaml').read_text(encoding='utf-8'))['tours']
    bad = []
    for key, steps in tours.items():
        f = site / ('index.html' if key == 'index' else f'{key}.html')
        if not f.exists():
            bad.append(f'tour for missing page {key}')
            continue
        html = f.read_text(encoding='utf-8')
        for st in steps:
            sel = st['sel']
            ok = (sel.startswith('#') and f'id="{sel[1:]}"' in html) or (sel.startswith('.') and re.search(r'class="[^"]*\b' + re.escape(sel[1:]) + r'\b', html))
            if not ok:
                bad.append(f'{key}: tour stop "{st["title"]}" points at {sel}, which is not on the page')
    return bad


def c_feedback(site, docs):
    """C-21 every page offers "Suggest a change to this page", pointing at an issue form that exists and naming that page."""
    bad = []
    forms = {x.name for x in (ROOT / '.github' / 'ISSUE_TEMPLATE').glob('*.yml')}
    for p, d in docs:
        html = p.read_text(encoding='utf-8')
        m = re.search(r'<a href="([^"]+)">Suggest a change to this page</a>', html)
        if not m:
            bad.append(f'{p.name}: no feedback link')
            continue
        t = re.search(r'template=([^&"]+)', m.group(1))
        if not t or t.group(1) not in forms:
            bad.append(f'{p.name}: feedback link uses a missing issue form')
        elif p.name.replace('.', '%2E') not in m.group(1) and p.name not in m.group(1):
            bad.append(f'{p.name}: feedback link does not name the page')
    return bad


# Protective markings and handling caveats from the Government Security Classifications Policy and NATO practice. The page may
# name the three classifications (it explains them); it must never carry a caveat or a release marking.
MARKINGS = re.compile(r'\b(UK EYES ONLY|EYES ONLY|FVEY|NOFORN|REL(?:EASABLE)? TO\b|REL [A-Z]{3}(?:[ ,/][A-Z]{3})*\b|NATO (?:RESTRICTED|CONFIDENTIAL|SECRET|UNCLASSIFIED)|COSMIC TOP SECRET|ORCON|CABINET OFFICE EYES)')


def c_markings(site, docs):
    """C-22 no protective markings or handling caveats anywhere public: pages, downloads and the requirements file (ADR 0015, RQ-18)."""
    bad = []
    files = list(site.glob('*.html')) + list((site / 'downloads').glob('requirements*')) + [ROOT / 'content' / 'requirements.yaml']
    for f in files:
        for m in MARKINGS.finditer(f.read_text(encoding='utf-8')):
            bad.append(f'{f.name}: carries the marking "{m.group(0)}"')
    return bad


# C-23: old organisation names and personal details. The directorate is now the Government Data directorate in GDS
# (owner-stated, 6 November 2026). Personal and team details are matched by hash, so the check never publishes them.
OLD_ORG = re.compile(r'Office of the (?:Government )?Chief Data Officer|\bOCDO\b')
PERSONAL = {'fcd2b45b8eda145e', 'd24e913a4107af87', '602fa48e40f5b901', '8a0217b61d3a5f9e'}


def _grams(text):
    import hashlib
    words = re.findall(r'[a-z]+', text.lower())
    for n in (1, 3):
        for i in range(len(words) - n + 1):
            g = ' '.join(words[i:i + n])
            yield g, hashlib.sha256(g.encode()).hexdigest()[:16]


def c_people(site, docs):
    """C-23 no old organisation name (OCDO) and no personal or team details anywhere: pages, downloads or repository files. Contact is by form only."""
    bad = []
    base = SCAN_ROOT[0]
    files = list(site.rglob('*.html')) + [f for f in (site / 'downloads').rglob('*') if f.is_file() and f.suffix in TEXT_EXT | {'.json', '.ttl', '.jsonld', '.csv', '.yaml', '.md', '.txt'}]
    files += [f for f in base.rglob('*') if f.is_file() and not any(x in f.relative_to(base).parts for x in ('.git', 'node_modules', 'site', 'build')) and f.suffix in TEXT_EXT | {'.py', '.cff', '.yaml', '.yml', '.md', '.json'}]
    for f in files:
        t = f.read_text(encoding='utf-8', errors='ignore')
        rel = f.name if f.is_relative_to(site) else str(f.relative_to(base))
        for m in OLD_ORG.finditer(t):
            if 'check_site.py' not in rel:
                bad.append(f'{rel}: old organisation name "{m.group(0)}"')
        hit = {h for g, h in _grams(t) if h in PERSONAL}
        if hit:
            bad.append(f'{rel}: personal or team details ({len(hit)} match)')
    return bad


def c_email_repo(site, docs):
    """C-17 no email address in the repository's own files either; test fixtures may use reserved example domains only."""
    bad = []
    base = SCAN_ROOT[0]
    for f in base.rglob('*'):
        if not f.is_file() or any(x in f.relative_to(base).parts for x in ('.git', 'node_modules', 'site', 'build')) or f.suffix not in TEXT_EXT | {'.py', '.cff', ''}:
            continue
        rel = f.relative_to(base)
        for m in EMAIL.finditer(f.read_text(encoding='utf-8', errors='ignore')):
            if rel.parts[0] == 'tests' and re.search(r'@example\.(org|com|net)$', m.group(0)):
                continue
            bad.append(f'{rel}: {m.group(0)}')
    return bad


CHECKS = [c_csp, c_external, c_email, c_ids, c_links, c_tables, c_meta, c_colophon, c_skip, c_deck_film, c_inline, c_banner, c_lang_title, c_weight, c_svg_names, c_unrendered, c_email_repo, c_llms, c_no_style_attr, c_tours, c_feedback, c_markings, c_people]


def run(site, quiet=False):
    docs = [(p, parse(p)) for p in pages(site)]
    failed = {}
    for c in CHECKS:
        bad = c(site, docs)
        cid = c.__doc__.split()[0]
        if bad:
            failed[cid] = bad
            if not quiet:
                print(f'FAIL {cid} {c.__doc__.split(" ", 1)[1].strip()}')
                for b in bad[:8]:
                    print('   ', b)
                if len(bad) > 8:
                    print(f'    ... and {len(bad) - 8} more')
        elif not quiet:
            print(f'pass {cid}')
    return failed


# Each break damages a copy of the site in the way the check exists to catch.
def _sub(f, a, b, count=1):
    t = f.read_text(encoding='utf-8')
    if a not in t:
        raise RuntimeError(f'break could not find {a!r} in {f.name}')
    f.write_text(t.replace(a, b, count), encoding='utf-8')


def _plant_repo(s):
    repo = s / 'repo'
    repo.mkdir()
    (repo / 'README.md').write_text('Write to data.team' + '@' + 'dsit.gov.uk')
    SCAN_ROOT[0] = repo


BREAKS = {
    'C-01': lambda s: _sub(s / 'index.html', "default-src 'self'", "default-src *; script-src 'unsafe-inline'"),
    'C-02': lambda s: _sub(s / 'index.html', '<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="https://cdn.example.com/x.css">'),
    'C-03': lambda s: _sub(s / 'downloads' / 'profile.json', '"title":"DCAT Application Profile for the UK"', '"title":"DCAT Application Profile for the UK","c":"someone' + '@' + 'dsit.gov.uk"'),
    'C-04': lambda s: _sub(s / 'profile.html', 'id="model"', 'id="classes"'),
    'C-05': lambda s: _sub(s / 'index.html', 'href="builder.html"', 'href="builder.html#no-such-anchor"'),
    'C-06': lambda s: _sub(s / 'profile.html', '<caption id="explorer-cap">', '<caption-x id="explorer-cap">'),
    'C-07': lambda s: _sub(s / 'index.html', '<meta name="artefact:review-date"', '<meta name="artefact:reviewdate"'),
    'C-08': lambda s: _sub(s / 'index.html', 'aria-label="QR code', 'aria-label="Code'),
    'C-09': lambda s: _sub(s / 'index.html', '<a class="skip" href="#main">Skip to main content</a>', ''),
    'C-10': lambda s: (s / 'Film 1 - showcase.dc.html').write_text('<p>film</p>'),
    'C-11': lambda s: _sub(s / 'index.html', '<script src="app.js"></script>', '<script>alert(1)</script>'),
    'C-12': lambda s: _sub(s / 'roles.html', 'is a proposal for review. It is not endorsed', 'is ready'),
    'C-13': lambda s: _sub(s / 'roles.html', '<title>Your role - DCAT-AP-UK</title>', '<title>Knowledge - DCAT-AP-UK</title>'),
    'C-14': lambda s: (s / 'style.css').write_text((s / 'style.css').read_text() + '/*' + 'x' * 1_600_000 + '*/'),
    'C-16': lambda s: _sub(s / 'strategy.html', '<h2 id="layers">', '<h2 id="layers">{layers}'),
    'C-17': lambda s: _plant_repo(s),
    'C-19': lambda s: _sub(s / 'index.html', '<main id="main"', '<main style="color:red" id="main"'),
    'C-20': lambda s: _sub(s / 'builder.html', 'id="b-level"', 'id="b-level-gone"'),
    'C-23': lambda s: _sub(s / 'governance.html', '<h2 id="adrs"', '<p>Office of the Government Chief Data Officer</p><h2 id="adrs"'),
    'C-22': lambda s: _sub(s / 'requirements.html', '<h2 id="controlled">', '<p>REL FVEY</p><h2 id="controlled">'),
    'C-21': lambda s: _sub(s / 'types.html', 'template=change-request.yml', 'template=no-such-form.yml'),
    'C-18': lambda s: _sub(s / 'llms.txt', 'downloads/profile.json)', 'downloads/no-such-file.json)'),
    'C-15': lambda s: _sub(s / 'profile.html', 'role="group" aria-labelledby="model-t"', 'role="img"'),
}


def vaccinate(site):
    ok = True
    for c in CHECKS:
        cid = c.__doc__.split()[0]
        if cid not in BREAKS:
            print(f'FAIL {cid} has no deliberate break')
            ok = False
            continue
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'site'
            shutil.copytree(site, copy)
            BREAKS[cid](copy)
            docs = [(p, parse(p)) for p in pages(copy)]
            caught = bool(c(copy, docs))
            SCAN_ROOT[0] = ROOT
            print(('pass' if caught else 'FAIL') + f' {cid} catches its deliberate break')
            ok &= caught
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default=str(ROOT / 'site'))
    ap.add_argument('--vaccinate', action='store_true')
    a = ap.parse_args(argv)
    site = Path(a.site)
    if a.vaccinate:
        sys.exit(0 if vaccinate(site) else 1)
    failed = run(site)
    print(f'{len(CHECKS) - len(failed)} of {len(CHECKS)} checks pass')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
