"""Generate every machine-readable form of DCAT-UK AP from the profile source.

Outputs (all regenerated on every build, never edited by hand):
  dcat-uk-ap.shacl.ttl      SHACL shapes (core SHACL only, so any SHACL engine can run them)
  dcat-uk-ap.schema.json    JSON Schema 2020-12 for the compact JSON form used by the portal and the record builder
  dcat-uk-ap.context.jsonld JSON-LD 1.1 context for the compact form
  dcat-uk-ap.linkml.yaml    LinkML schema, for continuity with the xGov MEM toolchain
  dcat-uk-ap.ns.ttl         RDFS/OWL definitions of the few terms this profile adds (dcatuk:)
  codelists.ttl/.jsonld     SKOS concept schemes; codelists.csv
  data-dictionary.csv       every property on every class, with obligations and lineage
  crosswalk-mem.csv         xGov MEM slot -> DCAT-UK AP property, with the change
  backlog.csv               every xGov MEM backlog item and how it was dealt with
  profile.json              the profile for the browser (record builder and validator)
  examples/*.ttl|.jsonld|.json
"""
import csv
import io
import json

import yaml
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

import ukap

SH = Namespace('http://www.w3.org/ns/shacl#')
DATATYPES = {
    'integer': XSD.nonNegativeInteger, 'decimal': XSD.decimal, 'boolean': XSD.boolean, 'duration': XSD.duration,
}
# schema.org terms for the crosswalk (K: author's mapping, to be checked before endorsement)
SCHEMA_ORG = {
    'title': 'name', 'description': 'description', 'abstract': 'abstract', 'alternative': 'alternateName', 'identifier': 'identifier',
    'publisher': 'publisher', 'creator': 'creator', 'contactPoint': 'contactPoint (via publisher)', 'licence': 'license',
    'issued': 'datePublished', 'modified': 'dateModified', 'created': 'dateCreated', 'keyword': 'keywords', 'spatial': 'spatialCoverage',
    'temporal': 'temporalCoverage', 'version': 'version', 'distribution': 'distribution', 'landingPage': 'url', 'language': 'inLanguage',
    'conformsTo': 'conformsTo (dct)', 'isReplacedBy': '(none)', 'expires': 'expires', 'theme': 'about', 'downloadURL': 'contentUrl',
    'mediaType': 'encodingFormat', 'byteSize': 'contentSize', 'accessURL': 'url', 'inSeries': 'isPartOf',
}


def sh_list(g, items):
    head = BNode()
    Collection(g, head, list(items))
    return head


def prop_shape(p, g, x, prop, path):
    ps = BNode()
    g.add((ps, SH.path, path))
    g.add((ps, SH.name, Literal(prop['label'], lang='en')))
    g.add((ps, SH.description, Literal(prop['definition'], lang='en')))
    ob = x['ob']
    # Every value constraint is a violation, whatever the obligation; the obligation only decides whether absence is allowed.
    g.add((ps, SH.severity, SH.Violation))
    g.add((ps, URIRef(p.prefixes['dcatuk'] + 'obligation'), Literal(ob)))
    if ob == 'M':
        g.add((ps, SH.minCount, Literal(1)))
    if str(x['card']) in ('1', '0..1'):
        g.add((ps, SH.maxCount, Literal(1)))
        if ob != 'M':
            # a second value is an error whatever the obligation
            pass
    k = prop['kind']
    if k in ('text', 'literal'):
        g.add((ps, SH.nodeKind, SH.Literal))
    elif k == 'date':
        g.add((ps, SH['or'], sh_list(g, [dt_shape(g, XSD.date), dt_shape(g, XSD.dateTime), dt_shape(g, XSD.gYearMonth), dt_shape(g, XSD.gYear)])))
    elif k == 'wkt':
        g.add((ps, SH.datatype, URIRef(p.prefixes['geosparql'] + 'wktLiteral')))
    elif k in DATATYPES:
        g.add((ps, SH.datatype, DATATYPES[k]))
    elif k in ('iri', 'url', 'concept', 'email'):
        g.add((ps, SH.nodeKind, SH.IRI))
        if k == 'url':
            g.add((ps, SH.pattern, Literal('^https?://')))
        if k == 'email':
            g.add((ps, SH.pattern, Literal('^mailto:[^@]+@[^@]+$')))
            g.add((ps, SH.message, Literal('A team email address must be a mailto address (rule R-06).', lang='en')))
        cl = prop.get('codelist')
        if k == 'concept' and cl and cl not in ukap.OPEN_CODELISTS:
            g.add((ps, SH['in'], sh_list(g, [URIRef(i) for i in p.concept_iris(cl)])))
        if cl == 'language':
            g.add((ps, SH.pattern, Literal('^' + p.codelists['language']['scheme_uri'] + '/')))
    elif k == 'object':
        g.add((ps, SH.nodeKind, SH.BlankNodeOrIRI))
    if prop.get('max_length'):
        g.add((ps, SH.maxLength, Literal(prop['max_length'])))
    if x['p'] == 'startDate':
        g.add((ps, SH.lessThanOrEquals, URIRef(p.expand(p.props['endDate']['uri']))))
        g.add((ps, SH.message, Literal("A period's end date must not be before its start date (rule R-07).", lang='en')))
    return ps


