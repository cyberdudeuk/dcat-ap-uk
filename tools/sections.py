"""Section fingerprints for change flags (the pattern the Data Quality Commons uses).

A page's sections are its headings (h2 or h3) that carry an id. Each section's fingerprint is a hash of its plain text,
from its heading to the next one. Flags compare today's fingerprints with content/section-baseline.json, recorded at a
release by tools/section_baseline.py:

  new      the section (or the whole page) did not exist at the baseline
  updated  the section's wording changed since the baseline

Only words count: markup, icons and attribute changes do not flag anything.
"""
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / 'content' / 'section-baseline.json'
HEAD = re.compile(r'<h([23])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', re.S)
# Text that changes on every build or every day without the content changing.
VOLATILE = re.compile(r'DCAT-AP-UK-\d+\.\d+\.\d+(?:-[a-z0-9.]+)?-[0-9a-f]{6,}|\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z?\b')


def plain(fragment):
    fragment = re.sub(r'<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>|<span class="(?:flag|secflag)[^"]*">.*?</span>', ' ', fragment, flags=re.S)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', fragment))
    text = re.sub(r'\s+', ' ', VOLATILE.sub(' ', text)).strip()
    return re.sub(r'\s+([.,;:!?)\]])', r'\1', re.sub(r'([(\[])\s+', r'\1', text))  # inline markup must not move punctuation


def sections(body):
    """{section id: fingerprint} for every h2 or h3 with an id in the page body (or in a whole page's <main>)."""
    m = re.search(r'<main\b[^>]*>(.*)</main>', body, flags=re.S)
    body = m.group(1) if m else body
    heads = list(HEAD.finditer(body))
    out = {}
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        text = plain(h.group(3)) + ' | ' + plain(body[h.end():end])
        out[h.group(2)] = hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]
    return out


def load_baseline():
    return json.loads(BASELINE.read_text(encoding='utf-8')) if BASELINE.exists() else {'since': None, 'pages': {}}


def compare(old, now):
    """old: the page's baseline sections, or None if the page did not exist. Returns {id: 'new' | 'updated'}."""
    if old is None:
        return {k: 'new' for k in now}
    return {k: ('new' if k not in old else 'updated') for k, h in now.items() if old.get(k) != h}
