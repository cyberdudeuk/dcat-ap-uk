#!/usr/bin/env python3
"""Build the DCAT-UK AP portal and every downloadable file from the profile source.

    python3 -I tools/build.py [--out site]

Everything in the output folder is generated. Edit profile/, content/, examples/, site_src/ or this script, never the output.
"""
import argparse
import hashlib
import html
import io
import json
import math
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml  # noqa: E402

import generate  # noqa: E402
import ukap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
E = lambda s: html.escape(str(s if s is not None else ''), quote=True)  # noqa: E731
OB_LABEL = {'M': 'Mandatory', 'R': 'Recommended', 'O': 'Optional', 'C': 'Conditional'}
CHANGE_LABEL = {
    'unchanged': 'Unchanged', 'new': 'New', 'uri-fixed': 'Property IRI fixed', 'example-fixed': 'Example fixed', 'range-relaxed': 'Range relaxed',
    'range-changed': 'Range changed', 'range-fixed': 'Range fixed', 'obligation-changed': 'Obligation changed', 'definition-fixed': 'Definition fixed',
    'codelist-mapped': 'Codelist mapped', 'codelist-added': 'Codelist added', 'value-restored': 'Value restored', 'renamed': 'Renamed', 'merged': 'Merged'}
STATUS_LABEL = {'resolved': ('Resolved', 'ok'), 'provisional': ('Resolved, provisional', 'warn'), 'owner': ('Needs the owner', 'warn'),
                'superseded': ('Superseded', 'brand'), 'upstream': ('Waits on another project', 'warn')}
LEVEL = {'full': ('Yes', 'ok'), 'partial': ('Partly', 'warn'), 'none': ('No', 'err'), 'notseen': ('Not seen', 'brand')}
PROV_TEXT = {'V': 'Verified against the primary source', 'K': 'Background knowledge, not yet checked at the source', 'P': 'From a supplied pack',
             'S': 'Search-sourced', 'O': 'An operating rule of this profile', 'U': 'Unconfirmed'}

NAV = [
    ('index', 'Home', 'house', None),
    ('Profile', 'The profile', 'layers', ['profile', 'properties', 'codelists']),
    ('Tools', 'Tools', 'wrench', ['builder', 'validate', 'examples']),
    ('changes', "What's changed", 'git-pull-request', None),
    ('strategy', 'Strategy', 'route', None),
    ('roles', 'Your role', 'users-round', None),
    ('knowledge', 'Knowledge', 'network', None),
    ('downloads', 'Downloads', 'download', None),
    ('estate', 'Estate', 'compass', None),
    ('About', 'About', 'info', ['governance', 'accessibility', 'contact', 'sitemap', 'whats-new']),
]
TITLES = {
    'index': 'Home', 'profile': 'The profile at a glance', 'properties': 'Every property', 'codelists': 'Codelists', 'builder': 'Build a record',
    'validate': 'Check records', 'examples': 'Worked examples', 'changes': "What's changed from the xGov MEM", 'strategy': 'How it fits the strategy',
    'roles': 'Your role', 'knowledge': 'Knowledge', 'downloads': 'Downloads and API', 'estate': 'The estate: four portals',
    'governance': 'Design and governance', 'accessibility': 'Accessibility statement', 'contact': 'Contact', 'sitemap': 'Site map',
    'whats-new': "What's new", '404': 'Page not found'}
DESC = {
    'index': 'A proposed UK application profile of DCAT for describing public sector datasets and data services, evolved from the xGov MEM.',
    'profile': 'The classes of DCAT-UK AP, how they connect, and every property with its obligation, filterable.',
    'properties': 'Definitions, purpose, guidance, examples and lineage for every DCAT-UK AP property.',
    'codelists': 'Controlled lists for access rights, security classification, themes, frequency and more, with EU mappings.',
    'builder': 'Build a DCAT-UK AP record in your browser, with live checks, and download it as JSON, JSON-LD or Turtle.',
    'validate': 'Check DCAT-UK AP records, or convert xGov MEM records, in your browser. Nothing is uploaded.',
    'examples': 'Worked DCAT-UK AP records for datasets, data services, a series, a critical data asset and a catalogue.',
    'changes': 'How DCAT-UK AP differs from the xGov MEM, and how every issue in its backlog was dealt with.',
    'strategy': 'How DCAT-UK AP supports the roadmap for modern digital government, the National Data Library and the DAM Policy.',
    'roles': 'Routes through DCAT-UK AP for catalogue managers, data owners, leaders, engineers, suppliers and users.',
    'knowledge': 'Glossary, thesaurus, taxonomy and knowledge graph for DCAT-UK AP.',
    'downloads': 'SHACL shapes, JSON Schema, JSON-LD context, LinkML, codelists, data dictionary and examples.',
    'estate': 'How DCAT-UK AP compares with and joins the DAM playbooks, the Data Quality Commons and the Repos Asset Catalogue.',
    'governance': 'Status, versioning, change process, decisions, defects, open items, checks and self-assessment.',
    'accessibility': 'Accessibility statement for the DCAT-UK AP portal.',
    'contact': 'Ask a question, report a problem or request a change to DCAT-UK AP using the contact form.',
    'sitemap': 'Every page of the DCAT-UK AP portal.', 'whats-new': 'Changes in each release of DCAT-UK AP.', '404': 'The page could not be found.'}
SHORT_SRC = {'roadmap': 'Roadmap 2025 to 2030', 'ndl': 'National Data Library', 'dam': 'DAM Policy', 'rma2026': '2026 metadata guidance',
             'discovery': 'Discovery pattern', 'principles': 'Sharing principles', 'aiready': 'AI-ready data'}
ICONS = json.loads((ROOT / 'site_src' / 'icons.json').read_text())['icons']


def icon(name, cls='i'):
    if name not in ICONS:
        raise KeyError(f'icon {name} is not vendored: add it to tools/vendor_icons.py')
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-')


def tag(ob, text=None):
    return f'<strong class="tag {ob}">{E(text or OB_LABEL[ob])}</strong>'


def prov(code, date_=None):
    t = PROV_TEXT[code] + (f', {date_}' if date_ else '')
    return f'<abbr class="prov {code}" title="{E(t)}" data-tip="{E(t)}">{code}</abbr>'


def table(tid, caption, head, rows, sortable=True, row_attrs=None, num=()):
    th = ''.join(f'<th scope="col"{" class=num" if i in num else ""}>{h}</th>' for i, h in enumerate(head))
    body = ''
    for ri, r in enumerate(rows):
        attrs = (row_attrs[ri] if row_attrs else '')
        cells = ''.join((f'<th scope="row">{c}</th>' if ci == 0 else f'<td{" class=num" if ci in num else ""}>{c}</td>') for ci, c in enumerate(r))
        body += f'<tr{attrs}>{cells}</tr>'
    return (f'<div class="table-wrap" role="region" aria-labelledby="{tid}-cap" tabindex="0"><table id="{tid}"{" data-sortable" if sortable else ""}>'
            f'<caption id="{tid}-cap">{caption}</caption><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')


def ul(items, cls=''):
    return f'<ul{" class=" + chr(34) + cls + chr(34) if cls else ""}>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def qr_svg(text, label):
    import segno
    buf = io.BytesIO()
    segno.make(text, error='m').save(buf, kind='svg', scale=3, border=2, dark='#0b0c0c', light='#ffffff', xmldecl=False, svgns=True,
                                      title=label, svgclass='qr')
    s = buf.getvalue().decode()
    return s.replace('<svg ', f'<svg role="img" aria-label="{E(label)}" ', 1)


def barcode_svg(text, label):
    from barcode import Code128
    from barcode.writer import SVGWriter
    buf = io.BytesIO()
    Code128(text, writer=SVGWriter()).write(buf, options={'module_height': 9, 'module_width': 0.22, 'font_size': 0, 'text_distance': 1, 'quiet_zone': 2})
    s = buf.getvalue().decode()
    s = re.sub(r'<\?xml[^>]*>\s*', '', s)
    s = re.sub(r'<!DOCTYPE[^>]*>\s*', '', s)
    s = re.sub(r'<!--.*?-->\s*', '', s, flags=re.S)
    s = re.sub(r'<svg ', f'<svg role="img" aria-label="{E(label)}" ', s, count=1)
    return s


