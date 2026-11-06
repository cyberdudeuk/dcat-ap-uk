"""Load the DCAT-UK AP profile, check its integrity, and convert compact records to RDF.

The profile (profile/dcat-uk-ap.yaml) and codelists (profile/codelists.yaml) are the single source of truth.
Everything else is generated. This module refuses to load a profile with a broken reference, so a mistake in the source
stops the build rather than reaching a published page (build standard: regenerate, never text-patch).
"""
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
OPEN_CODELISTS = {'licences', 'organisations', 'language'}
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
    p = Profile(prof, cls, orgs, lineage, examples)
    p.check()
    return p


class Profile:
    def __init__(self, prof, codelists, orgs, lineage, examples):
        self.meta = prof['meta']
        self.prefixes = prof['prefixes']
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

    # -- integrity --------------------------------------------------------------
    def check(self):
        errs = []
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
            for o in c.get('one_of', []):
                if o not in seen:
                    errs.append(f'class {ck}: one_of names {o}, not a property of the class')
        for k in self.props:
            if k not in used:
                errs.append(f'property {k}: not used by any class')
        for sk, s in self.codelists.items():
            codes = [c['code'] for c in s['concepts']]
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
                g.add((n, URIRef(p.prefixes['dcatuk'] + 'unknown-' + key), Literal(str(v))))
                continue
            for item in (v if isinstance(v, list) else [v]):
                g.add((n, URIRef(p.expand(prop['uri'])), value(prop, item)))

    node_for(record, record['class'])
    return g


def frame_graph(p, record):
    return to_graph(p, record)