def dt_shape(g, dt):
    n = BNode()
    g.add((n, SH.datatype, dt))
    return n


def shacl(p):
    g = Graph()
    for pre, ns in p.prefixes.items():
        g.bind(pre, Namespace(ns))
    base = Namespace(p.meta['namespace'].replace('ns#', 'shapes#'))
    g.bind('ukshapes', base)
    onto = URIRef(p.meta['namespace'].replace('ns#', 'shapes'))
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, DCTERMS.title, Literal(p.meta['title'] + ' SHACL shapes', lang='en')))
    g.add((onto, OWL.versionInfo, Literal(p.meta['version'])))
    g.add((onto, DCTERMS.license, URIRef('http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/')))
    for ck, c in p.classes.items():
        s = base[ck + 'Shape']
        g.add((s, RDF.type, SH.NodeShape))
        g.add((s, SH.targetClass, URIRef(p.expand(c['uri']))))
        g.add((s, SH.name, Literal(c['label'], lang='en')))
        g.add((s, SH.description, Literal(c['definition'], lang='en')))
        for x, prop in p.class_props(ck):
            g.add((s, SH.property, prop_shape(p, g, x, prop, URIRef(p.expand(prop['uri'])))))
        if c.get('one_of'):
            alts = []
            for name in c['one_of']:
                a = BNode()
                pp = BNode()
                g.add((a, SH.property, pp))
                g.add((pp, SH.path, URIRef(p.expand(p.props[name]['uri']))))
                g.add((pp, SH.minCount, Literal(1)))
                alts.append(a)
            g.add((s, SH['or'], sh_list(g, alts)))
            rule = next(r for r in p.rules if r['class'] == ck and r['id'] in ('R-01', 'R-02'))
            g.add((s, SH.message, Literal(f"{rule['text']} (rule {rule['id']})", lang='en')))
        if ck in ('Dataset', 'DataService'):
            # R-03: commercial or internal access needs a rights statement
            r3 = base[ck + 'RightsShape']
            g.add((r3, RDF.type, SH.NodeShape))
            g.add((r3, SH.targetClass, URIRef(p.expand(c['uri']))))
            g.add((r3, SH.message, Literal('When access rights are commercial or internal, give a rights statement (rule R-03).', lang='en')))
            opn = BNode(); po = BNode()
            g.add((opn, SH.property, po)); g.add((po, SH.path, DCTERMS.accessRights))
            g.add((po, SH['in'], sh_list(g, [URIRef(p.concept_iri('access-rights', 'open'))])))
            has = BNode(); ph = BNode()
            g.add((has, SH.property, ph)); g.add((ph, SH.path, DCTERMS.rights)); g.add((ph, SH.minCount, Literal(1)))
            g.add((r3, SH['or'], sh_list(g, [opn, has])))
        if ck == 'Dataset':
            # R-04: critical data assets carry the extra mandatory properties
            r4 = base['CriticalDataAssetShape']
            g.add((r4, RDF.type, SH.NodeShape))
            g.add((r4, SH.targetClass, URIRef(p.expand(c['uri']))))
            g.add((r4, SH.message, Literal('A critical data asset must give every property marked mandatory for critical data assets (rule R-04).', lang='en')))
            not_cda = BNode(); inner = BNode(); pc = BNode()
            g.add((not_cda, SH['not'], inner)); g.add((inner, SH.property, pc))
            g.add((pc, SH.path, URIRef(p.expand(p.props['criticalDataAsset']['uri']))))
            g.add((pc, SH.hasValue, Literal('true', datatype=XSD.boolean)))
            full = BNode()
            for x, prop in p.class_props(ck):
                if x.get('cda') == 'M':
                    q = BNode()
                    g.add((full, SH.property, q))
                    g.add((q, SH.path, URIRef(p.expand(prop['uri']))))
                    g.add((q, SH.minCount, Literal(1)))
            g.add((r4, SH['or'], sh_list(g, [not_cda, full])))
    return g


