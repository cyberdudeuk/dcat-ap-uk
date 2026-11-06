"""Load the DCAT-UK AP profile, check its integrity, and convert compact records to RDF.

The profile (profile/dcat-uk-ap.yaml) and codelists (profile/codelists.yaml) are the single source of truth.
Everything else is generated. This module refuses to load a profile with a broken reference, so a mistake in the source
stops the build rather than reaching a published page (build standard: regenerate, never text-patch).
"""
import copy
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KINDS = {'text', 'literal', 'date', 'decimal', 'integer', 'boolean', 'duration', 'wkt',
         'iri', 'url', 'email', 'concept', 'object'}
OBLIGATIONS = {'M', 'R', 'O', 'C'}
CHANGES = {'unchanged', 'new', 'uri-fixed', 'example-fixed', 'range-relaxed', 'range-changed', 'range-fixed',
           'obligation-changed', 'definition-fixed', 'codelist-mapped', 'codelist-added', 'value-restored', 'renamed', 'merged'}
# Codelists the profile closes (only listed values are valid). Others are open: the list is a recommendation.
OPEN_CODELISTS = {'licences', 'organisations', 'language', 'jurisdiction'}
RANK = {'O': 0, 'R': 1, 'C': 2, 'M': 3}  # an extension may only move a property up this order
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


class ProfileError(Exception):
    pass


def load(root=ROOT):
    root = Path(root)
    prof = yaml.safe_load((root / 'profile' / 'dcat-uk-ap.yaml').read_text(encoding='utf-8'))
    cls = yaml.safe_load((root / 'profile' / 'codelists.yaml').read_text(encoding='utf-8'))
    orgs_path = root / 'profile' / 'organisations.json'
    orgs = json.loads(orgs_path.read_text(encoding='utf-8')) if orgs_path.exists() else None
    lineage = yaml.safe_load((root / 'content' / 'lineage.yaml').read_text(encoding='utf-8'))
    examples = yaml.safe_load((root / 'examples' / 'examples.yaml').read_text(encoding='utf-8'))
    ext_path = root / 'profile' / 'extensions.yaml'
    ext = yaml.safe_load(ext_path.read_text(encoding='utf-8')) if ext_path.exists() else None
    cw_path = root / 'profile' / 'crosswalks.yaml'
    p = Profile(prof, cls, orgs, lineage, examples, ext)
    p.crosswalks = yaml.safe_load(cw_path.read_text(encoding='utf-8')) if cw_path.exists() else {}
    p.check()
    return p


