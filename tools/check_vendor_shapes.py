#!/usr/bin/env python3
"""Check weaver output and add-on kits against each vendor's own published schema (ADR 0021, D-035).

Each schema is fetched from the vendor's public repository at the commit content/vendors.yaml cites, so the check is
reproducible and moves only when the citation moves. Every worked dataset example is woven into each format and
validated. Some vendor requests also need fields that are not metadata (an Iceberg table schema, OpenMetadata columns);
those are reported as "to add at load time" and do not fail the check, because DCAT-AP-UK does not carry them.

Needs network access to github.com and node. Exit 1 on any problem. CI runs it on every build.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

WEAVE = r"""
const V = require(process.argv[1]); const d = JSON.parse(require('fs').readFileSync(0, 'utf8')); const o = {};
for (const m of d.models) o[m] = d.records.map(r => V.weave(d.P, 'ukap', m, r).out);
process.stdout.write(JSON.stringify(o));
"""


class Repo:
    """A sparse, blob-less fetch of one commit; files are read on demand."""
    def __init__(self, tmp, repo, sha):
        self.dir = Path(tmp) / repo.replace('/', '_')
        env = {'GIT_TERMINAL_PROMPT': '0', 'PATH': '/usr/bin:/bin:/usr/local/bin'}
        subprocess.run(['git', 'init', '-q', str(self.dir)], check=True)
        subprocess.run(['git', '-C', str(self.dir), 'fetch', '-q', '--depth', '1', '--filter=blob:none', f'https://github.com/{repo}', sha], check=True, env=env, timeout=300)
        self.sha, self.env = sha, env

    def read(self, path):
        return subprocess.run(['git', '-C', str(self.dir), 'show', f'{self.sha}:{path}'], check=True, capture_output=True, text=True, env=self.env).stdout

    def tree(self, prefix):
        out = subprocess.run(['git', '-C', str(self.dir), 'ls-tree', '-r', '--name-only', self.sha, prefix], check=True, capture_output=True, text=True, env=self.env).stdout
        return [x for x in out.splitlines() if x]


_FETCHED = {}
_HOME = []


def fetch(tmp, repo, sha):
    """One fetch per repository and commit for the life of the process (tests run the check many times)."""
    if (repo, sha) not in _FETCHED:
        if not _HOME:
            import atexit
            import shutil
            _HOME.append(tempfile.mkdtemp(prefix='vendor-shapes-'))
            atexit.register(shutil.rmtree, _HOME[0], True)
        _FETCHED[(repo, sha)] = Repo(_HOME[0], repo, sha)
    return _FETCHED[(repo, sha)]


def pin(vd, repo):
    for x in vd['vendors']:
        for r in x.get('repos', []):
            if r['repo'] == repo:
                return r['commit']
    raise SystemExit(f'{repo} is not cited in content/vendors.yaml')


def shape_problems(shapes, name, value, path='', partial=False):
    """Validate a value against a botocore (Smithy JSON) shape: types, members and required members."""
    s, bad = shapes[name], []
    t = s['type']
    if t == 'structure':
        if not isinstance(value, dict):
            return [f'{path or name}: expected an object']
        for k in value:
            if k not in s['members']:
                bad.append(f'{path}.{k}: not a member of {name}')
        if not partial:
            for k in s.get('required', []):
                if k not in value:
                    bad.append(f'{path or name}: missing required {k}')
        for k, v in value.items():
            if k in s['members']:
                bad += shape_problems(shapes, s['members'][k]['shape'], v, f'{path}.{k}')
    elif t == 'map':
        if not isinstance(value, dict):
            return [f'{path}: expected a map']
        for k, v in value.items():
            bad += shape_problems(shapes, s['value']['shape'], v, f'{path}[{k}]')
            if 'max' in shapes[s['key']['shape']] and len(k) > shapes[s['key']['shape']]['max']:
                bad.append(f'{path}: key {k} is longer than {shapes[s["key"]["shape"]]["max"]}')
    elif t == 'list':
        if not isinstance(value, list):
            return [f'{path}: expected a list']
        for i, v in enumerate(value):
            bad += shape_problems(shapes, s['member']['shape'], v, f'{path}[{i}]')
    elif t == 'string':
        if not isinstance(value, str):
            return [f'{path}: expected a string']
        if 'max' in s and len(value) > s['max']:
            bad.append(f'{path}: longer than {s["max"]} characters')
        if 'min' in s and len(value) < s['min']:
            bad.append(f'{path}: shorter than {s["min"]} characters')
    return bad


def check(vd, outputs, kits, tmp):
    problems, notes = [], []

    def fail(where, msgs):
        problems.extend(f'{where}: {m}' for m in msgs)

    # AWS Glue and Amazon SageMaker Catalog (DataZone): botocore service models
    bc = fetch(tmp, 'boto/botocore', pin(vd, 'boto/botocore'))
    glue = json.loads(bc.read('botocore/data/glue/2017-03-31/service-2.json'))['shapes']
    for i, o in enumerate(outputs['glue']):
        fail(f'glue example {i}', shape_problems(glue, 'TableInput', o, 'TableInput'))
    dz = json.loads(bc.read('botocore/data/datazone/2018-05-10/service-2.json'))['shapes']
    for i, o in enumerate(outputs['datazone']):
        miss = [k for k in dz['CreateAssetInput'].get('required', []) if k not in o]
        notes.append(f'datazone: add at load time {", ".join(miss)} (the domain, asset type and project are tenant choices)') if miss and i == 0 else None
        fail(f'datazone example {i}', shape_problems(dz, 'CreateAssetInput', o, 'CreateAssetInput', partial=True))

    # Apache Iceberg REST catalog: the OpenAPI CreateTableRequest
    ice = fetch(tmp, 'apache/iceberg', pin(vd, 'apache/iceberg'))
    api = yaml.safe_load(ice.read('open-api/rest-catalog-open-api.yaml'))
    sch = dict(api['components']['schemas']['CreateTableRequest'])
    miss = [k for k in sch.get('required', []) if k not in outputs['iceberg'][0]]
    if miss:
        notes.append(f'iceberg: add at load time {", ".join(miss)} (the table schema comes from the data, not the metadata)')
    sch.pop('required', None)
    doc = {'components': api['components'], **sch}
    v = jsonschema.Draft202012Validator(doc)
    for i, o in enumerate(outputs['iceberg']):
        fail(f'iceberg example {i}', [e.message for e in v.iter_errors(o)])

    # OpenLineage: the Dataset definition and the documentation facet, resolved through the spec's own $ids
    ol = fetch(tmp, 'OpenLineage/OpenLineage', pin(vd, 'OpenLineage/OpenLineage'))
    core = json.loads(ol.read('spec/OpenLineage.json'))
    docf = json.loads(ol.read('spec/facets/DocumentationDatasetFacet.json'))
    reg = Registry().with_resources([(core['$id'], Resource.from_contents(core)), (docf['$id'], Resource.from_contents(docf))])
    ds = jsonschema.Draft202012Validator({'$ref': core['$id'] + '#/$defs/Dataset'}, registry=reg)
    dv = jsonschema.Draft202012Validator({'$ref': docf['$id'] + '#/$defs/DocumentationDatasetFacet'}, registry=reg)
    for i, o in enumerate(outputs['openlineage']):
        fail(f'openlineage example {i}', [e.message for e in ds.iter_errors(o)])
        d = (o.get('facets') or {}).get('documentation')
        if d:
            fail(f'openlineage example {i} documentation facet', [e.message for e in dv.iter_errors(d)])
            if d.get('_schemaURL') != docf['$id']:
                fail(f'openlineage example {i}', [f'documentation facet _schemaURL {d.get("_schemaURL")} is not the spec\'s {docf["$id"]}'])
    jsonschema.Draft202012Validator.check_schema(kits['openlineage-facet'])

    # OpenMetadata: the table entity, with its relative references resolved from the spec folder
    om = fetch(tmp, 'open-metadata/OpenMetadata', pin(vd, 'open-metadata/OpenMetadata'))
    base = 'openmetadata-spec/src/main/resources/json/schema/'
    res = []
    for f in om.tree(base + 'type') + [base + 'entity/data/table.json']:
        if f.endswith('.json'):
            j = json.loads(om.read(f))
            if '$id' in j:
                res.append((j['$id'], Resource.from_contents(j, default_specification=DRAFT7)))
    reg = Registry().with_resources(res)
    table = json.loads(om.read(base + 'entity/data/table.json'))
    miss = [k for k in table.get('required', []) if k not in outputs['openmetadata'][0]]
    notes.append(f'openmetadata: add at load time {", ".join(miss)} (the id is assigned by the server; columns come from the data)') if miss else None
    tv = jsonschema.Draft7Validator({'$ref': table['$id'], 'definitions': {}}, registry=reg)
    for i, o in enumerate(outputs['openmetadata']):
        errs = [e for e in tv.iter_errors(o) if e.validator != 'required' or e.path]
        fail(f'openmetadata example {i}', [f'{"/".join(map(str, e.absolute_path))}: {e.message}' for e in errs])

    # Oracle OCI Data Catalog: the custom property kit against the SDK's CreateCustomPropertyDetails
    oci = fetch(tmp, 'oracle/oci-python-sdk', pin(vd, 'oracle/oci-python-sdk'))
    src = oci.read('src/oci/data_catalog/models/create_custom_property_details.py')
    names = set(re.findall(r"'[a-z_]+': '([a-zA-Z]+)'", src.split('self.attribute_map = {', 1)[1].split('}', 1)[0]))
    allowed = set(re.search(r'allowed_values = \[([^\]]+)\]', src).group(1).replace('"', '').replace(' ', '').split(','))
    for c in kits['oci-custom-properties']['customProperties']:
        fail(f'oci kit {c["displayName"]}', [f'{k} is not a CreateCustomPropertyDetails field' for k in c if k not in names])
        if c['dataType'] not in allowed:
            fail(f'oci kit {c["displayName"]}', [f'dataType {c["dataType"]} is not one of {sorted(allowed)}'])

    # DataHub: structured property kit keys against the project's own example file
    dh = fetch(tmp, 'datahub-project/datahub', pin(vd, 'datahub-project/datahub'))
    ex = yaml.safe_load(dh.read('metadata-ingestion/examples/structured_properties/structured_properties.yaml'))
    keys = {k for p in ex for k in p}
    types = {p['type'] for p in ex}
    for p in yaml.safe_load(kits['datahub-structured-properties']):
        fail(f'datahub kit {p["id"]}', [f'{k} is not a key the DataHub examples use' for k in p if k not in keys])
        if p['type'] not in types:
            fail(f'datahub kit {p["id"]}', [f'type {p["type"]} is not one the examples use'])
    return problems, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    import ukap
    import build
    vd = yaml.safe_load((ROOT / 'content' / 'vendors.yaml').read_text(encoding='utf-8'))
    p = ukap.load()
    site = build.Site.__new__(build.Site)
    site.vd, site.p = vd, p
    kits = build.Site.vendor_kits(site)
    prof = json.loads((ROOT / 'site' / 'downloads' / 'profile.json').read_text(encoding='utf-8'))
    recs = [e['record'] for e in p.examples if e['record'].get('class') == 'Dataset']
    models = ['glue', 'datazone', 'iceberg', 'openlineage', 'openmetadata']
    out = subprocess.run(['node', '-e', WEAVE, str(ROOT / 'site_src' / 'validator.js')], input=json.dumps({'P': prof, 'records': recs, 'models': models}),
                         capture_output=True, text=True, check=True)
    outputs = json.loads(out.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        problems, notes = check(vd, outputs, kits, tmp)
    for n in notes:
        print('note ' + n)
    for x in problems:
        print('FAIL ' + x)
    print(f'{len(recs)} dataset examples in {len(models)} formats, and 3 kits: {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