# ---------------------------------------------------------------------------
def js_value(p, prop):
    k = prop['kind']
    if k == 'object':
        return {'anyOf': [{'type': 'string', 'format': 'iri-reference'}, {'$ref': f'#/$defs/{prop["range"]}'}]}
    if k == 'date':
        return {'type': 'string', 'pattern': r'^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$'}
    if k == 'integer':
        return {'type': ['string', 'integer'], 'pattern': r'^\d+$'}
    if k == 'decimal':
        return {'type': ['string', 'number'], 'pattern': r'^\d+(\.\d+)?$'}
    if k == 'boolean':
        return {'type': ['string', 'boolean'], 'enum': ['true', 'false', True, False]}
    if k == 'url':
        return {'type': 'string', 'pattern': '^https?://'}
    if k == 'email':
        return {'type': 'string', 'pattern': '^(mailto:)?[^@\\s]+@[^@\\s]+$'}
    if k == 'concept':
        cl = prop.get('codelist')
        if cl in ukap.OPEN_CODELISTS:
            return {'type': 'string'}
        return {'type': 'string', 'enum': sorted(set(compact_forms(p, cl)))}
    if k == 'iri' and prop.get('codelist') == 'licences':
        return {'type': 'string'}
    return {'type': 'string'}


def compact_forms(p, cl):
    out = []
    ext = p.codelists[cl].get('external')
    pre = {'frequency': 'eufreq', 'language': 'eulang'}.get(cl)
    for c in p.codelists[cl]['concepts']:
        full = p.concept_iri(cl, c['code'])
        out.append(full)
        out.append((pre + ':' + c['code']) if ext and pre else 'ukcl:' + cl + '/' + c['code'])
    return out


def json_schema(p):
    defs = {}
    for ck, c in p.classes.items():
        props = {'class': {'const': ck}, 'id': {'type': 'string'}}
        req = []
        for x, prop in p.class_props(ck):
            v = js_value(p, prop)
            props[x['p']] = {'description': prop['definition'], **(
                {'anyOf': [v, {'type': 'array', 'items': v, 'minItems': 1}]} if p.multi(x) else v)}
            if prop.get('max_length'):
                props[x['p']]['maxLength'] = prop['max_length']
            if x['ob'] == 'M':
                req.append(x['p'])
        d = {'type': 'object', 'title': c['label'], 'description': c['definition'], 'properties': props,
             'required': req, 'additionalProperties': False}
        allof = []
        if c.get('one_of'):
            allof.append({'anyOf': [{'required': [o]} for o in c['one_of']]})
        if ck in ('Dataset', 'DataService'):
            opens = [f for f in compact_forms(p, 'access-rights') if f.endswith('/open')]
            allof.append({'if': {'properties': {'accessRights': {'not': {'enum': opens}}}, 'required': ['accessRights']},
                          'then': {'required': ['rights']}})
        if ck == 'Dataset':
            cda = [x['p'] for x, _ in p.class_props(ck) if x.get('cda') == 'M']
            allof.append({'if': {'properties': {'criticalDataAsset': {'enum': ['true', True]}}, 'required': ['criticalDataAsset']},
                          'then': {'required': cda}})
        if allof:
            d['allOf'] = allof
        defs[ck] = d
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': p.meta['site_url'] + 'downloads/dcat-uk-ap.schema.json',
        'title': p.meta['title'] + ' ' + p.meta['version'],
        'description': 'JSON Schema for records in the compact JSON form of DCAT-UK AP. Pair it with the JSON-LD context to get RDF.',
        'oneOf': [{'$ref': f'#/$defs/{k}'} for k in p.classes],
        '$defs': defs,
    }