class Site:
    def __init__(self, p, portal, out):
        self.p, self.c, self.out = p, portal, Path(out)
        self.m = p.meta
        self.search = []
        self.pages = {}
        h = hashlib.sha256()
        for f in sorted(list((ROOT / 'profile').glob('*')) + list((ROOT / 'content').glob('*')) + list((ROOT / 'examples').glob('*'))
                        + list((ROOT / 'site_src').glob('*')) + [ROOT / 'tools' / 'build.py', ROOT / 'tools' / 'generate.py', ROOT / 'tools' / 'ukap.py']):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        self.build_id = f'{self.m["id"]}-{self.m["version"]}-{h.hexdigest()[:10]}'
        self.gloss_terms = sorted(((t['term'], t) for t in portal['glossary']), key=lambda x: -len(x[0]))
        self.src = {s['id']: s for s in p.lineage['sources']}

    # -- helpers ----------------------------------------------------------------
    def gloss(self, text, used=None):
        """Escape text, then link the first mention of glossary terms with an accessible tooltip."""
        out = E(text)
        used = used if used is not None else set()
        for term, t in self.gloss_terms:
            if t['id'] in used or len(term) < 4:
                continue
            m = re.search(r'(?<![\w>/-])(' + re.escape(E(term)) + r')(?![\w<-])', out)  # not part of a hyphenated name such as DCAT-UK
            if m and out.rfind('<', 0, m.start()) <= out.rfind('>', 0, m.start()) and out.rfind('<a ', 0, m.start()) <= out.rfind('</a>', 0, m.start()):
                a = f'<a class="term" href="knowledge.html#g-{t["id"]}" data-tip="{E(t["term"] + ": " + t["def"])}">{m.group(1)}</a>'
                out = out[:m.start()] + a + out[m.end():]
                used.add(t['id'])
        return out

    def add_search(self, t, k, u, s=''):
        self.search.append({'t': t, 'k': k, 'u': u, 's': re.sub(r'\s+', ' ', str(s))[:150]})

    def src_link(self, sid):
        s = self.src[sid]
        return f'<a href="{E(s["url"])}">{E(s["title"])}</a>{prov(s["prov"], s.get("date") if s["prov"] == "V" else None)}'

    def class_page(self, ck):
        return f'class-{slug(ck)}.html'

    def hero(self, ic, caption, title, lede, meta=None):
        mt = ''
        if meta:
            mt = '<ul class="meta-row">' + ''.join(f'<li>{icon(i)}<span>{x}</span></li>' for i, x in meta) + '</ul>'
        return (f'<div class="hero"><div class="tile">{icon(ic)}</div><div><p class="caption">{E(caption)}</p><h1>{E(title)}</h1>'
                f'<p class="lede">{lede}</p>{mt}</div></div>')

    # -- page shell ---------------------------------------------------------------
    def nav(self, key):
        items = ''
        for k, label, ic, kids in NAV:
            if kids:
                cur = key in kids
                sub = ''.join(f'<li><a href="{c}.html"{" aria-current=" + chr(34) + "page" + chr(34) if c == key else ""}>{E(TITLES[c])}</a></li>' for c in kids)
                items += (f'<li class="grp{" current" if cur else ""}"><button type="button" aria-expanded="false">{icon(ic)}<span>{E(label)}</span>{icon("chevron-down")}</button>'
                          f'<ul class="sub">{sub}</ul></li>')
            else:
                href = 'index.html' if k == 'index' else f'{k}.html'
                items += f'<li><a href="{href}"{" aria-current=" + chr(34) + "page" + chr(34) if k == key else ""}>{icon(ic)}<span>{E(label)}</span></a></li>'
        items += f'<li class="more"><button type="button" aria-expanded="false">{icon("menu")}<span>More</span>{icon("chevron-down")}</button><ul class="sub"></ul></li>'
        return f'<nav class="gbar" aria-label="Portal sections"><ul class="top">{items}</ul></nav>'

    def drawer(self, groups):
        if not groups:
            return '', ''
        h = '<h2>On this page</h2>'
        for g in groups:
            lis = ''.join(f'<li><a href="#{E(i["id"])}">{icon(i.get("icon", "chevron-right"))}<span>{E(i["label"])}</span>'
                          + (f'<span class="count" aria-label="{i["count"]} items">{i["count"]}</span>' if i.get('count') else '')
                          + ('<span class="flag">New</span>' if i.get('new') else '') + '</a></li>' for i in g['items'])
            h += f'<details open><summary>{icon(g.get("icon", "list-checks"))}<span>{E(g["title"])}</span></summary><ul>{lis}</ul></details>'
        toggle = ('<button type="button" class="toggle no-print" id="drawer-toggle" aria-controls="drawer" aria-expanded="true">'
                  '<span class="track" aria-hidden="true"></span><span class="tlabel">Hide page contents</span></button>')
        return toggle, f'<nav class="drawer" id="drawer" aria-label="On this page">{h}</nav>'

    def page(self, key, body, drawer=None, crumbs=None, scripts=(), jsonld_extra=None):
        m = self.m
        title = TITLES[key]
        full = (m['title'] if key == 'index' else f'{title} - {m["short_title"]}')
        desc = DESC[key]
        canonical = m['site_url'] + ('' if key == 'index' else f'{key}.html')
        toggle, drawer_html = self.drawer(drawer)
        cr = ''
        if crumbs:
            cr = '<nav aria-label="Breadcrumb"><ol class="crumbs"><li><a href="index.html">Home</a></li>' + ''.join(
                f'<li><a href="{h}">{E(t)}</a></li>' if h else f'<li aria-current="page">{E(t)}</li>' for t, h in crumbs) + '</ol></nav>'
        ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': full, 'description': desc, 'url': canonical, 'inLanguage': 'en-GB',
              'identifier': self.build_id, 'version': m['version'], 'dateModified': m['as_of'], 'datePublished': m['first_published'],
              'license': 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
              'isPartOf': {'@type': 'WebSite', 'name': m['title'], 'url': m['site_url']}}
        if jsonld_extra:
            ld['mainEntity'] = jsonld_extra
        self.pages[key] = title
        self.add_search(title, 'Page', f'{key}.html' if key != 'index' else 'index.html', desc)
        scr = ''.join(f'<script src="{s}"></script>' for s in scripts)
        doc = f'''<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(canonical)}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="style.css">
<meta name="artefact:id" content="{E(m["id"])}">
<meta name="artefact:version" content="{E(m["version"])}">
<meta name="artefact:class" content="portal">
<meta name="artefact:as-of" content="{E(m["as_of"])}">
<meta name="artefact:review-date" content="{E(m["review"])}">
<meta name="artefact:build" content="{E(self.build_id)}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<div class="banner" role="region" aria-label="Status"><strong class="tag warn">Proposed</strong>{E(m["short_title"])} {E(m["version"])} is a proposal for review. It is not endorsed and is not an official GOV.UK service. <a href="governance.html#status">What this means</a></div>
<header class="mast"><div class="mast-in">
<a class="name" href="index.html"><svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect width="32" height="32" rx="4" fill="#4c2c92"/><path d="M8 10h16M8 16h11M8 22h7" stroke="#fff" stroke-width="3" stroke-linecap="round"/><circle cx="24" cy="22" r="3" fill="#ffdd00"/></svg>{E(m["short_title"])}<span class="visually-hidden">: {E(m["title"])}</span></a>
<div class="mast-tools no-print">
<button type="button" data-open="palette">{icon("search")}<span class="lbl">Search</span> <kbd>/</kbd></button>
<button type="button" id="theme">{icon("contrast")}<span class="lbl">Light or dark</span></button>
<button type="button" id="share">{icon("share-2")}<span class="lbl">Share</span></button>
</div></div></header>
{self.nav(key)}
{toggle}
<div class="wrap">{drawer_html}<main id="main" tabindex="-1">{cr}
{body}
</main></div>
{self.colophon(key)}
<dialog id="palette" aria-labelledby="pal-h"><div class="pal-in"><h2 id="pal-h">Search the portal</h2>
<label class="visually-hidden" for="pal-q">Search</label><input type="search" id="pal-q" role="combobox" aria-expanded="true" aria-controls="pal-list" autocomplete="off" placeholder="Property, class, codelist, issue or page">
<p class="small" id="pal-count" aria-live="polite"></p><ul class="pal-list" id="pal-list" role="listbox" aria-label="Results"></ul>
<p class="btns"><button type="button" class="btn secondary small" id="pal-close">Close</button></p></div></dialog>
<dialog id="keys" aria-labelledby="keys-h"><div class="pal-in"><h2 id="keys-h">Keyboard shortcuts</h2>
<dl class="facts"><dt><kbd>/</kbd> or <kbd>Ctrl</kbd> <kbd>K</kbd></dt><dd>Search</dd><dt><kbd>?</kbd></dt><dd>These shortcuts</dd><dt><kbd>Esc</kbd></dt><dd>Close menus, tooltips and dialogs</dd><dt>Arrow keys</dt><dd>Move between tabs and search results</dd></dl>
<p class="btns"><button type="button" class="btn secondary small" id="keys-close">Close</button></p></div></dialog>
<div id="live" class="visually-hidden" aria-live="polite"></div>
<script src="search-index.js"></script>{scr}<script src="app.js"></script>
</body>
</html>
'''
        (self.out / ('index.html' if key == 'index' else f'{key}.html')).write_text(doc, encoding='utf-8')

    def colophon(self, key):
        m = self.m
        url = m['site_url'] + ('' if key == 'index' else f'{key}.html')
        return f'''<footer class="colophon"><div class="col-in">
<section aria-labelledby="f1"><h2 id="f1">About this portal</h2><ul>
<li><a href="governance.html#status">Status: proposed, not endorsed</a></li><li><a href="accessibility.html">Accessibility statement</a></li>
<li><a href="contact.html">Contact form</a></li><li><a href="sitemap.html">Site map</a></li><li><a href="{E(m["repo_url"])}">Source on GitHub</a></li></ul></section>
<section aria-labelledby="f2"><h2 id="f2">Disclaimers and transparency</h2>
<p class="small">Not an official GOV.UK service or policy, and not endorsed by the Data Standards Authority. Facts carry source labels: {prov("V")} verified, {prov("K")} background knowledge, {prov("P")} supplied pack, {prov("U")} unconfirmed. Examples are illustrative. Built with help from Claude, an AI model by Anthropic; every generated fact is checked by tests or labelled. No cookies, analytics or third-party requests.</p></section>
<section aria-labelledby="f3"><h2 id="f3">Licence and version</h2>
<p class="small">Content and the profile: <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>. Code: MIT. Lineage: the xGov MEM (OGL v3.0). Icons: Lucide (ISC).<br>Version {E(m["version"])}, as of {E(m["as_of"])}, review by {E(m["review"])}.<br>{E(m["attribution"])}.</p></section>
<section aria-labelledby="f4"><h2 id="f4">Build identifier</h2>
<div class="codes">{qr_svg(url, "QR code linking to this page")}{barcode_svg(self.build_id, "Barcode of the build identifier " + self.build_id)}</div>
<p class="small"><code>{E(self.build_id)}</code></p></section>
</div></footer>'''

    # -- pages ------------------------------------------------------------------
    def build_all(self):
        p = self.p
        self.out.mkdir(parents=True, exist_ok=True)
        for f in ('style.css', 'app.js', 'validator.js'):
            shutil.copy(ROOT / 'site_src' / f, self.out / f)
        (self.out / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="4" fill="#4c2c92"/><path d="M8 10h16M8 16h11M8 22h7" stroke="#fff" stroke-width="3" stroke-linecap="round"/><circle cx="24" cy="22" r="3" fill="#ffdd00"/></svg>\n')
        files = generate.generate(p)
        dl = self.out / 'downloads'
        (dl / 'examples').mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (dl / name).write_text(text, encoding='utf-8')
        prof = json.loads(files['profile.json'])
        (self.out / 'profile-data.js').write_text('window.UKAP_PROFILE=' + files['profile.json'] + ';\nwindow.UKAP_EXAMPLES='
                                                  + json.dumps({e['key']: e['record'] for e in p.examples}, ensure_ascii=False) + ';\n', encoding='utf-8')
        self.files = files
        self.home()
        self.profile_page()
        for ck in p.classes:
            self.class_detail(ck)
        self.properties_page()
        self.codelists_page()
        self.builder_page()
        self.validate_page()
        self.examples_page()
        self.changes_page()
        self.strategy_page()
        self.roles_page()
        self.knowledge_page()
        self.downloads_page()
        self.estate_page()
        self.governance_page()
        self.accessibility_page()
        self.contact_page()
        self.whatsnew_page()
        self.notfound_page()
        self.sitemap_page()
        self.write_machine(prof)
        (self.out / 'search-index.js').write_text('window.UKAP_SEARCH=' + json.dumps(self.search, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
        (self.out / '.nojekyll').write_text('')
        (self.out / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {self.m["site_url"]}sitemap.xml\n')
        urls = ''.join(f'<url><loc>{E(self.m["site_url"] + ("" if k == "index" else k + ".html"))}</loc><lastmod>{self.m["as_of"]}</lastmod></url>' for k in self.pages if k != '404')
        (self.out / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
        return self

    def counts(self):
        p = self.p
        n_props = sum(len(c['properties']) for c in p.classes.values())
        return {'classes': len(p.classes), 'props': len(p.props), 'uses': n_props, 'codelists': len(p.codelists),
                'concepts': sum(len(s['concepts']) for s in p.codelists.values()), 'backlog': len(p.lineage['backlog']),
                'resolved': sum(1 for b in p.lineage['backlog'] if b['status'] in ('resolved', 'provisional')),
                'new': sum(1 for v in p.props.values() if v['mem']['change'] == 'new'), 'orgs': (p.orgs or {}).get('count', 0),
                'mem_slots': len(p.mem_slots()), 'examples': len(p.examples), 'rules': len(p.rules)}

    def home(self):
        c, k = self.c, self.counts()
        doors = ''.join(f'<div class="card door">{icon(d["icon"])}<h3><a href="{d["href"]}">{E(d["title"])}</a></h3><p>{E(d["text"])}</p><p class="go"><a href="{d["href"]}">{E(d["cta"])}</a></p></div>' for d in c['doors'])
        why = ''.join(f'<div class="card"><h3>{icon(w["icon"])} {E(w["title"])}</h3><p>{E(w["text"])}</p></div>' for w in c['why_matters'])
        stats = [(k['classes'], 'classes', 'profile.html'), (k['props'], 'properties', 'properties.html'), (k['codelists'], 'codelists', 'codelists.html'),
                 (f'{k["resolved"]} of {k["backlog"]}', 'backlog items resolved', 'changes.html#backlog'), (k['new'], 'new properties since the xGov MEM', 'changes.html#crosswalk'),
                 (f'{k["orgs"]:,}', 'organisations to choose from', 'codelists.html#orgs')]
        st = ''.join(f'<div class="card"><p class="stat">{E(n)}</p><p><a href="{h}">{E(t)}</a></p></div>' for n, t, h in stats)
        easy = ''.join(f'<li>{E(x)}</li>' for x in c['easy_read'])
        layers = ''.join(f'<li>{"<strong>" if l.get("here") else ""}{E(l["title"])}{"</strong> (this profile)" if l.get("here") else ""}: {E(l["text"])}</li>' for l in reversed(c['infrastructure_layers']))
        body = self.hero('layers', 'Proposed application profile', self.m['title'],
                         self.gloss('One way to describe UK public sector datasets and data services, so they can be found, judged and shared across every catalogue. Built on DCAT 3 and aligned with DCAT-AP, it evolves the xGov MEM.'),
                         meta=[('git-branch', f'Version {E(self.m["version"])}'), ('clock', f'As of {E(self.m["as_of"])}'), ('flag', 'Proposed, not endorsed')])
        body += f'<h2 id="start">Where do you want to start?</h2><div class="grid">{doors}</div>'
        body += f'<div class="easy" id="easy"><h2>{icon("book-open")} In short (Easy Read)</h2><ul>{easy}</ul></div>'
        body += f'<h2 id="why">Why one profile matters</h2><div class="grid">{why}</div>'
        body += f'<h2 id="glance">At a glance</h2><div class="grid">{st}</div><p class="small">Counts are calculated from the profile when the portal is built.</p>'
        body += f'<h2 id="where">Where it sits</h2><p>A pan-UK public data infrastructure, from the people who use data down to the data itself. The profile is the shared record in the middle. {prov("K")}</p><ol>{layers}</ol><p><a href="strategy.html">How it fits the strategy</a></p>'
        body += (f'<h2 id="status">Status</h2><div class="panel warning"><p>{E(c["governance"]["status"])}</p>'
                 f'<p><a href="{E(self.m["change_request"])}">Request a change</a> or <a href="contact.html">get in touch</a>.</p></div>')
        drawer = [{'title': 'Home', 'icon': 'house', 'items': [{'id': 'start', 'label': 'Where to start', 'icon': 'signpost'}, {'id': 'easy', 'label': 'In short', 'icon': 'book-open'},
                   {'id': 'why', 'label': 'Why it matters', 'icon': 'lightbulb'}, {'id': 'glance', 'label': 'At a glance', 'icon': 'gauge'},
                   {'id': 'where', 'label': 'Where it sits', 'icon': 'layers'}, {'id': 'status', 'label': 'Status', 'icon': 'flag'}]}]
        self.page('index', body, drawer)

    def model_svg(self):
        """Class diagram: boxes for classes, arrows for object properties, clipped to box edges. Every box links to its class page."""
        p = self.p
        W, H = 270, 56
        col = {0: 20, 1: 380, 2: 740, 3: 1100}
        row = {0: 20, 1: 170, 2: 320, 3: 470}
        grid = {'CatalogueRecord': (0, 0), 'Catalogue': (1, 0), 'DatasetSeries': (0, 1), 'Dataset': (1, 1), 'DataService': (2, 1), 'Relationship': (2, 0),
                'ContactPoint': (0, 2), 'Distribution': (1, 2), 'Location': (2, 2), 'Attribution': (3, 2), 'Agent': (0, 3), 'Checksum': (1, 3), 'PeriodOfTime': (2, 3)}
        pos = {k: (col[c], row[r]) for k, (c, r) in grid.items()}
        edges = [('Catalogue', 'Dataset', 'dataset'), ('CatalogueRecord', 'Dataset', 'primary topic'), ('Catalogue', 'DataService', 'service'),
                 ('Dataset', 'DatasetSeries', 'in series'), ('Dataset', 'DataService', ''), ('DataService', 'Dataset', 'serves'),
                 ('Dataset', 'Relationship', 'qualified relation'), ('Dataset', 'Agent', 'publisher, creator'), ('Dataset', 'Distribution', 'distribution'),
                 ('Dataset', 'Location', 'spatial'), ('Dataset', 'Attribution', 'responsible role'), ('Dataset', 'ContactPoint', 'contact point'),
                 ('Distribution', 'Checksum', 'checksum'), ('Dataset', 'PeriodOfTime', 'temporal'), ('Distribution', 'DataService', 'access service')]

        def clip(x1, y1, x2, y2):
            # point where the segment from the centre (x1, y1) towards (x2, y2) leaves the box centred on (x1, y1)
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                return x1, y1
            tx = (W / 2) / abs(dx) if dx else float('inf')
            ty = (H / 2) / abs(dy) if dy else float('inf')
            k = min(tx, ty)
            return x1 + dx * k, y1 + dy * k
        s = ''
        for a, b, lbl in edges:
            if not lbl:
                continue
            (xa, ya), (xb, yb) = pos[a], pos[b]
            ca, cb = (xa + W / 2, ya + H / 2), (xb + W / 2, yb + H / 2)
            x1, y1 = clip(*ca, *cb)
            x2, y2 = clip(*cb, *ca)
            s += f'<line class="edge" x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" marker-end="url(#arr)"/>'
            f = .5 if abs(y2 - y1) < 1 or abs(x2 - x1) < 1 else .38  # diagonal labels sit nearer the source, clear of other boxes
            mx, my = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            s += f'<text class="edge-label halo" x="{mx:.0f}" y="{my - 4:.0f}" text-anchor="middle">{E(lbl)}</text>'
        for ck, (x, y) in pos.items():
            c = p.classes[ck]
            m = sum(1 for z in c['properties'] if z['ob'] == 'M')
            s += (f'<g class="node {c["ob"]}"><a href="{self.class_page(ck)}">'
                  f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="4"/><text x="{x + 12}" y="{y + 23}" font-weight="700">{E(c["label"])}</text>'
                  f'<text x="{x + 12}" y="{y + 43}" class="sm">{E(c["uri"])} · {len(c["properties"])} properties · {m} M</text></a></g>')
        return (f'<svg class="graph" viewBox="0 0 1390 546" role="group" aria-labelledby="model-t"><title id="model-t">Class diagram of DCAT-UK AP</title>'
                f'<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>{s}</svg>'
                '<details><summary>The diagram as a list</summary><ul>' + ''.join(f'<li>{E(p.classes[a]["label"])} has <em>{E(lbl)}</em>: {E(p.classes[b]["label"])}</li>' for a, b, lbl in edges if lbl) + '</ul></details>')

    def explorer(self):
        p = self.p
        rows, attrs = [], []
        for ck, c in p.classes.items():
            for x, prop in p.class_props(ck):
                mem = prop['mem']
                rows.append([f'<a href="properties.html#p-{x["p"]}">{E(prop["label"])}</a>', f'<a href="{self.class_page(ck)}">{E(c["label"])}</a>', f'<code>{E(prop["uri"])}</code>',
                             tag(x['ob']) + (f' {tag("M", "M for critical data assets")}' if x.get('cda') == 'M' and x['ob'] != 'M' else ''), E(x['card']),
                             E(CHANGE_LABEL[mem['change']]) + (' <strong class="tag warn">Provisional</strong>' if prop.get('provisional') else '')])
                attrs.append(f' data-class="{ck}" data-ob="{x["ob"]}{" cda" if x.get("cda") == "M" else ""}" data-change="{mem["change"]}{" prov" if prop.get("provisional") else ""}"')
        sel_c = ''.join(f'<option value="{k}">{E(v["label"])}</option>' for k, v in p.classes.items())
        sel_ch = ''.join(f'<option value="{k}">{E(v)}</option>' for k, v in CHANGE_LABEL.items())
        f = (f'<div class="filters" data-for="explorer"><label>Search<input type="search" placeholder="title, licence, dct:"></label>'
             f'<label>Class<select data-col="class"><option value="">All</option>{sel_c}</select></label>'
             f'<label>Obligation<select data-col="ob"><option value="">All</option><option value="M">Mandatory</option><option value="R">Recommended</option><option value="O">Optional</option><option value="C">Conditional</option><option value="cda">Mandatory for critical data assets</option></select></label>'
             f'<label>Change from xGov MEM<select data-col="change"><option value="">All</option>{sel_ch}<option value="prov">Provisional</option></select></label>'
             f'<button type="button" class="btn secondary small" data-csv="dcat-uk-ap-properties.csv">{icon("download")} Download shown</button><output aria-live="polite"></output></div>')
        return f + table('explorer', 'Every property on every class', ['Property', 'Class', 'IRI', 'Obligation', 'Cardinality', 'Change'], rows, row_attrs=attrs)

    def profile_page(self):
        p, k = self.p, self.counts()
        cards = ''.join(f'<div class="card"><h3>{icon(c["icon"])} <a href="{self.class_page(ck)}">{E(c["label"])}</a></h3><p>{tag(c["ob"])} <code>{E(c["uri"])}</code></p><p>{self.gloss(c["definition"])}</p><p class="small">{len(c["properties"])} properties, {sum(1 for z in c["properties"] if z["ob"] == "M")} mandatory</p></div>' for ck, c in p.classes.items())
        obs = ''.join(f'<dt>{tag(o)}</dt><dd>{E(v["text"])}</dd>' for o, v in p.obligations.items())
        rules = table('t-rules', 'Rules that span more than one property', ['Rule', 'Applies to', 'What it says'],
                      [[E(r['id']), E(p.classes[r['class']]['label']), E(r['text'])] for r in p.rules], sortable=False)
        body = self.hero('layers', 'The profile', 'The profile at a glance', self.gloss(
            f'DCAT-UK AP has {k["classes"]} classes and {k["props"]} properties. Each class lists the properties a record of that kind can have, and whether each is mandatory, recommended, optional or conditional.'))
        body += f'<h2 id="model">How the classes connect</h2><p>Select a class to see its properties. A red outline marks a mandatory class.</p>{self.model_svg()}'
        body += f'<h2 id="classes">Classes</h2><div class="grid">{cards}</div>'
        body += f'<h2 id="obligations">What the obligations mean</h2><dl class="facts">{obs}</dl><p>A record <a class="term" href="knowledge.html#g-conformance">conforms</a> when it meets every mandatory and conditional rule. When the record describes a critical data asset, more properties become mandatory: they are marked "M for critical data assets".</p>'
        body += f'<h2 id="rules">Rules</h2>{rules}'
        body += f'<h2 id="explorer-h">Explore every property</h2><p>Filter by class, obligation or what changed since the xGov MEM. Sort by any column.</p>{self.explorer()}'
        drawer = [{'title': 'The profile', 'icon': 'layers', 'items': [{'id': 'model', 'label': 'Class diagram', 'icon': 'network'}, {'id': 'classes', 'label': 'Classes', 'icon': 'boxes', 'count': k['classes']},
                   {'id': 'obligations', 'label': 'Obligations', 'icon': 'scale'}, {'id': 'rules', 'label': 'Rules', 'icon': 'list-checks', 'count': k['rules']},
                   {'id': 'explorer-h', 'label': 'Explore properties', 'icon': 'filter', 'count': k['uses']}]},
                  {'title': 'Classes', 'icon': 'boxes', 'items': [{'id': 'classes', 'label': c['label'], 'icon': c['icon']} for c in p.classes.values()]}]
        self.page('profile', body, drawer, crumbs=[('The profile', None)])
        for ck, c in p.classes.items():
            self.add_search(c['label'], 'Class', self.class_page(ck), c['definition'])

    def prop_block(self, key, prop, ck=None, x=None, used=None):
        mem = prop['mem']
        issues = ' '.join(f'<a href="changes.html#issue-{n}">#{n}</a>' for n in prop.get('issues', []))
        cl = prop.get('codelist')
        cl_link = ''
        if cl == 'organisations':
            cl_link = '<a href="codelists.html#orgs">GOV.UK organisations</a>'
        elif cl:
            cl_link = f'<a href="codelists.html#cl-{cl}">{E(self.p.codelists[cl]["label"])}</a>'
        rng = prop.get('range')
        facts = [('IRI', f'<code>{E(prop["uri"])}</code>'), ('Value', E(prop['kind']) + (f': <a href="{self.class_page(rng)}">{E(self.p.classes[rng]["label"])}</a>' if rng else '') + (f', from {cl_link}' if cl_link else ''))]
        if x:
            facts.insert(0, ('Obligation', tag(x['ob']) + (f' {tag("M", "Mandatory for critical data assets")}' if x.get('cda') == 'M' and x['ob'] != 'M' else '') + (f' {E(x["condition"])}' if x.get('condition') else '')))
            facts.insert(1, ('Cardinality', E(x['card'])))
        for f, lbl in (('purpose', 'Why it matters'), ('distinct_from', 'Not to be confused with'), ('guidance', 'How to fill it in')):
            if prop.get(f):
                facts.append((lbl, self.gloss(prop[f], used)))
        if prop.get('example'):
            facts.append(('Example', f'<code>{E(prop["example"])}</code>'))
        if prop.get('max_length'):
            facts.append(('Limit', f'{prop["max_length"]} characters'))
        lin = f'{E(CHANGE_LABEL[mem["change"]])}' + (f' (was <code>{E(mem["slot"])}</code>)' if mem.get('slot') and mem['slot'] != key else '') + (f'. {E(mem["note"])}' if mem.get('note') else '')
        facts.append(('Since the xGov MEM', lin))
        alts = []
        if prop.get('rma2026'):
            alts.append(f'2026 guidance: <code>{E(prop["rma2026"])}</code>')
        if prop.get('dm'):
            alts.append(f'Data Marketplace: <code>{E(prop["dm"])}</code>')
        if generate.SCHEMA_ORG.get(key):
            alts.append(f'schema.org: <code>{E(generate.SCHEMA_ORG[key])}</code> {prov("K")}')
        if alts:
            facts.append(('Also known as', '; '.join(alts)))
        if issues:
            facts.append(('Backlog', issues))
        if ck is None:
            on = [c2 for c2, c in self.p.classes.items() if any(z['p'] == key for z in c['properties'])]
            facts.append(('Used on', ', '.join(f'<a href="{self.class_page(c2)}#p-{key}">{E(self.p.classes[c2]["label"])}</a>' for c2 in on)))
        dl = ''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a, b in facts)
        prov_tag = ' <strong class="tag warn">Provisional</strong>' if prop.get('provisional') else ''
        return (f'<section class="prop" id="p-{key}" aria-labelledby="p-{key}-h"><h3 id="p-{key}-h">{E(prop["label"])}{prov_tag} <span class="uri">{E(prop["uri"])}</span></h3>'
                f'<p>{self.gloss(prop["definition"], used)}</p><dl class="facts">{dl}</dl></section>')

    def class_detail(self, ck):
        p = self.p
        c = p.classes[ck]
        groups = {o: [] for o in 'MCRO'}
        for x, prop in p.class_props(ck):
            groups[x['ob']].append((x, prop))
        used = set()
        body = self.hero(c['icon'], f'Class · {OB_LABEL[c["ob"]]}', c['label'], self.gloss(c['definition']),
                         meta=[('code-xml', f'<code>{E(c["uri"])}</code>'), ('list-checks', f'{len(c["properties"])} properties'),
                               ('history', f'xGov MEM: {E(c["mem"]) if c["mem"] else "new class"}')])
        summary = table('cls-sum', f'Properties of {E(c["label"].lower())}', ['Property', 'Obligation', 'Cardinality', 'Value'],
                        [[f'<a href="#p-{x["p"]}">{E(prop["label"])}</a>', tag(x['ob']) + (f' {tag("M", "M for critical data assets")}' if x.get('cda') == 'M' and x['ob'] != 'M' else ''), E(x['card']), E(prop['kind'])] for x, prop in p.class_props(ck)])
        body += f'<h2 id="summary">Summary</h2>{summary}'
        if any(x.get('cda') for x in c['properties']):
            cda = [(x, prop) for x, prop in p.class_props(ck) if x.get('cda') == 'M' and x['ob'] != 'M']
            body += (f'<h2 id="cda">Critical data assets</h2><div class="panel notice"><p>When <a href="#p-criticalDataAsset">critical data asset</a> is true, these become mandatory, '
                     f'as the <a href="{E(self.src["rma2026"]["url"])}">April 2026 guidance</a> and the Data Asset Management Policy ask:</p>'
                     + ul([f'<a href="#p-{x["p"]}">{E(prop["label"])}</a>' for x, prop in cda]) + '</div>')
        items = []
        for o in 'MCRO':
            if not groups[o]:
                continue
            body += f'<h2 id="ob-{o}">{OB_LABEL[o]} properties</h2>'
            for x, prop in groups[o]:
                body += self.prop_block(x['p'], prop, ck, x, used)
            items.append({'id': f'ob-{o}', 'label': OB_LABEL[o], 'icon': 'list-checks', 'count': len(groups[o])})
        ex = [e for e in p.examples if e['record']['class'] == ck]
        if ex:
            body += '<h2 id="examples">Examples</h2>' + ul([f'<a href="examples.html#ex-{e["key"]}">{E(e["label"])}</a>' for e in ex])
        drawer = [{'title': c['label'], 'icon': c['icon'], 'items': [{'id': 'summary', 'label': 'Summary', 'icon': 'table-2'}] + ([{'id': 'cda', 'label': 'Critical data assets', 'icon': 'badge-check'}] if any(x.get('cda') for x in c['properties']) else []) + items + ([{'id': 'examples', 'label': 'Examples', 'icon': 'file-code-2', 'count': len(ex)}] if ex else [])},
                  {'title': 'Other classes', 'icon': 'boxes', 'items': []}]
        key = f'class-{slug(ck)}'
        TITLES[key] = c['label']
        DESC[key] = f'The {c["label"].lower()} class in DCAT-UK AP: {c["definition"]}'
        drawer.pop()
        self.page(key, body, drawer, crumbs=[('The profile', 'profile.html'), (c['label'], None)])

    def properties_page(self):
        p = self.p
        used = set()
        letters = {}
        for k, v in sorted(p.props.items(), key=lambda kv: kv[1]['label'].lower()):
            letters.setdefault(v['label'][0].upper(), []).append(k)
        body = self.hero('list-checks', 'The profile', 'Every property', self.gloss(f'All {len(p.props)} properties in alphabetical order, with what they mean, why they matter, how to fill them in and where they came from.'))
        for L, keys in letters.items():
            body += f'<h2 id="l-{L}">{L}</h2>'
            for k in keys:
                body += self.prop_block(k, p.props[k], used=used)
                self.add_search(p.props[k]['label'], 'Property', f'properties.html#p-{k}', p.props[k]['uri'] + ' ' + p.props[k]['definition'])
        drawer = [{'title': 'A to Z', 'icon': 'list-checks', 'items': [{'id': f'l-{L}', 'label': L, 'icon': 'chevron-right', 'count': len(v)} for L, v in letters.items()]}]
        self.page('properties', body, drawer, crumbs=[('The profile', 'profile.html'), ('Every property', None)])

    def codelists_page(self):
        p = self.p
        body = self.hero('tags', 'The profile', 'Codelists', self.gloss('Fixed lists of values, so the same thing is always recorded the same way. Each value has a web identifier, and most are mapped to the EU vocabularies DCAT-AP uses.'))
        items = []
        for sk, s in p.codelists.items():
            rows = []
            for c in s['concepts']:
                m = c.get('maps') or {}
                match = ''
                if m.get('exact') or m.get('close'):
                    match = ('exact: ' if m.get('exact') else 'close: ') + f'<code>{E(m.get("exact") or m.get("close"))}</code>' + prov(s.get('mapping_prov') or c['maps'].get('prov', 'K'))
                rows.append([E(c['label']), f'<code>{E(p.concept_iri(sk, c["code"]))}</code>', self.gloss(c.get('definition', '')) + (f' <span class="small">{E(c["note"])}</span>' if c.get('note') else ''),
                             f'<code>{E(c["mem"])}</code>' if c.get('mem') else '', match])
                self.add_search(c['label'], f'Value in {s["label"]}', f'codelists.html#cl-{sk}', c.get('definition', ''))
            note = []
            if s.get('external'):
                note.append(f'This list belongs to someone else: <a href="{E(s["scheme_uri"])}">{E(s["scheme_uri"])}</a>. The profile lists the values it expects.')
            if s.get('provisional'):
                note.append('<strong class="tag warn">Provisional</strong> Pending research.')
            if s.get('source'):
                note.append(f'Source: <a href="{E(s["source"])}">{E(s["source"])}</a>{prov(s.get("source_prov", "K"), self.m["verified_on"])}' + (f'. Definitions {prov(s["definitions_prov"])}' if s.get('definitions_prov') else ''))
            if s.get('withdrawn'):
                note.append('Withdrawn from the xGov MEM: ' + '; '.join(f'<code>{E(w["mem"])}</code> ({E(w["reason"])})' for w in s['withdrawn']))
            body += (f'<section id="cl-{sk}" aria-labelledby="cl-{sk}-h"><h2 id="cl-{sk}-h">{E(s["label"])}</h2><p>{self.gloss(s["definition"])}</p>'
                     + (''.join(f'<p class="small">{n}</p>' for n in note))
                     + table(f't-{sk}', f'{E(s["label"])}: {len(s["concepts"])} values', ['Value', 'Identifier', 'Meaning', 'xGov MEM value', 'EU match'], rows) + '</section>')
            items.append({'id': f'cl-{sk}', 'label': s['label'], 'icon': 'tags', 'count': len(s['concepts'])})
            self.add_search(s['label'], 'Codelist', f'codelists.html#cl-{sk}', s['definition'])
        o = p.orgs or {'orgs': [], 'count': 0}
        rows = [[E(x['title']), f'<code>{E(x["slug"])}</code>', E(x['type']), E(x['status'])] for x in o['orgs']]
        attrs = [f' data-status="{E(x["status"])}"' for x in o['orgs']]
        body += (f'<section id="orgs" aria-labelledby="orgs-h"><h2 id="orgs-h">Organisations</h2><p>Publisher and creator use the organisation’s GOV.UK address. This list of {o["count"]:,} organisations was read from the '
                 f'<a href="{E(o.get("source", ""))}">GOV.UK organisations API</a> on {E(o.get("read", ""))} by the GitHub Repos Asset Catalogue, and reused here {prov("P")}. '
                 'Closed organisations are kept so records that name them still resolve after machinery of government changes. Bodies not on GOV.UK can use their own register address.</p>'
                 '<div class="filters" data-for="t-orgs"><label>Search<input type="search" placeholder="name or slug"></label><label>Status<select data-col="status"><option value="">All</option><option value="live">Live</option><option value="closed">Closed</option><option value="exempt">Exempt</option><option value="joining">Joining</option><option value="transitioning">Transitioning</option></select></label><output aria-live="polite"></output></div>'
                 + table('t-orgs', f'GOV.UK organisations ({o["count"]:,})', ['Organisation', 'Slug', 'Type', 'Status'], rows, row_attrs=attrs) + '</section>')
        items.append({'id': 'orgs', 'label': 'Organisations', 'icon': 'building-2', 'count': o['count']})
        self.page('codelists', body, [{'title': 'Codelists', 'icon': 'tags', 'items': items}], crumbs=[('The profile', 'profile.html'), ('Codelists', None)])

    def builder_page(self):
        p = self.p
        opts = ''.join(f'<option value="{k}">{E(v["label"])}</option>' for k, v in p.classes.items() if k in ('Dataset', 'DataService', 'Distribution', 'DatasetSeries', 'Catalogue'))
        exs = ''.join(f'<option value="{E(e["key"])}">{E(e["label"])}</option>' for e in p.examples)
        orgs = ''.join(f'<option value="{E(o["uri"])}">{E(o["title"])}</option>' for o in (p.orgs or {'orgs': []})['orgs'] if o['status'] == 'live')
        body = self.hero('pencil-ruler', 'Tools', 'Build a record', self.gloss('Fill in the fields to build a record that conforms to DCAT-UK AP. Checks run as you type. Nothing leaves your browser: download the record when you are done.'))
        body += f'''<noscript><div class="panel warning"><p>The record builder needs JavaScript. You can still read the <a href="profile.html">profile</a> and copy the <a href="examples.html">examples</a>.</p></div></noscript>
<div class="builder"><form id="builder-form" novalidate aria-labelledby="b-h"><h2 id="b-h">Your record</h2>
<div class="field"><label for="b-example">Start from an example (optional)</label><select id="b-example"><option value="">A blank record</option>{exs}</select></div>
<div class="field"><label for="b-class">What are you describing?</label><select id="b-class">{opts}</select></div>
<div class="field"><label for="b-id">Web address that identifies it (optional)</label><p class="hint" id="b-id-h">A stable address for the record, such as its page in your catalogue.</p><input type="url" id="b-id" aria-describedby="b-id-h" placeholder="https://"></div>
<div class="field C"><label><input type="checkbox" id="b-cda"> This is a critical data asset</label><p class="hint">Under the Data Asset Management Policy. More properties become mandatory.</p></div>
<div id="b-fields"></div><datalist id="orgs-list">{orgs}</datalist></form>
<aside class="sticky" aria-labelledby="b-res-h"><h2 id="b-res-h">Checks</h2><div id="b-status" aria-live="polite"></div>
<p class="small" id="b-m-t"></p><div class="meter" aria-hidden="true"><span id="b-m"></span></div><p class="small" id="b-r-t"></p><div class="meter" aria-hidden="true"><span id="b-r"></span></div>
<ul class="results" id="b-issues"></ul>
<div class="tabs" id="b-tabs"><div role="tablist" aria-label="Output format"><button role="tab" id="t-json" aria-controls="o-json">JSON</button><button role="tab" id="t-jsonld" aria-controls="o-jsonld">JSON-LD</button><button role="tab" id="t-ttl" aria-controls="o-ttl">Turtle</button></div>
<div role="tabpanel" id="o-json" aria-labelledby="t-json" tabindex="0"><pre id="b-json" tabindex="0"></pre><p class="btns"><button type="button" class="btn small" data-dl="json">{icon("download")} Download JSON</button><button type="button" class="btn secondary small" data-copy="b-json">Copy</button></p></div>
<div role="tabpanel" id="o-jsonld" aria-labelledby="t-jsonld" tabindex="0" hidden><pre id="b-jsonld" tabindex="0"></pre><p class="btns"><button type="button" class="btn small" data-dl="jsonld">{icon("download")} Download JSON-LD</button><button type="button" class="btn secondary small" data-copy="b-jsonld">Copy</button></p></div>
<div role="tabpanel" id="o-ttl" aria-labelledby="t-ttl" tabindex="0" hidden><pre id="b-ttl" tabindex="0"></pre><p class="btns"><button type="button" class="btn small" data-dl="ttl">{icon("download")} Download Turtle</button><button type="button" class="btn secondary small" data-copy="b-ttl">Copy</button></p></div></div>
<p class="small">The same rules as the published <a href="downloads.html">SHACL shapes</a>. The tests hold the two to the same verdict.</p></aside></div>'''
        self.page('builder', body, None, crumbs=[('Tools', None), ('Build a record', None)], scripts=('validator.js', 'profile-data.js'))

    def validate_page(self):
        p = self.p
        mem_sample = (ROOT / 'tests' / 'fixtures' / 'mem-dataset.yaml').read_text(encoding='utf-8').split('\n', 2)[2]
        # the published sample carries no email address (COL-02): the MEM's contact email is swapped for a web address
        mem_sample = re.sub(r'  email: .*\n', '  address: https://www.ordnancesurvey.co.uk/contact-us\n', mem_sample)
        ap_sample = json.dumps(p.examples[0]['record'], indent=2, ensure_ascii=False)
        body = self.hero('clipboard-check', 'Tools', 'Check records', self.gloss('Paste one record, or a list of records, as JSON, or as YAML in the xGov MEM form. The check runs in your browser; nothing is uploaded.'))
        body += f'''<noscript><div class="panel warning"><p>Checking in the browser needs JavaScript. You can check records with the <a href="downloads.html">SHACL shapes or JSON Schema</a> in your own tools.</p></div></noscript>
<form id="validate-form" novalidate aria-labelledby="v-h" onsubmit="return false"><h2 id="v-h">Your records</h2>
<div class="field"><label for="v-mode">What are you pasting?</label><select id="v-mode"><option value="ap">A DCAT-UK AP record (compact JSON)</option><option value="mem">An xGov MEM record, to convert and check</option></select></div>
<div class="field"><label for="v-input">Record</label><p class="hint" id="v-input-h">JSON, or simple YAML for xGov MEM records.</p><textarea id="v-input" aria-describedby="v-input-h" spellcheck="false"></textarea></div>
<p class="btns"><button type="button" class="btn" id="v-run">{icon("clipboard-check")} Check</button><button type="button" class="btn secondary" data-sample="s-ap" data-mode="ap">Try a DCAT-UK AP example</button><button type="button" class="btn secondary" data-sample="s-mem" data-mode="mem">Try an xGov MEM example</button></p></form>
<div id="v-out" aria-live="polite"></div>
<h2 id="how">How the check works</h2><p>It applies every obligation, cardinality, codelist and rule in the profile, using the same <a href="downloads/profile.json">profile file</a> the SHACL shapes are generated from. Converting an xGov MEM record uses the <a href="changes.html#crosswalk">crosswalk</a>, and lists what it changed.</p>
<details><summary>The DCAT-UK AP example</summary><pre id="s-ap" tabindex="0">{E(ap_sample)}</pre></details>
<details><summary>The xGov MEM example</summary><pre id="s-mem" tabindex="0">{E(mem_sample)}</pre></details>'''
        body = body.replace(' onsubmit="return false"', '')
        self.page('validate', body, None, crumbs=[('Tools', None), ('Check records', None)], scripts=('validator.js', 'profile-data.js'))

    def examples_page(self):
        p = self.p
        body = self.hero('file-code-2', 'Tools', 'Worked examples', self.gloss('Each example passes the SHACL shapes, the JSON Schema and the browser validator on every build. They are illustrative, built from public records, and not confirmed by the publishers. Synthetic examples say so.'))
        items = []
        for e in p.examples:
            k = e['key']
            ttl = self.files[f'examples/{k}.ttl']
            js = self.files[f'examples/{k}.json']
            iss = ' '.join(f'<a href="changes.html#issue-{n}">#{n}</a>' for n in e.get('issues', []))
            body += (f'<section id="ex-{k}" aria-labelledby="ex-{k}-h"><h2 id="ex-{k}-h">{E(e["label"])}</h2><p>{self.gloss(e["teaches"])}</p>'
                     f'<p class="small">Class: <a href="{self.class_page(e["record"]["class"])}">{E(p.classes[e["record"]["class"]]["label"])}</a>{" · Backlog: " + iss if iss else ""} {prov("U")}</p>'
                     f'<div class="tabs" id="tabs-{k}"><div role="tablist" aria-label="Format of {E(e["label"].lower())}">'
                     f'<button role="tab" id="t-{k}-j" aria-controls="p-{k}-j">JSON</button><button role="tab" id="t-{k}-t" aria-controls="p-{k}-t">Turtle</button></div>'
                     f'<div role="tabpanel" id="p-{k}-j" aria-labelledby="t-{k}-j" tabindex="0"><pre id="c-{k}-j" tabindex="0">{E(js)}</pre><p class="btns"><button type="button" class="btn secondary small" data-copy="c-{k}-j">Copy</button><a class="btn secondary small" href="downloads/examples/{k}.json" download>{icon("download")} JSON</a><a class="btn secondary small" href="downloads/examples/{k}.jsonld" download>JSON-LD</a></p></div>'
                     f'<div role="tabpanel" id="p-{k}-t" aria-labelledby="t-{k}-t" tabindex="0" hidden><pre id="c-{k}-t" tabindex="0">{E(ttl)}</pre><p class="btns"><button type="button" class="btn secondary small" data-copy="c-{k}-t">Copy</button><a class="btn secondary small" href="downloads/examples/{k}.ttl" download>{icon("download")} Turtle</a></p></div></div>'
                     f'<p><a href="builder.html">Open it in the record builder</a> by choosing it under "Start from an example".</p></section>')
            items.append({'id': f'ex-{k}', 'label': e['label'], 'icon': 'file-code-2'})
            self.add_search(e['label'], 'Example', f'examples.html#ex-{k}', e['teaches'])
        self.page('examples', body, [{'title': 'Examples', 'icon': 'file-code-2', 'items': items}], crumbs=[('Tools', None), ('Worked examples', None)])

    def changes_page(self):
        p = self.p
        lin = p.lineage
        k = self.counts()
        # crosswalk
        rows, attrs = [], []
        for key, v in sorted(p.props.items(), key=lambda kv: (kv[1]['mem'].get('slot') is None, kv[1]['mem'].get('slot') or kv[0])):
            mem = v['mem']
            rows.append([f'<code>{E(mem["slot"])}</code>' if mem.get('slot') else '<span class="small">(none)</span>', f'<a href="properties.html#p-{key}">{E(v["label"])}</a> <code>{E(v["uri"])}</code>',
                         E(CHANGE_LABEL[mem['change']]), E(mem.get('note', ''))])
            attrs.append(f' data-change="{mem["change"]}"')
        rows.append(['<code>type</code>', 'The class (rdf:type)', 'Merged', 'The class of a record gives its type; there is no separate type property.'])
        attrs.append(' data-change="merged"')
        sel = ''.join(f'<option value="{a}">{E(b)}</option>' for a, b in CHANGE_LABEL.items())
        cw = (f'<div class="filters" data-for="t-cw"><label>Search<input type="search"></label><label>Change<select data-col="change"><option value="">All</option>{sel}</select></label>'
              f'<button type="button" class="btn secondary small" data-csv="crosswalk-mem.csv">{icon("download")} Download shown</button><output aria-live="polite"></output></div>'
              + table('t-cw', f'xGov MEM to DCAT-UK AP ({k["mem_slots"]} xGov MEM properties mapped, {k["new"]} new)', ['xGov MEM', 'DCAT-UK AP', 'Change', 'Why'], rows, row_attrs=attrs))
        # backlog
        brow, battrs = [], []
        for b in lin['backlog']:
            lbl, cls = STATUS_LABEL[b['status']]
            where = ', '.join(self.where_link(w) for w in b.get('where', []))
            brow.append([f'<a id="issue-{b["n"]}" href="{E(lin["source"])}/{b["n"]}">#{b["n"]}</a>', E(b['title']), f'<strong class="tag {cls}">{lbl}</strong>', self.gloss(b['resolution'].strip()), where])
            battrs.append(f' data-status="{b["status"]}"')
            self.add_search(f'Issue {b["n"]}: {b["title"]}', 'Backlog item', f'changes.html#issue-{b["n"]}', b['resolution'])
        bl = ('<div class="filters" data-for="t-bl"><label>Search<input type="search"></label><label>Status<select data-col="status"><option value="">All</option>'
              + ''.join(f'<option value="{a}">{E(b[0])}</option>' for a, b in STATUS_LABEL.items()) + f'</select></label><button type="button" class="btn secondary small" data-csv="backlog.csv">{icon("download")} Download shown</button><output aria-live="polite"></output></div>'
              + table('t-bl', f'Every open xGov MEM issue ({len(lin["backlog"])}), and how it was dealt with', ['Issue', 'Title', 'Status', 'How it was dealt with', 'Where'], brow, row_attrs=battrs))
        kept = table('t-kept', 'Closed issues whose outcome the profile keeps', ['Issue', 'Title', 'Kept'], [[f'<a id="issue-{c["n"]}" href="{E(lin["source"])}/{c["n"]}">#{c["n"]}</a>', E(c['title']), E(c['kept'])] for c in lin['closed_kept']], sortable=False)
        prs = table('t-prs', 'Open pull requests in the xGov MEM repository', ['Pull request', 'What it does', 'Status', 'Why'], [[f'#{E(x["n"])}', E(x['title']), f'<strong class="tag brand">{STATUS_LABEL[x["status"]][0]}</strong>', E(x['note'])] for x in lin['open_prs']], sortable=False)
        # DCAT-AP alignment
        need = {'Catalogue': ['publisher', 'description', 'title'], 'CatalogueRecord': ['modified', 'primaryTopic'], 'Dataset': ['title', 'description'],
                'DatasetSeries': ['title', 'description'], 'Distribution': ['accessURL'], 'DataService': ['title', 'endpointURL'], 'Agent': ['name'],
                'Checksum': ['algorithm', 'checksumValue'], 'Relationship': ['hadRole', 'relation']}
        arows = []
        for ck, props in need.items():
            obs = {x['p']: x['ob'] for x in p.classes[ck]['properties']}
            extra = [p.props[x['p']]['label'] for x in p.classes[ck]['properties'] if x['ob'] == 'M' and x['p'] not in props]
            arows.append([E(p.classes[ck]['label']), ', '.join(E(p.props[x]['label']) for x in props), 'Yes' if all(obs.get(x) == 'M' for x in props) else 'No', E(', '.join(extra) or 'None')])
        ap = table('t-ap', 'DCAT-AP 3.0.1 mandatory properties, and what the UK adds', ['Class', 'Mandatory in DCAT-AP 3.0.1', 'Mandatory here too', 'Also mandatory in the UK'], arows, sortable=False)
        # 2026 guidance crosswalk
        rma = [(k2, v) for k2, v in p.props.items() if v.get('rma2026')]
        rrows = [[f'<code>{E(v["rma2026"])}</code>', f'<a href="properties.html#p-{k2}">{E(v["label"])}</a>', E(self.ob_summary(k2))] for k2, v in rma]
        rm = table('t-rma', 'Attributes in "Recording metadata to describe critical data assets" (16 April 2026)', ['Guidance attribute', 'DCAT-UK AP property', 'Obligation here'], rrows)
        dm = [(k2, v) for k2, v in p.props.items() if v.get('dm')]
        drows = [[f'<code>{E(v["dm"])}</code>', f'<a href="properties.html#p-{k2}">{E(v["label"])}</a>', f'<code>{E(v["uri"])}</code>'] for k2, v in dm]
        dmt = table('t-dm', 'Data Marketplace JSON Schema properties (co-cddo/data-catalogue-metadata, read 6 November 2026)', ['Data Marketplace', 'DCAT-UK AP', 'IRI'], drows)
        body = self.hero('git-pull-request', "What's changed", "What's changed from the xGov MEM", self.gloss(
            f'Every property of the xGov MEM maps to the profile, so existing records convert automatically. {k["resolved"]} of the {k["backlog"]} open backlog items are resolved here; the rest need the owner. {k["new"]} properties are new, mostly from that backlog.'))
        body += '<h2 id="summary">In summary</h2>' + ul([
            'Built on the DCAT 3 Recommendation instead of a working draft, and aligned with DCAT-AP 3.0.1 so records harvest into European tools.',
            'Every bug in the backlog is fixed: the contact point definition, the distribution range, the missing security classification IRI, the wrong example publisher and the title case examples.',
            'New requirements from the working group are in: geographic coverage, time period, schema, personal data, sensitive data, reference data and who can see a record.',
            'Critical data assets get their own mandatory properties, from the April 2026 guidance.',
            'Codelists are linked data, mapped to EU vocabularies. Themes use the data.gov.uk topics.',
            'Contact points prefer a contact form and never name a person.',
            'Release management: semantic versions, a change request form, release assets and a release gate.'])
        body += f'<h2 id="crosswalk">The crosswalk</h2><p>Download as <a href="downloads/crosswalk-mem.csv">CSV</a>. To convert records, use <a href="validate.html">Check records</a>.</p>{cw}'
        body += f'<h2 id="backlog">The backlog</h2><p>Read from the xGov MEM repository on {E(lin["read_on"])} {prov("V", lin["read_on"])}: {lin["totals"]["items"]} issues and pull requests, of which {lin["totals"]["issues_open"]} issues and {lin["totals"]["prs_open"]} pull requests were open. Contributors are not named.</p>{bl}{kept}{prs}'
        body += f'<h2 id="dcatap">Alignment with DCAT-AP</h2><p>The UK profile keeps every mandatory property of {self.src_link("dcatap")}, so any record that conforms here is a valid DCAT-AP record for those properties. It adds UK requirements on top.</p>{ap}'
        body += f'<h2 id="guidance">The 2026 guidance for critical data assets</h2><p>{self.src_link("rma2026")}. The guidance does not label every attribute; the obligations here follow its wording and its list of mandatory information.</p>{rm}'
        body += f'<h2 id="marketplace">The Data Marketplace schema</h2><p>{self.src_link("dm")}.</p>{dmt}'
        drawer = [{'title': "What's changed", 'icon': 'git-pull-request', 'items': [
            {'id': 'summary', 'label': 'In summary', 'icon': 'list-checks'}, {'id': 'crosswalk', 'label': 'Crosswalk', 'icon': 'split', 'count': len(rows)},
            {'id': 'backlog', 'label': 'Backlog', 'icon': 'clipboard-list', 'count': len(lin['backlog'])}, {'id': 'dcatap', 'label': 'DCAT-AP', 'icon': 'globe'},
            {'id': 'guidance', 'label': '2026 guidance', 'icon': 'landmark', 'count': len(rma)}, {'id': 'marketplace', 'label': 'Data Marketplace', 'icon': 'boxes', 'count': len(dm)}]}]
        self.page('changes', body, drawer, crumbs=[("What's changed", None)])

    def ob_summary(self, key):
        out = []
        for ck, c in self.p.classes.items():
            for x in c['properties']:
                if x['p'] == key and ck in ('Dataset', 'DataService', 'Distribution'):
                    out.append(f'{c["label"]}: {OB_LABEL[x["ob"]]}' + (' (M for critical data assets)' if x.get('cda') == 'M' and x['ob'] != 'M' else ''))
        return '; '.join(out)

    def where_link(self, w):
        kind, _, ref = w.partition(':')
        if kind == 'prop':
            return f'<a href="properties.html#p-{ref}">{E(self.p.props[ref]["label"])}</a>'
        if kind == 'class':
            return f'<a href="{self.class_page(ref)}">{E(self.p.classes[ref]["label"])}</a>'
        if kind == 'codelist':
            return f'<a href="codelists.html#cl-{ref}">{E(self.p.codelists[ref]["label"])}</a>'
        if kind == 'example':
            return f'<a href="examples.html#ex-{ref}">example</a>'
        if kind == 'page':
            return f'<a href="{ref}.html">{E(TITLES.get(ref, ref))}</a>'
        if kind == 'adr':
            return f'<a href="governance.html#adr-{ref}">ADR {E(ref)}</a>'
        if kind == 'check':
            return f'<a href="governance.html#checks">{E(ref)}</a>'
        return E(w)

    def strategy_page(self):
        c = self.c
        rows = [[self.src_link(s['src']), self.gloss(s['serves'])] for s in c['strategy']]
        st = table('t-st', 'What each strategy needs, and how the profile serves it', ['Strategy or policy', 'How the profile serves it'], rows, sortable=False)
        layers = ''.join(f'<li><strong>{E(l["title"])}</strong>{" (this profile)" if l.get("here") else ""}: {E(l["text"])}</li>' for l in reversed(c['infrastructure_layers']))
        nrows = [[E(n['nation']), E(n['applies']), E(n['languages']), E(n['notes'])] for n in c['nations']]
        nt = table('t-nations', 'What applies in each nation', ['Nation', 'What applies', 'Languages to record', 'Notes'], nrows, sortable=False)
        others = ''.join(f'<li><a href="{E(o["url"])}">{E(o["title"])}</a>: {E(o["note"])} {prov("K")}</li>' for o in self.p.lineage['other_models'])
        srcs = table('t-src', 'Sources, in order of precedence', ['Source', 'Publisher', 'Date', 'Role'], [[self.src_link(s['id']), E(s['publisher']), E(s['date']), E(s['role'])] for s in self.p.lineage['sources']])
        body = self.hero('route', 'Strategy', 'How it fits the strategy', self.gloss('The profile is one small part of a bigger plan: making public sector data easy to find and use across the UK. This page shows which parts of that plan it serves, and where its limits are.'))
        body += f'<h2 id="serves">What it serves</h2>{st}'
        body += f'<h2 id="layers">A pan-UK public data infrastructure</h2><p>Read from the top, people find data; read from the bottom, bodies keep their own data and describe it once. The layers are the author’s model, drawn from the sources below {prov("K")}.</p><ol>{layers}</ol>'
        body += f'<h2 id="nations">Four nations</h2><p>England-only rules are not presented as UK-wide. Check each nation’s position before relying on it {prov("K")}.</p>{nt}'
        body += ('<h2 id="limits">Limits</h2>' + ul(['The profile describes data; it does not move it, grant access to it or check its quality.',
                                                      'The Data Asset Management Policy names no metadata standard. Using this profile for returns needs a decision by the owning team.',
                                                      'The strategic roadmap for public sector data had not been published when this was written. When it is, check this page against it.',
                                                      'Mappings marked K need a specialist review before endorsement.']))
        body += f'<h2 id="others">Related profiles and models</h2><ul>{others}</ul>'
        body += f'<h2 id="sources">Sources</h2>{srcs}'
        drawer = [{'title': 'Strategy', 'icon': 'route', 'items': [{'id': 'serves', 'label': 'What it serves', 'icon': 'target', 'count': len(c['strategy'])}, {'id': 'layers', 'label': 'Infrastructure layers', 'icon': 'layers'},
                   {'id': 'nations', 'label': 'Four nations', 'icon': 'map', 'count': len(c['nations'])}, {'id': 'limits', 'label': 'Limits', 'icon': 'triangle-alert'},
                   {'id': 'others', 'label': 'Related profiles', 'icon': 'link'}, {'id': 'sources', 'label': 'Sources', 'icon': 'scroll-text', 'count': len(self.p.lineage['sources'])}]}]
        self.page('strategy', body, drawer, crumbs=[('Strategy', None)])

    def roles_page(self):
        c = self.c
        cards = ''
        for ps in c['personas']:
            route = ''.join(f'<li><a href="{E(h)}">{E(t)}</a></li>' for h, t in ps['route'])
            cards += (f'<section class="card" id="role-{ps["id"]}" aria-labelledby="role-{ps["id"]}-h"><h3 id="role-{ps["id"]}-h">{icon(ps["icon"])} {E(ps["title"])}</h3><p class="small">{E(ps["context"])}</p>'
                      f'<p><strong>Needs:</strong> {E(ps["need"])}</p><p><strong>Worries:</strong> {E(ps["worry"])}</p><p><strong>Your route</strong></p><ol>{route}</ol></section>')
            self.add_search(ps['title'], 'Role', f'roles.html#role-{ps["id"]}', ps['need'])
        deia = ''.join(f'<div class="card"><h3>{icon(d["icon"])} {E(d["title"])}</h3><p>{E(d["text"])}</p></div>' for d in c['deia'])
        easy = ''.join(f'<li>{E(x)}</li>' for x in c['easy_read'])
        display = ('<div class="filters"><label>Text size<select data-display="size"><option value="">Standard</option><option value="large">Large</option></select></label>'
                   '<label>Spacing<select data-display="spacing"><option value="">Standard</option><option value="wide">Wide</option></select></label></div>')
        body = self.hero('users-round', 'Your role', 'Your role', self.gloss('Routes through the profile for the people who record, check, build, buy and use metadata. These are proto-personas: written from the backlog and policy, and not yet tested with users.'))
        body += (f'<h2 id="start">New to metadata?</h2><div class="easy"><h3>{icon("book-open")} Easy Read</h3><ul>{easy}</ul></div>'
                 '<p>A good record answers five questions for the person who finds it: what is this, who looks after it, can I have it, what may I do with it, and who do I ask? '
                 'The <a href="properties.html#p-title">title</a> and <a href="properties.html#p-description">description</a> answer the first; <a href="properties.html#p-publisher">publisher</a> the second; '
                 '<a href="properties.html#p-accessRights">access rights</a> the third; the <a href="properties.html#p-licence">licence</a> the fourth; and the <a href="properties.html#p-contactPoint">contact point</a> the last.</p>')
        body += f'<h2 id="roles">Roles</h2><div class="grid">{cards}</div>'
        body += f'<h2 id="inclusion">Inclusion and accessibility</h2><div class="grid">{deia}</div><h3 id="display">Display options</h3><p>Saved in this browser only.</p>{display}'
        drawer = [{'title': 'Your role', 'icon': 'users-round', 'items': [{'id': 'start', 'label': 'New to metadata?', 'icon': 'book-open'}, {'id': 'roles', 'label': 'Roles', 'icon': 'users-round', 'count': len(c['personas'])},
                   {'id': 'inclusion', 'label': 'Inclusion', 'icon': 'heart-handshake'}, {'id': 'display', 'label': 'Display options', 'icon': 'sliders-horizontal'}]},
                  {'title': 'Roles', 'icon': 'users-round', 'items': [{'id': f'role-{x["id"]}', 'label': x['title'], 'icon': x['icon']} for x in c['personas']]}]
        self.page('roles', body, drawer, crumbs=[('Your role', None)])

    def kg_svg(self):
        """Knowledge graph: classes, codelists, backlog items, sources and portals in rings. Each node links to its page."""
        p = self.p
        nodes, edges = [], []
        def add(nid, label, kind, href):
            nodes.append((nid, label, kind, href))
        for ck, c in p.classes.items():
            add('c:' + ck, c['label'], 'class', self.class_page(ck))
        for sk, s in p.codelists.items():
            add('l:' + sk, s['label'], 'codelist', f'codelists.html#cl-{sk}')
        for b in p.lineage['backlog']:
            add(f'i:{b["n"]}', f'#{b["n"]}', 'issue', f'changes.html#issue-{b["n"]}')
        for s in self.c['strategy']:
            add('s:' + s['src'], SHORT_SRC.get(s['src'], self.src[s['src']]['title'][:24]), 'source', 'strategy.html#serves')
        for pt in self.c['estate']['portals']:
            if pt['id'] != 'ap':
                add('e:' + pt['id'], {'dam': 'DAM playbooks', 'dqc': 'DQ Commons', 'cat': 'Repos catalogue'}[pt['id']], 'portal', 'estate.html')
        ids = {n[0] for n in nodes}
        for ck, c in p.classes.items():
            for x, prop in p.class_props(ck):
                if prop.get('range') and prop['range'] != ck:
                    edges.append(('c:' + ck, 'c:' + prop['range']))
                if prop.get('codelist') and prop['codelist'] in p.codelists:
                    edges.append(('c:' + ck, 'l:' + prop['codelist']))
        for b in p.lineage['backlog']:
            for w in b.get('where', []):
                kind, _, ref = w.partition(':')
                tgt = None
                if kind == 'prop':
                    tgt = next(('c:' + ck for ck, c in p.classes.items() if any(z['p'] == ref for z in c['properties'])), None)
                elif kind == 'class':
                    tgt = 'c:' + ref
                elif kind == 'codelist':
                    tgt = 'l:' + ref
                if tgt in ids:
                    edges.append((f'i:{b["n"]}', tgt))
        for s in self.c['strategy']:
            edges.append(('s:' + s['src'], 'c:Dataset'))
        for pt in self.c['estate']['portals']:
            if pt['id'] != 'ap':
                edges.append(('e:' + pt['id'], 'c:Catalogue'))
        edges = sorted(set((a, b) for a, b in edges if a != b))
        ring = {'class': 115, 'codelist': 230, 'issue': 360, 'source': 430, 'portal': 430}
        groups = {}
        for n in nodes:
            groups.setdefault(n[2] if n[2] not in ('source', 'portal') else 'outer', []).append(n)
        pos = {}
        cx, cy = 560, 500
        for g, ns in groups.items():
            r = ring['source'] + 30 if g == 'outer' else ring[g]
            off = 0.3 if g == 'outer' else 0
            for i, n in enumerate(ns):
                a = off + 2 * math.pi * i / len(ns)
                pos[n[0]] = (round(cx + r * math.cos(a), 1), round(cy + r * math.sin(a), 1))
        s = ''
        for a, b in edges:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            s += f'<line class="edge" data-a="{E(a)}" data-b="{E(b)}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="opacity:.35"/>'
        for nid, label, kind, href in nodes:
            x, y = pos[nid]
            anchor = 'start' if x >= cx else 'end'
            dx = 9 if x >= cx else -9
            s += (f'<g data-n="{E(nid)}" data-k="{kind}"><a href="{E(href)}"><circle class="k-{kind}" cx="{x}" cy="{y}" r="7"/>'
                  f'<text x="{x + dx}" y="{y + 4}" text-anchor="{anchor}">{E(label)}</text></a></g>')
        legend = ''.join(f'<li><label><input type="checkbox" data-kind="{k}" checked> <i style="background:{c}"></i>{E(l)}</label></li>' for k, c, l in
                         (('class', '#1d70b8', 'Classes'), ('codelist', '#00703c', 'Codelists'), ('issue', '#d4351c', 'Backlog items'), ('source', '#b58840', 'Strategy sources'), ('portal', '#912b88', 'Sister portals')))
        svg = f'<svg class="graph" id="kg" viewBox="0 0 1120 1000" role="group" aria-labelledby="kg-t"><title id="kg-t">Knowledge graph of DCAT-UK AP: {len(nodes)} nodes and {len(edges)} links</title>{s}</svg>'
        return f'<ul class="legend" aria-label="Show or hide kinds of node">{legend}</ul>{svg}', nodes, edges

    def knowledge_page(self):
        c, p = self.c, self.p
        g = sorted(c['glossary'], key=lambda t: t['term'].lower())
        gl = ''.join(f'<dt id="g-{t["id"]}">{E(t["term"])}</dt><dd>{E(t["def"])}</dd>' for t in g)
        for t in g:
            self.add_search(t['term'], 'Glossary', f'knowledge.html#g-{t["id"]}', t['def'])
        th_rows = [[E(a), f'<a href="#g-{t["id"]}">{E(t["term"])}</a>'] for t in g for a in t.get('alt', [])]
        th = table('t-th', 'Other words people use, and the term used here', ['If you say', 'This portal says'], sorted(th_rows))
        tax = '<ul>' + ''.join(f'<li><a href="{self.class_page(ck)}">{E(cl["label"])}</a> <code>{E(cl["uri"])}</code><ul>' + ''.join(
            f'<li><a href="properties.html#p-{x["p"]}">{E(p.props[x["p"]]["label"])}</a> {tag(x["ob"], x["ob"])}</li>' for x in cl['properties']) + '</ul></li>' for ck, cl in p.classes.items()) + '</ul>'
        cltax = '<ul>' + ''.join(f'<li><a href="codelists.html#cl-{sk}">{E(s["label"])}</a><ul>' + ''.join(f'<li>{E(x["label"])}</li>' for x in s['concepts']) + '</ul></li>' for sk, s in p.codelists.items()) + '</ul>'
        graph, nodes, edges = self.kg_svg()
        nl = ''.join(f'<li><a href="{E(n[3])}">{E(n[1])}</a> ({E(n[2])})</li>' for n in nodes)
        terms = [f'<li><code>{E(v["uri"])}</code>: {E(v["definition"])}{" (provisional)" if v.get("provisional") else ""}</li>' for v in p.props.values() if v['uri'].startswith('dcatuk:')]
        body = self.hero('network', 'Knowledge', 'Knowledge', self.gloss('The words, structure and connections behind the profile: a glossary, a thesaurus of other words people use, the taxonomy of classes and codelists, the few terms the profile adds, and a graph of how it all connects.'))
        body += f'<h2 id="glossary">Glossary</h2><dl class="facts">{gl}</dl>'
        body += f'<h2 id="thesaurus">Thesaurus</h2>{th}'
        body += f'<h2 id="taxonomy">Taxonomy</h2><div class="tabs" id="tax-tabs"><div role="tablist" aria-label="Taxonomy"><button role="tab" id="tt-c" aria-controls="tp-c">Classes and properties</button><button role="tab" id="tt-l" aria-controls="tp-l">Codelists</button><button role="tab" id="tt-o" aria-controls="tp-o">Terms the profile adds</button></div>'
        body += f'<div role="tabpanel" id="tp-c" aria-labelledby="tt-c" tabindex="0">{tax}</div><div role="tabpanel" id="tp-l" aria-labelledby="tt-l" tabindex="0" hidden>{cltax}</div>'
        body += f'<div role="tabpanel" id="tp-o" aria-labelledby="tt-o" tabindex="0" hidden><p>Everything else is reused from DCAT, Dublin Core, vCard, ADMS, PROV, SPDX, DQV and schema.org. Only these are new, under the proposed namespace <code>{E(self.m["namespace"])}</code>. Download the <a href="downloads/dcat-uk-ap.ns.ttl">definitions</a>.</p><ul>{"".join(terms)}</ul></div></div>'
        body += f'<h2 id="graph">Knowledge graph</h2><p>Classes in the middle, then codelists, then the backlog items that shaped them, with the strategy and the sister portals around the edge. Select a node to go to it; point at it to light up its links.</p>{graph}<details><summary>The same graph as a list</summary><ul>{nl}</ul></details>'
        drawer = [{'title': 'Knowledge', 'icon': 'network', 'items': [{'id': 'glossary', 'label': 'Glossary', 'icon': 'book-open', 'count': len(g)}, {'id': 'thesaurus', 'label': 'Thesaurus', 'icon': 'languages', 'count': len(th_rows)},
                   {'id': 'taxonomy', 'label': 'Taxonomy', 'icon': 'boxes'}, {'id': 'graph', 'label': 'Knowledge graph', 'icon': 'waypoints', 'count': len(nodes)}]}]
        self.page('knowledge', body, drawer, crumbs=[('Knowledge', None)])

    def downloads_page(self):
        p = self.p
        meta = [('dcat-uk-ap.shacl.ttl', 'SHACL shapes', 'Check RDF records with any SHACL engine.', 'text/turtle'),
                ('dcat-uk-ap.schema.json', 'JSON Schema 2020-12', 'Check records in the compact JSON form.', 'application/schema+json'),
                ('dcat-uk-ap.context.jsonld', 'JSON-LD context', 'Turn compact JSON records into RDF.', 'application/ld+json'),
                ('dcat-uk-ap.linkml.yaml', 'LinkML schema', 'For continuity with the xGov MEM toolchain. Not yet checked by LinkML tools.', 'application/yaml'),
                ('dcat-uk-ap.ns.ttl', 'Terms the profile adds', 'RDFS and OWL definitions of the dcatuk: terms.', 'text/turtle'),
                ('codelists.ttl', 'Codelists (SKOS, Turtle)', 'Every UK codelist as a SKOS concept scheme.', 'text/turtle'),
                ('codelists.jsonld', 'Codelists (SKOS, JSON-LD)', 'The same, as JSON-LD.', 'application/ld+json'),
                ('codelists.csv', 'Codelists (CSV)', 'Every value, its identifier and its EU match.', 'text/csv'),
                ('data-dictionary.csv', 'Data dictionary (CSV)', 'Every property on every class with obligations and lineage.', 'text/csv'),
                ('crosswalk-mem.csv', 'xGov MEM crosswalk (CSV)', 'xGov MEM property to DCAT-UK AP property.', 'text/csv'),
                ('backlog.csv', 'Backlog register (CSV)', 'Every xGov MEM backlog item and how it was dealt with.', 'text/csv'),
                ('profile.json', 'Profile for tools (JSON)', 'What the browser validator reads. Also for other tools, such as the Metadata Weaver.', 'application/json'),
                ('organisations.json', 'Organisations (JSON)', 'GOV.UK organisations for publisher and creator.', 'application/json'),
                ('catalog.jsonld', 'This list, as DCAT (JSON-LD)', 'A DCAT-UK AP description of these downloads.', 'application/ld+json'),
                ('catalog.ttl', 'This list, as DCAT (Turtle)', 'The same, as Turtle.', 'text/turtle'),
                ('../xref.json', 'Cross-reference manifest', 'Shared keys for the sister portals: properties, codelists and terms.', 'application/json')]
        self.dl_meta = meta
        rows = [[f'<a href="downloads/{E(f)}" download>{E(t)}</a>', E(d), f'<code>{E(mt)}</code>'] for f, t, d, mt in meta]
        ex_rows = [[E(e['label']), ' · '.join(f'<a href="downloads/examples/{e["key"]}.{x}" download>{x}</a>' for x in ('json', 'jsonld', 'ttl'))] for e in p.examples]
        body = self.hero('download', 'Downloads', 'Downloads and API', self.gloss('Every file is generated from the profile source on each build, so they always agree. They are static files: use the addresses as a simple read-only API.'))
        body += f'<h2 id="files">The profile in every format</h2>' + table('t-dl', 'Files', ['File', 'What it is for', 'Media type'], rows, sortable=False)
        body += f'<h2 id="examples">Examples</h2>' + table('t-ex', 'Worked examples', ['Example', 'Formats'], ex_rows, sortable=False)
        body += (f'<h2 id="tests">Test records for suppliers</h2><p>The repository holds records that must pass (the examples) and records that must fail (<a href="{E(self.m["repo_url"])}/blob/main/tests/fixtures/invalid.yaml">tests/fixtures/invalid.yaml</a>), '
                 f'each naming the rule it breaks. A product that claims conformance should accept every example and reject every failing record. The repository’s own tests hold the SHACL shapes, the JSON Schema and the browser validator to exactly that.</p>')
        body += ('<h2 id="use">How to use them</h2>' + ul([
            'Check a Turtle file: <code>pyshacl -s dcat-uk-ap.shacl.ttl -d record.ttl</code>',
            'Check a compact JSON record: validate it against <code>dcat-uk-ap.schema.json</code> with any Draft 2020-12 validator.',
            'Declare conformance: give your catalogue <code>dct:conformsTo &lt;https://w3id.org/dcat-uk-ap/1.0&gt;</code> once the namespace is registered.']))
        drawer = [{'title': 'Downloads', 'icon': 'download', 'items': [{'id': 'files', 'label': 'Files', 'icon': 'file-down', 'count': len(meta)}, {'id': 'examples', 'label': 'Examples', 'icon': 'file-code-2', 'count': len(p.examples)},
                   {'id': 'tests', 'label': 'Test records', 'icon': 'clipboard-check'}, {'id': 'use', 'label': 'How to use them', 'icon': 'circle-help'}]}]
        self.page('downloads', body, drawer, crumbs=[('Downloads', None)])

    def estate_page(self):
        es = self.c['estate']
        names = {x['id']: x for x in es['portals']}
        order = ['dam', 'dqc', 'cat', 'ap']
        cards = ''.join(f'<div class="card"><p class="caption">{E(x["bearing"])}</p><h3><a href="{E(x["url"])}">{E(x["name"])}</a>{" (this portal)" if x["id"] == "ap" else ""}</h3><p><strong>{E(x["question"])}</strong></p><p class="small">{E(x["status"])}</p></div>' for x in (names[o] for o in order))
        body = self.hero('compass', 'Estate', 'The estate: four portals', self.gloss(es['note']))
        body += f'<h2 id="portals">The four portals</h2><div class="grid">{cards}</div><p>Not sure where to start? The <a href="{E(es["compass"])}">estate compass</a> suggests a route across all four. DCAT-UK AP is its South bearing: the ground everything else stands on, because nothing can be found, governed or improved until it is described.</p>'
        for g in es['comparison']:
            rows = []
            for r in g['rows']:
                cells = [E(r['item'])]
                for o in order:
                    lv, cls = LEVEL[r[o]]
                    cells.append(f'<strong class="tag {cls}">{lv}</strong>' + (f' <span class="small">{E(r["ap_note"])}</span>' if o == 'ap' and r.get('ap_note') else ''))
                rows.append(cells)
            body += f'<h2 id="cmp-{slug(g["group"])}">Compared like for like: {E(g["group"].lower())}</h2>' + table(f't-{slug(g["group"])}', f'{E(g["group"])}, as of {E(es["as_of"])}', ['', 'DAM playbooks', 'DQ Commons', 'Repos catalogue', 'DCAT-UK AP'], rows, sortable=False)
        gains = ''.join(f'<li><strong>{E(names[x["from"]]["name"])} to {E(names[x["to"]]["name"])}:</strong> {E(x["text"])}</li>' for x in es['gains'])
        keys = table('t-keys', 'Shared keys', ['Key', 'Used for', 'Where'], [[E(k['key']), E(k['used_for']), E(k['where'])] for k in es['shared_keys']], sortable=False)
        jr = ''.join(f'<li><strong>{E(j["title"])}:</strong> ' + ' then '.join(f'<a href="{E(names[a]["url"])}">{E(names[a]["name"])}</a> ({E(t)})' for a, t in j['steps']) + '</li>' for j in es['journeys'])
        body += f'<h2 id="gains">What each gains from the others</h2><ul>{gains}</ul><h2 id="shared-keys">Shared keys</h2><p>Published in <a href="xref.json">xref.json</a>, in the same shape as the sister portals’ manifests.</p>{keys}<h2 id="journeys">Journeys across portals</h2><ul>{jr}</ul>'
        drawer = [{'title': 'Estate', 'icon': 'compass', 'items': [{'id': 'portals', 'label': 'The four portals', 'icon': 'compass', 'count': 4}] + [{'id': f'cmp-{slug(g["group"])}', 'label': g['group'], 'icon': 'table-2', 'count': len(g['rows'])} for g in es['comparison']]
                   + [{'id': 'gains', 'label': 'Gains', 'icon': 'merge'}, {'id': 'shared-keys', 'label': 'Shared keys', 'icon': 'link'}, {'id': 'journeys', 'label': 'Journeys', 'icon': 'route', 'count': len(es['journeys'])}]}]
        self.page('estate', body, drawer, crumbs=[('Estate', None)])

    def governance_page(self):
        gv = self.c['governance']
        adr = ''.join(f'<section id="adr-{a["id"]}" class="prop"><h3>ADR {E(a["id"])}: {E(a["title"])} <strong class="tag {"ok" if a["status"] == "Accepted" else "warn"}">{E(a["status"])}</strong></h3><dl class="facts"><dt>Context</dt><dd>{E(a["context"])}</dd><dt>Decision</dt><dd>{E(a["decision"])}</dd><dt>Consequences</dt><dd>{E(a["consequences"])}</dd></dl></section>' for a in gv['adrs'])
        defects = table('t-def', 'Defect register', ['Defect', 'Found', 'What', 'Root cause', 'Fix', 'Check that stops it coming back'], [[E(d['id']), E(d['found']), E(d['what']), E(d['cause']), E(d['fix']), E(d['check'])] for d in gv['defects']])
        open_ = table('t-open', 'Open register: what design cannot close', ['Item', 'What', 'Who must act'], [[E(o['id']), E(o['item']), E(o['who'])] for o in gv['open']])
        raid = table('t-raid', 'Risks, assumptions, issues and dependencies', ['Type', 'What'], [[E(r['type']), E(r['text'])] for r in gv['raid']])
        ss = table('t-ss', 'Service Standard, self-assessed (not an assessment)', ['Point', 'Standard', 'Status', 'Evidence'], [[str(s['n']), E(s['point']), f'<strong class="tag {"ok" if s["status"] == "met" else "warn" if s["status"] == "partial" else "err"}">{E(s["status"].replace("-", " "))}</strong>', E(s['note'])] for s in gv['service_standard']], sortable=False)
        adv = ''.join(f'<li><strong>{E(a["claim"])}</strong> {E(a["answer"])}</li>' for a in gv['adversarial'])
        toc = gv['theory_of_change']
        tocd = (f'<dl class="facts"><dt>Problem</dt><dd>{E(toc["problem"])}</dd><dt>Activities</dt><dd>{ul([E(x) for x in toc["activities"]])}</dd><dt>Outputs</dt><dd>{ul([E(x) for x in toc["outputs"]])}</dd>'
                f'<dt>Outcomes</dt><dd>{ul([E(x) for x in toc["outcomes"]])}</dd><dt>Impact</dt><dd>{E(toc["impact"])}</dd><dt>Assumptions</dt><dd>{ul([E(x) for x in toc["assumptions"]])}</dd><dt>We would be wrong if</dt><dd>{ul([E(x) for x in toc["falsification"]])}</dd></dl>')
        arch = table('t-arch', 'Architecture', ['Layer', 'What'], [[E(a['layer']), E(a['text'])] for a in gv['architecture']], sortable=False)
        art = table('t-art', 'The usual artefact set, with an honest status', ['Artefact', 'Where', 'Status'], [[E(a['name']), (f'<a href="{E(a["where"])}">{E(a["where"])}</a>' if a['where'].endswith(('.html', ')')) or '.html#' in a['where'] else E(a['where'])), E(a['status'])] for a in gv['artefacts']])
        steps = ''.join(f'<li><strong>{E(s["step"])}:</strong> {E(s["text"])}</li>' for s in gv['change_process'])
        cp = gv['checkpoint']
        tests = [('Profile integrity', 'The loader refuses a broken profile: unknown properties, bad obligations, cardinalities that contradict obligations, orphan properties, email addresses in text, broken backlog links.', 'tests/test_profile.py ProfileIntegrity'),
                 ('Three validators agree', 'Every example passes, and every deliberate break fails, in SHACL, JSON Schema and the browser validator.', 'tests/test_profile.py ValidExamples, DeliberateBreaks'),
                 ('Every rule has a break', 'No rule exists without a record that breaks it.', 'tests/test_profile.py test_every_rule_has_a_break'),
                 ('Coverage', 'Every open xGov MEM issue is registered, every xGov MEM property is mapped, and every DCAT-AP mandatory property is mandatory here.', 'tests/test_profile.py Coverage'),
                 ('Pages', 'Unique ids, links that resolve, no email address anywhere, no external scripts or fonts, a Content Security Policy, captions on tables, colophon and self-describing metadata on every page, no deck or film files.', 'tools/check_site.py, with its own deliberate breaks'),
                 ('In a real browser', 'axe-core with no serious or critical issues, no horizontal overflow from 320 to 1920 pixels, contrast in light and dark, keyboard, no console errors.', 'tools/check_browser.py')]
        tt = table('checks-t', 'Checks on every change', ['Check', 'What it proves', 'Where'], [[E(a), E(b), f'<code>{E(c)}</code>'] for a, b, c in tests], sortable=False)
        body = self.hero('scale', 'About', 'Design and governance', self.gloss('How the profile is governed and changed, the decisions behind it, what is known to be wrong or missing, how it is checked, and an honest self-assessment.'))
        body += f'<h2 id="status">Status</h2><div class="panel warning"><p>{E(gv["status"])}</p></div>'
        body += f'<h2 id="checkpoint">Checkpoint</h2><dl class="facts"><dt>Intent</dt><dd>{E(cp["intent"])}</dd><dt>Arc</dt><dd>{ul([E(x) for x in cp["arc"]])}</dd><dt>Verdict</dt><dd>{E(cp["verdict"])}</dd></dl>'
        body += f'<h2 id="versioning">Versioning and releases</h2>{ul([E(x) for x in gv["versioning"]])}'
        body += f'<h2 id="change">Changing the profile</h2><ol>{steps}</ol><p class="btns"><a class="btn" href="{E(self.m["change_request"])}">{icon("git-pull-request")} Request a change</a></p>'
        body += f'<h2 id="namespace">Namespace and identifiers</h2><p>{E(self.m["namespace_status"])}</p>'
        body += f'<h2 id="checks">How it is checked</h2>{tt}'
        body += f'<h2 id="adrs">Decisions</h2>{adr}'
        body += f'<h2 id="defects">Defects</h2>{defects}'
        body += f'<h2 id="open">Open register</h2>{open_}'
        body += f'<h2 id="adversarial">The case against, answered</h2><ul>{adv}</ul>'
        body += f'<h2 id="raid">RAID</h2>{raid}'
        body += f'<h2 id="toc">Theory of change</h2>{tocd}'
        body += f'<h2 id="research">Research plan</h2>{ul([E(x) for x in gv["research_plan"]])}<p>Measures of success: </p>{ul([E(x) for x in gv["measures"]])}'
        body += f'<h2 id="architecture">Architecture</h2>{arch}'
        body += f'<h2 id="assessment">Service Standard self-assessment</h2>{ss}'
        body += f'<h2 id="privacy">Data protection and algorithmic transparency</h2><dl class="facts"><dt>Data protection</dt><dd>{E(gv["dpia"])}</dd><dt>Algorithmic Transparency Recording Standard</dt><dd>{E(gv["atrs"])}</dd></dl>'
        body += f'<h2 id="artefacts">Artefact set</h2>{art}'
        items = [('status', 'Status', 'flag'), ('checkpoint', 'Checkpoint', 'milestone'), ('versioning', 'Versioning', 'git-branch'), ('change', 'Changing the profile', 'git-pull-request'),
                 ('namespace', 'Namespace', 'link'), ('checks', 'Checks', 'clipboard-check'), ('adrs', 'Decisions', 'scroll-text'), ('defects', 'Defects', 'circle-alert'), ('open', 'Open register', 'clipboard-list'),
                 ('adversarial', 'The case against', 'scale'), ('raid', 'RAID', 'triangle-alert'), ('toc', 'Theory of change', 'target'), ('research', 'Research plan', 'users-round'),
                 ('architecture', 'Architecture', 'blocks'), ('assessment', 'Self-assessment', 'list-checks'), ('privacy', 'Privacy', 'lock'), ('artefacts', 'Artefact set', 'boxes')]
        counts = {'adrs': len(gv['adrs']), 'defects': len(gv['defects']), 'open': len(gv['open']), 'assessment': len(gv['service_standard']), 'artefacts': len(gv['artefacts'])}
        drawer = [{'title': 'Governance', 'icon': 'scale', 'items': [{'id': i, 'label': l, 'icon': ic, 'count': counts.get(i)} for i, l, ic in items]}]
        self.page('governance', body, drawer, crumbs=[('About', None), ('Design and governance', None)])

    def accessibility_page(self):
        body = self.hero('accessibility', 'About', 'Accessibility statement', 'This statement applies to the DCAT-UK AP portal. It is a draft until a manual audit has been done.')
        body += f'''<h2 id="using">Using this portal</h2><p>We want as many people as possible to be able to use this portal. You should be able to:</p>
{ul(["change colours, contrast levels and fonts using your browser or device settings, and switch between light and dark", "zoom in up to 400% without the text spilling off the screen", "navigate the whole portal using just a keyboard or speech recognition software", "listen to it using a screen reader", "make text larger and spacing wider from Display options on the Your role page"])}
<h2 id="how">How accessible this portal is</h2><p>Every build is checked automatically with axe-core in Chromium, for horizontal overflow at widths from 320 to 1920 pixels, and for colour contrast in light and dark. We know some parts may not be fully accessible:</p>
{ul(["the class diagram and the knowledge graph are complex images; each has a text alternative", "the record builder has many fields; it has not been tested with screen reader users", "the portal is in English only", "it has not been audited manually"])}
<h2 id="feedback">Feedback and contact information</h2><p>If you need information in a different format, or you find a problem, use the <a href="contact.html">contact form</a>. If you cannot use the form, ask a colleague to raise it for you. We will reply within 10 working days.</p>
<h2 id="enforcement">Enforcement procedure</h2><p>This portal is a personal public-good project, not a public sector body's website, so the Public Sector Bodies Accessibility Regulations 2018 may not apply. We follow them anyway. If it were adopted by a public body, the Equality and Human Rights Commission would be responsible for enforcing them.</p>
<h2 id="technical">Technical information</h2><p>We are committed to making this portal accessible, in line with the Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility Regulations 2018.</p>
<h3>Compliance status</h3><p>This portal is partially compliant with the Web Content Accessibility Guidelines version 2.2 AA standard, because it has not yet been audited manually.</p>
<h2 id="preparation">Preparation of this statement</h2><p>This statement was prepared on {E(self.m["as_of"])}. The portal was last tested automatically on the same date. It will be reviewed by {E(self.m["review"])}.</p>'''
        self.page('accessibility', body, [{'title': 'Accessibility', 'icon': 'accessibility', 'items': [{'id': i, 'label': l} for i, l in (('using', 'Using this portal'), ('how', 'How accessible it is'), ('feedback', 'Feedback'), ('enforcement', 'Enforcement'), ('technical', 'Technical information'), ('preparation', 'Preparation'))]}], crumbs=[('About', None), ('Accessibility statement', None)])

    def contact_page(self):
        m = self.m
        body = self.hero('message-square', 'About', 'Contact', 'Ask a question, report a problem or request a change. Contact is by form only: no email address is published.')
        body += f'''<div class="grid"><div class="card"><h3>{icon("message-square")} Ask or report</h3><p>Questions, problems and accessibility issues.</p><p class="go"><a class="btn" href="{E(m["contact"])}">Open the contact form</a></p></div>
<div class="card"><h3>{icon("git-pull-request")} Request a change</h3><p>A new property, value or rule, or a change to an obligation.</p><p class="go"><a class="btn" href="{E(m["change_request"])}">Open the change request form</a></p></div>
<div class="card"><h3>{icon("lock")} Report a security problem</h3><p>Privately, through GitHub's private vulnerability reporting.</p><p class="go"><a class="btn secondary" href="{E(m["repo_url"])}/security/advisories/new">Report privately</a></p></div></div>
<div class="panel notice"><h2 id="privacy">Before you write</h2><p>The contact and change request forms are GitHub issue forms, so what you write is public. Do not include personal data, the names of colleagues, or anything above OFFICIAL. You need a free GitHub account. If you cannot use the form, ask a colleague to raise it for you.</p></div>'''
        self.page('contact', body, None, crumbs=[('About', None), ('Contact', None)])

    def whatsnew_page(self):
        body = self.hero('history', 'About', "What's new", 'Changes in each release, newest first.')
        body += f'<h2 id="v1">{E(self.m["version"])}, {E(self.m["as_of"])}</h2>' + ul([
            'First release candidate of DCAT-UK AP, evolved from the xGov MEM v0.1.0.',
            'Profile, codelists, shapes, schema, context and examples generated from one source.',
            'Portal with record builder, validator and xGov MEM conversion, crosswalks, backlog register, strategy, roles, knowledge layer, estate comparison and governance.',
            'Joined the estate compass as its South bearing.'])
        self.page('whats-new', body, None, crumbs=[('About', None), ("What's new", None)])

    def notfound_page(self):
        body = self.hero('circle-help', 'Error', 'Page not found', 'If you typed the address, check it is correct. If you followed a link from the xGov MEM site, the property may have a new name: try the <a href="changes.html#crosswalk">crosswalk</a> or search.')
        body += '<p class="btns"><button type="button" class="btn" data-open="palette">Search the portal</button><a class="btn secondary" href="index.html">Go to the home page</a></p>'
        self.page('404', body)

    def sitemap_page(self):
        body = self.hero('map', 'About', 'Site map', 'Every page, grouped as the menus are.')
        for k, label, ic, kids in NAV:
            body += f'<h2>{icon(ic)} {E(label)}</h2>'
            keys = kids or [k]
            lis = ''.join(f'<li><a href="{"index" if x == "index" else x}.html">{E(TITLES[x])}</a>: {E(DESC[x])}</li>' for x in keys)
            if k == 'Profile':
                lis += ''.join(f'<li><a href="{self.class_page(ck)}">{E(c["label"])}</a></li>' for ck, c in self.p.classes.items())
            body += f'<ul>{lis}</ul>'
        self.page('sitemap', body, None, crumbs=[('About', None), ('Site map', None)])

    def write_machine(self, prof):
        """xref.json for the estate, and a DCAT-UK AP description of the downloads (the profile describing itself)."""
        p, m = self.p, self.m
        xref = {'portal': m['title'], 'id': 'ap', 'url': m['site_url'], 'version': m['version'], 'as_of': m['as_of'], 'status': m['status'],
                'keys': {'properties': {k: {'label': v['label'], 'uri': v['uri'], 'url': f'{m["site_url"]}properties.html#p-{k}'} for k, v in p.props.items()},
                         'classes': {k: {'label': v['label'], 'uri': v['uri'], 'url': m['site_url'] + self.class_page(k)} for k, v in p.classes.items()},
                         'codelists': {k: {'label': v['label'], 'url': f'{m["site_url"]}codelists.html#cl-{k}'} for k, v in p.codelists.items()},
                         'terms': {t['id']: {'term': t['term'], 'url': f'{m["site_url"]}knowledge.html#g-{t["id"]}'} for t in self.c['glossary']},
                         'organisations': {'key': 'GOV.UK organisation slug', 'url': m['site_url'] + 'downloads/organisations.json'}},
                'related': [{'id': x['id'], 'name': x['name'], 'url': x['url']} for x in self.c['estate']['portals'] if x['id'] != 'ap'] + [{'id': 'compass', 'name': 'Estate compass', 'url': self.c['estate']['compass']}]}
        (self.out / 'xref.json').write_text(json.dumps(xref, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        cat = {'class': 'Catalogue', 'id': m['site_url'] + 'downloads/', 'title': f'{m["title"]} {m["version"]} downloads',
               'description': 'The machine-readable forms of DCAT-UK AP, generated from one source on every build.',
               'publisher': 'https://github.com/cyberdudeuk', 'homepage': m['site_url'], 'conformsTo': ['https://w3id.org/dcat-uk-ap/1.0'],
               'modified': m['as_of'], 'language': ['eulang:ENG'], 'licence': 'http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
               'dataset': [m['site_url'] + 'downloads/#profile']}
        ds = {'class': 'Dataset', 'id': m['site_url'] + 'downloads/#profile', 'title': f'{m["title"]} {m["version"]}', 'description': 'Shapes, schema, context, codelists and dictionary of the profile.',
              'identifier': f'{m["id"]}-{m["version"]}', 'publisher': 'https://github.com/cyberdudeuk',
              'contactPoint': [{'fn': 'DCAT-UK AP maintainers', 'hasURL': m['contact']}], 'accessRights': 'ukcl:access-rights/open',
              'securityClassification': 'ukcl:security-classification/official', 'personalData': 'ukcl:personal-data/none',
              'licence': 'http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/', 'accrualPeriodicity': 'eufreq:IRREG',
              'issued': m['first_published'], 'modified': m['as_of'], 'version': m['version'], 'theme': ['ukcl:theme/government-reference-data'],
              'landingPage': [m['site_url'] + 'downloads.html'],
              'distribution': [{'class': 'Distribution', 'id': m['site_url'] + 'downloads/' + f, 'title': t, 'accessURL': [m['site_url'] + 'downloads/' + f],
                                'downloadURL': [m['site_url'] + 'downloads/' + f], 'mediaType': 'https://www.iana.org/assignments/media-types/' + mt}
                               for f, t, d, mt in self.dl_meta if not f.startswith(('..', 'catalog'))]}
        g = ukap.to_graph(p, cat)
        ukap.to_graph(p, ds, g)
        res = ukap.Profile.__dict__  # noqa: F841 (kept for readability)
        (self.out / 'downloads' / 'catalog.ttl').write_text(g.serialize(format='turtle'), encoding='utf-8')
        (self.out / 'downloads' / 'catalog.jsonld').write_text(json.dumps({'@context': m['site_url'] + 'downloads/dcat-uk-ap.context.jsonld', '@graph': [cat, ds]}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        self.self_records = [cat, ds]


def write_docs(p, portal):
    """docs/registers.md and docs/adr/*.md, generated from content/portal.yaml so the repository and the portal never disagree."""
    gv = portal['governance']
    d = ROOT / 'docs'
    (d / 'adr').mkdir(parents=True, exist_ok=True)
    for f in (d / 'adr').glob('*.md'):
        f.unlink()
    for a in gv['adrs']:
        (d / 'adr' / f'{a["id"]}-{slug(a["title"])}.md').write_text(
            f'# ADR {a["id"]}: {a["title"]}\n\nStatus: {a["status"]}\n\n## Context\n\n{a["context"]}\n\n## Decision\n\n{a["decision"]}\n\n## Consequences\n\n{a["consequences"]}\n\n'
            '<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->\n', encoding='utf-8')
    md = ['# Registers', '', 'Generated from `content/portal.yaml` and `content/lineage.yaml` by `tools/build.py`. Edit there, never here. The same registers are on the portal\'s [governance page](https://cyberdudeuk.github.io/dcat-uk-ap/governance.html).', '',
          '## Status', '', gv['status'].strip(), '', '## Defect register', '', '| Defect | Found | What | Root cause | Fix | Check |', '|---|---|---|---|---|---|']
    md += [f'| {x["id"]} | {x["found"]} | {x["what"]} | {x["cause"]} | {x["fix"]} | {x["check"]} |' for x in gv['defects']]
    md += ['', '## Open register', '', '| Item | What | Who must act |', '|---|---|---|'] + [f'| {o["id"]} | {o["item"]} | {o["who"]} |' for o in gv['open']]
    md += ['', '## Backlog from the xGov MEM', '', '| Issue | Title | Status | Resolution |', '|---|---|---|---|'] + [
        f'| [#{b["n"]}](https://github.com/co-cddo/ukgov-metadata-exchange-model/issues/{b["n"]}) | {b["title"]} | {b["status"]} | {" ".join(b["resolution"].split())} |' for b in p.lineage['backlog']]
    md += ['', '## RAID', ''] + [f'- **{r["type"]}:** {r["text"]}' for r in gv['raid']]
    md += ['', '## Checkpoint', '', f'**Intent:** {gv["checkpoint"]["intent"]}', ''] + [f'- {x}' for x in gv['checkpoint']['arc']] + ['', f'**Verdict:** {gv["checkpoint"]["verdict"]}', '']
    (d / 'registers.md').write_text('\n'.join(md), encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=str(ROOT / 'site'))
    a = ap.parse_args(argv)
    p = ukap.load()
    portal = yaml.safe_load((ROOT / 'content' / 'portal.yaml').read_text(encoding='utf-8'))
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    s = Site(p, portal, out).build_all()
    write_docs(p, portal)
    print(f'built {len(s.pages)} pages into {out} ({s.build_id})')


if __name__ == '__main__':
    main()