class Profile:
    def __init__(self, prof, codelists, orgs, lineage, examples, ext=None, applied=()):
        self._raw = (prof, codelists, orgs, lineage, examples, ext)
        self.ext_doc = ext or {'prefixes': {}, 'extensions': [], 'synthetic_base': {}}
        self.extensions = {e['id']: e for e in self.ext_doc.get('extensions', [])}
        self.applied = tuple(applied)
        self.crosswalks = {}
        self.meta = prof['meta']
        self.prefixes = dict(prof['prefixes'], **(self.ext_doc.get('prefixes') or {}))
        self.props = prof['properties']
        self.classes = prof['classes']
        self.rules = prof['rules']
        self.obligations = prof['obligations']
        self.codelists = codelists
        self.orgs = orgs
        self.lineage = lineage
        self.examples = examples
        self.class_by_uri = {self.expand(c['uri']): k for k, c in self.classes.items()}

    # -- names ------------------------------------------------------------------
    def expand(self, curie):
        if curie is None:
            return None
        s = str(curie)
        if re.match(r'^[a-z][a-z0-9+.-]*://', s) or s.startswith(('mailto:', 'urn:')):
            return s
        if ':' in s:
            pre, local = s.split(':', 1)
            if pre in self.prefixes:
                return self.prefixes[pre] + local
        return s

    def concept_iri(self, scheme, code):
        cl = self.codelists[scheme]
        if cl.get('external'):
            return cl['scheme_uri'].rstrip('/') + '/' + code
        for c in cl['concepts']:
            if c['code'] == code and c.get('uri'):
                return c['uri']
        return self.meta['codelist_base'] + scheme + '/' + code

    def scheme_iri(self, scheme):
        cl = self.codelists.get(scheme, {})
        return cl.get('scheme_uri') or (self.meta['codelist_base'] + scheme)

    def concept_iris(self, scheme):
        if scheme == 'organisations':
            return []
        return [self.concept_iri(scheme, c['code']) for c in self.codelists[scheme]['concepts']]

    # -- extensions -------------------------------------------------------------
    def with_extensions(self, ids):
        """A new Profile: the base plus the named extensions. Raises ProfileError if an extension would weaken the base."""
        prof, codelists, orgs, lineage, examples, ext = self._raw
        prof = copy.deepcopy(prof)
        errs = []
        for eid in ids:
            e = self.extensions.get(eid)
            if e is None:
                raise ProfileError(f'unknown extension {eid}')
            for k, v in (e.get('properties') or {}).items():
                if k in prof['properties']:
                    errs.append(f'extension {eid}: property {k} already exists')
                prof['properties'][k] = copy.deepcopy(v)
            for ck, c in (e.get('new_classes') or {}).items():
                if ck in prof['classes']:
                    errs.append(f'extension {eid}: class {ck} already exists')
                prof['classes'][ck] = copy.deepcopy(c)
            for ck, entries in (e.get('classes') or {}).items():
                if ck not in prof['classes']:
                    errs.append(f'extension {eid}: unknown class {ck}')
                    continue
                plist = prof['classes'][ck]['properties']
                for x in entries:
                    cur = next((y for y in plist if y['p'] == x['p']), None)
                    if cur is None:
                        plist.append(dict(x, ext=eid))
                        continue
                    if RANK.get(x.get('ob'), -1) < RANK.get(cur['ob'], 0):
                        errs.append(f'extension {eid}: {ck}.{x["p"]} would weaken {cur["ob"]} to {x.get("ob")}')
                    if str(cur['card']).endswith('..1') or str(cur['card']) == '1':
                        if str(x.get('card', '')).endswith('n'):
                            errs.append(f'extension {eid}: {ck}.{x["p"]} would widen cardinality {cur["card"]} to {x.get("card")}')
                    cur.update({k2: v2 for k2, v2 in x.items() if k2 != 'p'}, ext=eid)
        if errs:
            raise ProfileError('\n'.join(errs))
        prof['meta'] = dict(prof['meta'], id=prof['meta']['id'] + ''.join('+' + i for i in ids))
        q = Profile(prof, codelists, orgs, lineage, examples, ext, applied=tuple(self.applied) + tuple(ids))
        return q

    def ext_example(self, eid, ex=None):
        """The example record of an extension: a base example or the synthetic base, with the extension's additions."""
        e = self.extensions[eid]
        ex = ex or e['example']
        if ex.get('base'):
            rec = copy.deepcopy(next(x['record'] for x in self.examples if x['key'] == ex['base']))
        else:
            rec = copy.deepcopy(self.ext_doc['synthetic_base'])
            rec['id'] = rec['id'].rsplit('/', 1)[0] + '/' + eid
        rec.update(copy.deepcopy(ex.get('add') or {}))
        return rec

    def ext_break(self, eid, b):
        rec = self.ext_example(eid)
        for k in b.get('remove', []):
            rec.pop(k, None)
        rec.update(copy.deepcopy(b.get('set') or {}))
        return rec

    def pattern_for(self, x, prop):
        """The regular expression a value must match: on the class property, the property, or its open codelist."""
        return x.get('pattern') or prop.get('pattern') or (self.codelists.get(prop.get('codelist') or '', {}) or {}).get('pattern')

    # -- integrity --------------------------------------------------------------
    def check(self):
        errs = []
        if not self.applied:
            ext_props = {k for e in self.extensions.values() for k in (e.get('properties') or {})}
            for cid, cw in (self.crosswalks or {}).items():
                for row in cw['rows']:
                    if row[0] != '(class)' and row[0] not in self.props and row[0] not in ext_props:
                        errs.append(f'crosswalk {cid}: unknown property {row[0]}')
            for eid, e in self.extensions.items():
                for f in ('label', 'summary', 'for', 'aligned_to', 'classes', 'example', 'breaks'):
                    if f not in e:
                        errs.append(f'extension {eid}: missing {f}')
                if not e.get('breaks'):
                    errs.append(f'extension {eid}: has no deliberate break')
                for t in ('summary', 'for'):
                    if EMAIL_RE.search(str(e.get(t, ''))):
                        errs.append(f'extension {eid}: {t} contains an email address (COL-02)')
                try:
                    self.with_extensions([eid]).check()
                except ProfileError as ex:
                    errs.append(f'extension {eid}: {ex}')
        for k, v in self.props.items():
            for f in ('uri', 'label', 'kind', 'definition', 'mem'):
                if f not in v:
                    errs.append(f'property {k}: missing {f}')
            if v.get('kind') not in KINDS:
                errs.append(f'property {k}: unknown kind {v.get("kind")}')
            if v.get('kind') == 'object' and v.get('range') not in self.classes:
                errs.append(f'property {k}: object range {v.get("range")} is not a class')
            cl = v.get('codelist')
            if cl and cl != 'organisations' and cl not in self.codelists:
                errs.append(f'property {k}: unknown codelist {cl}')
            if v.get('kind') == 'concept' and not cl:
                errs.append(f'property {k}: concept property without a codelist')
            ch = (v.get('mem') or {}).get('change')
            if ch not in CHANGES:
                errs.append(f'property {k}: unknown change {ch}')
            pre = str(v.get('uri', '')).split(':', 1)[0]
            if pre not in self.prefixes:
                errs.append(f'property {k}: unknown prefix {pre}')
            for t in ('definition', 'guidance', 'purpose', 'example'):
                if EMAIL_RE.search(str(v.get(t, ''))):
                    errs.append(f'property {k}: {t} contains an email address (COL-02)')
        used = set()
        for ck, c in self.classes.items():
            if c.get('ob') not in OBLIGATIONS:
                errs.append(f'class {ck}: bad obligation')
            seen = set()
            for x in c['properties']:
                if x['p'] not in self.props:
                    errs.append(f'class {ck}: unknown property {x["p"]}')
                if x['p'] in seen:
                    errs.append(f'class {ck}: property {x["p"]} listed twice')
                seen.add(x['p'])
                used.add(x['p'])
                if x.get('ob') not in OBLIGATIONS:
                    errs.append(f'class {ck}.{x["p"]}: bad obligation {x.get("ob")}')
                if x.get('ob') == 'C' and not x.get('condition'):
                    errs.append(f'class {ck}.{x["p"]}: conditional without a condition')
                if x.get('cda') and x['cda'] not in OBLIGATIONS:
                    errs.append(f'class {ck}.{x["p"]}: bad cda obligation')
                card = str(x.get('card', ''))
                if card not in {'1', '0..1', '0..n', '1..n'}:
                    errs.append(f'class {ck}.{x["p"]}: bad cardinality {card}')
                if x.get('ob') == 'M' and not card.startswith('1'):
                    errs.append(f'class {ck}.{x["p"]}: mandatory but cardinality {card}')
                if x.get('ob') != 'M' and card.startswith('1'):
                    errs.append(f'class {ck}.{x["p"]}: cardinality {card} but obligation {x.get("ob")}')
                if x.get('pattern'):
                    try:
                        re.compile(x['pattern'])
                    except re.error as ex:
                        errs.append(f'class {ck}.{x["p"]}: bad pattern ({ex})')
            for o in c.get('one_of', []):
                if o not in seen:
                    errs.append(f'class {ck}: one_of names {o}, not a property of the class')
        for k in self.props:
            if k not in used:
                errs.append(f'property {k}: not used by any class')
        for sk, s in self.codelists.items():
            codes = [c['code'] for c in s['concepts']]
            for c in codes:
                if not isinstance(c, str):
                    errs.append(f'codelist {sk}: code {c!r} is not text (quote it in YAML; "no" reads as false)')
            codes = [str(c) for c in codes]
            if len(codes) != len(set(codes)):
                errs.append(f'codelist {sk}: duplicate codes')
            if not s.get('external'):
                for c in codes:
                    if not re.match(r'^[a-z0-9-]+$', c):
                        errs.append(f'codelist {sk}: code {c} is not lower-case kebab')
        issue_nums = {b['n'] for b in self.lineage['backlog']}
        for k, v in self.props.items():
            for n in v.get('issues', []):
                if n not in issue_nums and n not in {c['n'] for c in self.lineage['closed_kept']}:
                    errs.append(f'property {k}: issue {n} is not in the backlog register')
        keys = set()
        for b in self.lineage['backlog']:
            for w in b.get('where', []):
                kind, _, ref = w.partition(':')
                if kind == 'prop' and ref not in self.props:
                    errs.append(f'backlog {b["n"]}: unknown property {ref}')
                if kind == 'class' and ref not in self.classes:
                    errs.append(f'backlog {b["n"]}: unknown class {ref}')
                if kind == 'codelist' and ref not in self.codelists:
                    errs.append(f'backlog {b["n"]}: unknown codelist {ref}')
                if kind == 'example' and ref not in {e['key'] for e in self.examples}:
                    errs.append(f'backlog {b["n"]}: unknown example {ref}')
        for e in self.examples:
            if e['key'] in keys:
                errs.append(f'example {e["key"]} duplicated')
            keys.add(e['key'])
        if errs:
            raise ProfileError('\n'.join(errs))

    # -- helpers ----------------------------------------------------------------
    def class_props(self, ck):
        for x in self.classes[ck]['properties']:
            yield x, self.props[x['p']]

    def multi(self, x):
        return str(x['card']).endswith('n')

    def mem_slots(self):
        """Every xGov MEM slot, mapped to the property that replaces it (or None)."""
        out = {}
        for k, v in self.props.items():
            s = (v.get('mem') or {}).get('slot')
            if s:
                out[s] = k
        return out