def context(p):
    ctx = {'@version': 1.1, 'class': '@type', 'id': '@id'}
    for pre, ns in p.prefixes.items():
        if pre not in ('sh',):
            ctx[pre] = ns
    for k, c in p.classes.items():
        ctx[k] = c['uri']
    for k, v in p.props.items():
        term = {'@id': v['uri']}
        kind = v['kind']
        if kind in ('iri', 'url', 'concept', 'object', 'email'):
            term['@type'] = '@id'
        elif kind == 'date':
            term['@type'] = 'xsd:date'
        elif kind in DATATYPES:
            term['@type'] = 'xsd:' + str(DATATYPES[kind]).split('#')[1]
        elif kind == 'wkt':
            term['@type'] = 'geosparql:wktLiteral'
        ctx[k] = term
    return {'@context': ctx}


def linkml(p):
    slots, classes, enums = {}, {}, {}
    rng = {'text': 'string', 'literal': 'string', 'date': 'date', 'integer': 'integer', 'decimal': 'decimal', 'boolean': 'boolean',
           'duration': 'string', 'wkt': 'string', 'iri': 'uriorcurie', 'url': 'uri', 'email': 'string'}
    for k, v in p.props.items():
        s = {'slot_uri': v['uri'], 'description': v['definition']}
        if v['kind'] == 'object':
            s['range'] = v['range']
        elif v['kind'] == 'concept':
            s['range'] = ''.join(w.title() for w in v['codelist'].split('-')) + 'Values'
        else:
            s['range'] = rng[v['kind']]
        if v.get('mem', {}).get('slot'):
            s['aliases'] = [v['mem']['slot']]
        slots[k] = s
    for ck, c in p.classes.items():
        classes[ck] = {'class_uri': c['uri'], 'description': c['definition'], 'slots': [x['p'] for x in c['properties']],
                       'slot_usage': {x['p']: {k2: v2 for k2, v2 in (('required', x['ob'] == 'M'), ('recommended', x['ob'] == 'R'),
                                                                   ('multivalued', p.multi(x))) if v2} for x in c['properties']}}
    for sk, s in p.codelists.items():
        enums[''.join(w.title() for w in sk.split('-')) + 'Values'] = {
            'description': s['definition'],
            'permissible_values': {c['code']: {'meaning': p.concept_iri(sk, c['code']), 'description': c['label']} for c in s['concepts']}}
    doc = {'id': p.meta['namespace'].rstrip('#'), 'name': 'dcat-uk-ap', 'title': p.meta['title'], 'version': p.meta['version'],
           'license': 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
           'description': 'LinkML rendering of DCAT-UK AP, generated for continuity with the xGov MEM toolchain. The source of truth is profile/dcat-uk-ap.yaml.',
           'prefixes': {k: v for k, v in p.prefixes.items()} | {'linkml': 'https://w3id.org/linkml/'},
           'default_prefix': 'dcatuk', 'default_range': 'string', 'imports': ['linkml:types'],
           'classes': classes, 'slots': slots, 'enums': enums}
    return '# Generated by tools/generate.py. Do not edit.\n' + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


def namespace_terms(p):
    g = Graph()
    for pre, ns in p.prefixes.items():
        g.bind(pre, Namespace(ns))
    ont = URIRef(p.meta['namespace'].rstrip('#'))
    g.add((ont, RDF.type, OWL.Ontology))
    g.add((ont, DCTERMS.title, Literal('Terms added by ' + p.meta['title'], lang='en')))
    g.add((ont, OWL.versionInfo, Literal(p.meta['version'])))
    g.add((ont, RDFS.comment, Literal(p.meta['namespace_status'], lang='en')))
    for k, v in p.props.items():
        if v['uri'].startswith('dcatuk:'):
            t = URIRef(p.expand(v['uri']))
            g.add((t, RDF.type, OWL.DatatypeProperty if v['kind'] == 'boolean' else OWL.ObjectProperty if v['kind'] in ('concept', 'iri') else RDF.Property))
            g.add((t, RDFS.label, Literal(v['label'], lang='en')))
            g.add((t, RDFS.comment, Literal(v['definition'], lang='en')))
            g.add((t, RDFS.isDefinedBy, ont))
            if v.get('provisional'):
                g.add((t, URIRef('http://www.w3.org/2003/06/sw-vocab-status/ns#term_status'), Literal('unstable')))
    return g


def codelists_graph(p):
    g = Graph()
    for pre, ns in p.prefixes.items():
        g.bind(pre, Namespace(ns))
    for sk, s in p.codelists.items():
        if s.get('external'):
            continue
        scheme = URIRef(p.scheme_iri(sk))
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal(s['label'], lang='en')))
        g.add((scheme, SKOS.definition, Literal(s['definition'], lang='en')))
        for c in s['concepts']:
            n = URIRef(p.concept_iri(sk, c['code']))
            if c.get('uri'):
                g.add((n, SKOS.inScheme, scheme))
                g.add((n, SKOS.prefLabel, Literal(c['label'], lang='en')))
                continue
            g.add((n, RDF.type, SKOS.Concept))
            g.add((n, SKOS.inScheme, scheme))
            g.add((n, SKOS.topConceptOf, scheme))
            g.add((n, SKOS.notation, Literal(c['code'])))
            g.add((n, SKOS.prefLabel, Literal(c['label'], lang='en')))
            if c.get('definition'):
                g.add((n, SKOS.definition, Literal(c['definition'], lang='en')))
            if c.get('note'):
                g.add((n, SKOS.scopeNote, Literal(c['note'], lang='en')))
            if c.get('mem'):
                g.add((n, SKOS.hiddenLabel, Literal(c['mem'])))
            for kind, prop in (('exact', SKOS.exactMatch), ('close', SKOS.closeMatch)):
                if (c.get('maps') or {}).get(kind):
                    g.add((n, prop, URIRef(p.expand(c['maps'][kind]))))
            for also in c.get('also', []):
                g.add((n, SKOS.relatedMatch, URIRef(p.expand(also))))
            if c.get('see'):
                g.add((n, RDFS.seeAlso, URIRef(c['see'])))
    return g


def csv_text(rows, header):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def data_dictionary(p):
    rows = []
    for ck, c in p.classes.items():
        for x, prop in p.class_props(ck):
            mem = prop.get('mem') or {}
            rows.append([ck, x['p'], prop['label'], prop['uri'], x['ob'], x.get('cda', ''), x['card'], prop['kind'],
                         prop.get('range') or prop.get('codelist') or '', prop['definition'], mem.get('slot', ''), mem.get('change', ''),
                         prop.get('rma2026', ''), prop.get('dm', ''), SCHEMA_ORG.get(x['p'], ''),
                         ' '.join(str(i) for i in prop.get('issues', [])), 'yes' if prop.get('provisional') else ''])
    return csv_text(rows, ['class', 'property', 'label', 'uri', 'obligation', 'critical_data_asset_obligation', 'cardinality', 'kind',
                           'range_or_codelist', 'definition', 'mem_slot', 'change_from_mem', 'recording_metadata_2026', 'data_marketplace',
                           'schema_org', 'issues', 'provisional'])


def crosswalk_mem(p):
    rows = []
    for k, v in p.props.items():
        mem = v.get('mem') or {}
        if mem.get('slot'):
            rows.append([mem['slot'], k, v['uri'], mem['change'], mem.get('note', '')])
    rows.append(['type', '(class)', 'rdf:type', 'merged', 'The class of a record gives its type; there is no separate type property.'])
    return csv_text(sorted(rows), ['mem_slot', 'dcat_uk_ap_property', 'uri', 'change', 'note'])


def backlog_csv(p):
    rows = [[b['n'], b['title'], b['status'], b['resolution'].strip(), ' '.join(b.get('where', []))] for b in p.lineage['backlog']]
    return csv_text(rows, ['issue', 'title', 'status', 'resolution', 'where'])