# ---------------------------------------------------------------------------
# Compact record -> RDF
# ---------------------------------------------------------------------------
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$')
MEDIA_PREFIX = 'https://www.iana.org/assignments/media-types/'


def to_graph(p, record, g=None):
    """Turn one compact record (a dict) into triples. Returns the rdflib Graph."""
    from rdflib import Graph, URIRef, BNode, Literal, Namespace
    from rdflib.namespace import RDF, XSD
    g = g if g is not None else Graph()
    for pre, ns in p.prefixes.items():
        g.bind(pre, Namespace(ns))
    gs = Namespace(p.prefixes['geosparql'])

    def node_for(obj, rng):
        if isinstance(obj, str):
            return URIRef(p.expand(obj))
        ck = obj.get('class', rng)
        n = URIRef(p.expand(obj['id'])) if obj.get('id') else BNode()
        g.add((n, RDF.type, URIRef(p.expand(p.classes[ck]['uri']))))
        fill(n, ck, obj)
        return n

    def value(prop, v):
        k = prop['kind']
        if k == 'object':
            return node_for(v, prop['range'])
        if k in ('iri', 'url', 'concept'):
            s = str(v)
            if prop.get('codelist') and prop['kind'] == 'concept':
                return URIRef(p.expand(s))
            if prop is p.props.get('mediaType') and '/' in s and not s.startswith('http'):
                s = MEDIA_PREFIX + s
            return URIRef(p.expand(s))
        if k == 'email':
            s = str(v)
            return URIRef(s if s.startswith('mailto:') else 'mailto:' + s)
        s = str(v)
        if k == 'date':
            if DATETIME_RE.match(s):
                return Literal(s, datatype=XSD.dateTime)
            if DATE_RE.match(s):
                return Literal(s, datatype=XSD.date)
            if re.match(r'^\d{4}-\d{2}$', s):
                return Literal(s, datatype=XSD.gYearMonth)
            if re.match(r'^\d{4}$', s):
                return Literal(s, datatype=XSD.gYear)
            return Literal(s)  # invalid; left untyped so SHACL reports it
        if k == 'integer':
            return Literal(s, datatype=XSD.nonNegativeInteger)
        if k == 'decimal':
            return Literal(s, datatype=XSD.decimal)
        if k == 'boolean':
            return Literal(s.lower(), datatype=XSD.boolean)
        if k == 'duration':
            return Literal(s, datatype=XSD.duration)
        if k == 'wkt':
            return Literal(s, datatype=gs.wktLiteral)
        return Literal(s)

    def fill(n, ck, obj):
        for key, v in obj.items():
            if key in ('class', 'id'):
                continue
            prop = p.props.get(key)
            if prop is None:
                # unknown keys are kept under the profile namespace so validation can report them
                from urllib.parse import quote
                g.add((n, URIRef(p.prefixes['dcatuk'] + 'unknown-' + quote(str(key), safe='')), Literal(str(v))))
                continue
            for item in (v if isinstance(v, list) else [v]):
                g.add((n, URIRef(p.expand(prop['uri'])), value(prop, item)))

    node_for(record, record['class'])
    return g


def frame_graph(p, record):
    return to_graph(p, record)