def codelists_csv(p):
    rows = []
    for sk, s in p.codelists.items():
        for c in s['concepts']:
            m = c.get('maps') or {}
            rows.append([sk, c['code'], c['label'], p.concept_iri(sk, c['code']), c.get('definition', ''), c.get('mem', ''),
                         m.get('exact', '') or m.get('close', ''), 'exact' if m.get('exact') else 'close' if m.get('close') else ''])
    return csv_text(rows, ['codelist', 'code', 'label', 'iri', 'definition', 'mem_value', 'eu_match', 'match_type'])


def browser_profile(p):
    """A compact profile for the record builder and validator in the browser. Same rules as the SHACL."""
    out = {'meta': {k: p.meta[k] for k in ('id', 'title', 'version', 'status', 'as_of', 'codelist_base')},
           'prefixes': {k: v for k, v in p.prefixes.items() if k not in ('sh',)}, 'classes': {}, 'props': {}, 'codelists': {}, 'rules': p.rules}
    for ck, c in p.classes.items():
        out['classes'][ck] = {'uri': c['uri'], 'label': c['label'], 'one_of': c.get('one_of', []),
                              'props': [{'p': x['p'], 'ob': x['ob'], 'card': x['card'], 'cda': x.get('cda'), 'condition': x.get('condition')} for x in c['properties']]}
    for k, v in p.props.items():
        out['props'][k] = {kk: v.get(kk) for kk in ('uri', 'label', 'kind', 'range', 'codelist', 'definition', 'guidance', 'example', 'max_length', 'provisional') if v.get(kk) is not None}
    for sk, s in p.codelists.items():
        out['codelists'][sk] = {'label': s['label'], 'open': sk in ukap.OPEN_CODELISTS,
                                'concepts': [{'code': c['code'], 'label': c['label'], 'iri': p.concept_iri(sk, c['code']),
                                              'compact': compact_forms(p, sk)[i * 2 + 1], 'mem': c.get('mem')} for i, c in enumerate(s['concepts'])]}
    return out


def jsonld_doc(p, g):
    ctx = context(p)['@context']
    data = json.loads(g.serialize(format='json-ld', context=ctx, auto_compact=True))
    return data


def generate(p):
    """Return {relative path: str} for every generated file."""
    files = {}
    sh = shacl(p)
    files['dcat-uk-ap.shacl.ttl'] = sh.serialize(format='turtle')
    files['dcat-uk-ap.schema.json'] = json.dumps(json_schema(p), indent=2, ensure_ascii=False) + '\n'
    files['dcat-uk-ap.context.jsonld'] = json.dumps(context(p), indent=2) + '\n'
    files['dcat-uk-ap.linkml.yaml'] = linkml(p)
    files['dcat-uk-ap.ns.ttl'] = namespace_terms(p).serialize(format='turtle')
    cg = codelists_graph(p)
    files['codelists.ttl'] = cg.serialize(format='turtle')
    files['codelists.jsonld'] = cg.serialize(format='json-ld', indent=1)
    files['codelists.csv'] = codelists_csv(p)
    files['data-dictionary.csv'] = data_dictionary(p)
    files['crosswalk-mem.csv'] = crosswalk_mem(p)
    files['backlog.csv'] = backlog_csv(p)
    files['profile.json'] = json.dumps(browser_profile(p), ensure_ascii=False, separators=(',', ':'))
    orgs = p.orgs or {'orgs': []}
    files['organisations.json'] = json.dumps({k: orgs[k] for k in orgs if k != 'orgs'} | {'orgs': [[o['slug'], o['title'], o['type'], o['status']] for o in orgs['orgs']]},
                                             ensure_ascii=False, separators=(',', ':'))
    for e in p.examples:
        g = ukap.to_graph(p, e['record'])
        files[f'examples/{e["key"]}.ttl'] = g.serialize(format='turtle')
        files[f'examples/{e["key"]}.jsonld'] = json.dumps({'@context': p.meta['site_url'] + 'downloads/dcat-uk-ap.context.jsonld'} | {k: v for k, v in e['record'].items()}, indent=2, ensure_ascii=False) + '\n'
        files[f'examples/{e["key"]}.json'] = json.dumps(e['record'], indent=2, ensure_ascii=False) + '\n'
    return files
