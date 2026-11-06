#!/usr/bin/env node
/* DCAT-AP-UK MCP server. Lets an AI assistant read the profile and check, score, convert and export records.
   Model Context Protocol over stdio (JSON-RPC 2.0, one message per line). Read-only: no network, no files written.
   It uses the same validator as the portal (site_src/validator.js) and the generated profile.json, so its answers match the SHACL shapes.

   Run:   node integrations/mcp/server.js [--profile path/to/profile.json]
   The profile defaults to site/downloads/profile.json (run python3 -I tools/build.py first), or the DCAT_UK_AP_PROFILE environment variable.
   Licence: MIT. Not an official service; DCAT-AP-UK is a proposal, not endorsed. */
'use strict';
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const V = require(path.join(__dirname, '..', '..', 'site_src', 'validator.js'));

function profilePath() {
  const i = process.argv.indexOf('--profile');
  if (i > -1 && process.argv[i + 1]) return process.argv[i + 1];
  if (process.env.DCAT_UK_AP_PROFILE) return process.env.DCAT_UK_AP_PROFILE;
  return path.join(__dirname, '..', '..', 'site', 'downloads', 'profile.json');
}
const P = JSON.parse(fs.readFileSync(profilePath(), 'utf8'));
const PROTOCOL = '2025-06-18';

function prof(exts) { return exts && exts.length ? V.withExtensions(P, exts) : P; }
const extProp = { type: 'array', items: { type: 'string', enum: Object.keys(P.extensions || {}) }, description: 'Sector extensions to apply, for example ["health"].' };
const recProp = { type: 'object', description: 'A record in the compact JSON form of DCAT-AP-UK, with "class" set, for example "Dataset".' };

const TOOLS = [
  { name: 'profile_summary', description: 'What DCAT-AP-UK is, its version and status, its classes and its sector extensions.', inputSchema: { type: 'object', properties: {} },
    run: () => ({ meta: P.meta, status_note: 'Proposed, not endorsed. Not an official GOV.UK service.', classes: Object.keys(P.classes).map(k => ({ class: k, label: P.classes[k].label, properties: P.classes[k].props.length })),
      extensions: Object.keys(P.extensions || {}).map(k => ({ id: k, label: P.extensions[k].label })) }) },
  { name: 'describe_class', description: 'Every property of a class with its obligation (M, R, O, C) and cardinality, optionally with extensions applied.',
    inputSchema: { type: 'object', properties: { name: { type: 'string' }, extensions: extProp }, required: ['name'] },
    run: a => { const Q = prof(a.extensions); const C = Q.classes[a.name]; if (!C) throw new Error('No class ' + a.name + '. Classes: ' + Object.keys(Q.classes).join(', '));
      return { class: a.name, uri: C.uri, label: C.label, one_of: C.one_of, properties: C.props.map(x => Object.assign({ label: Q.props[x.p].label, uri: Q.props[x.p].uri }, x)) }; } },
  { name: 'describe_property', description: 'The definition, guidance, kind, codelist and example of a property, and the classes that use it.',
    inputSchema: { type: 'object', properties: { name: { type: 'string' }, extensions: extProp }, required: ['name'] },
    run: a => { const Q = prof(a.extensions); const p = Q.props[a.name]; if (!p) throw new Error('No property ' + a.name + '. Try search.');
      return Object.assign({ name: a.name, used_by: Object.keys(Q.classes).filter(k => Q.classes[k].props.some(x => x.p === a.name)).map(k => ({ class: k, entry: Q.classes[k].props.find(x => x.p === a.name) })) }, p); } },
  { name: 'list_codelist', description: 'The values of a codelist, with their identifiers.', inputSchema: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] },
    run: a => { const c = P.codelists[a.name]; if (!c) throw new Error('No codelist ' + a.name + '. Codelists: ' + Object.keys(P.codelists).join(', ')); return Object.assign({ name: a.name }, c); } },
  { name: 'search', description: 'Find properties, classes and codelists whose name, label or definition contains the words given.',
    inputSchema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] },
    run: a => { const w = String(a.query).toLowerCase().split(/\s+/).filter(Boolean); const hit = s => w.every(x => s.toLowerCase().indexOf(x) > -1);
      const props = Object.keys(P.props).filter(k => hit(k + ' ' + P.props[k].label + ' ' + P.props[k].definition)).map(k => ({ kind: 'property', name: k, label: P.props[k].label }));
      Object.keys(P.extensions || {}).forEach(e => Object.keys(P.extensions[e].props).forEach(k => { const p = P.extensions[e].props[k]; if (hit(k + ' ' + p.label + ' ' + p.definition)) props.push({ kind: 'property', name: k, label: p.label, extension: e }); }));
      return props.concat(Object.keys(P.classes).filter(k => hit(k + ' ' + P.classes[k].label)).map(k => ({ kind: 'class', name: k })),
        Object.keys(P.codelists).filter(k => hit(k + ' ' + P.codelists[k].label)).map(k => ({ kind: 'codelist', name: k }))).slice(0, 40); } },
  { name: 'validate_record', description: 'Check a record against DCAT-AP-UK (and any extensions). Returns errors, warnings, the conformance level and the quality score.',
    inputSchema: { type: 'object', properties: { record: recProp, extensions: extProp }, required: ['record'] },
    run: a => { const Q = prof(a.extensions); return { validation: V.validate(Q, a.record), conformance: V.conformance(Q, a.record), quality: V.fair(Q, a.record) }; } },
  { name: 'convert_mem', description: 'Convert a record in the xGov Metadata Exchange Model form to DCAT-AP-UK, listing what changed, and check it.',
    inputSchema: { type: 'object', properties: { record: { type: 'object' } }, required: ['record'] },
    run: a => { const c = V.fromMem(P, a.record); return { record: c.record, notes: c.notes, validation: V.validate(P, c.record) }; } },
  { name: 'convert_openapi', description: 'Draft a DCAT-AP-UK data service record from an OpenAPI description (parsed JSON). Email addresses are never copied.',
    inputSchema: { type: 'object', properties: { openapi: { type: 'object' }, url: { type: 'string', description: 'Where the OpenAPI description is published.' } }, required: ['openapi'] },
    run: a => { const c = V.fromOpenAPI(P, a.openapi, { url: a.url }); return { record: c.record, notes: c.notes, validation: V.validate(P, c.record) }; } },
  { name: 'export_record', description: 'Export a record as Turtle, schema.org JSON-LD or Croissant 1.1 (dataset level).',
    inputSchema: { type: 'object', properties: { record: recProp, format: { type: 'string', enum: ['turtle', 'schema.org', 'croissant'] }, extensions: extProp }, required: ['record', 'format'] },
    run: a => { const Q = prof(a.extensions); return a.format === 'turtle' ? V.toTurtle(Q, a.record) : a.format === 'croissant' ? V.toCroissant(Q, a.record) : V.toSchemaOrg(Q, a.record); } }
];

function reply(id, result) { process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: id, result: result }) + '\n'); }
function fail(id, code, message) { process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: id, error: { code: code, message: message } }) + '\n'); }

function handle(msg) {
  const id = msg.id;
  const isRequest = id !== undefined && id !== null;
  switch (msg.method) {
    case 'initialize':
      return reply(id, { protocolVersion: PROTOCOL, capabilities: { tools: {} },
        serverInfo: { name: 'dcat-ap-uk', version: P.meta.version },
        instructions: 'DCAT-AP-UK is a proposed UK application profile of DCAT, not endorsed. Use validate_record before claiming a record conforms.' });
    case 'ping': return reply(id, {});
    case 'tools/list': return reply(id, { tools: TOOLS.map(t => ({ name: t.name, description: t.description, inputSchema: t.inputSchema })) });
    case 'tools/call': {
      const t = TOOLS.find(x => x.name === (msg.params || {}).name);
      if (!t) return fail(id, -32602, 'Unknown tool ' + (msg.params || {}).name);
      try {
        const out = t.run((msg.params || {}).arguments || {});
        return reply(id, { content: [{ type: 'text', text: typeof out === 'string' ? out : JSON.stringify(out, null, 1) }], isError: false });
      } catch (e) { return reply(id, { content: [{ type: 'text', text: String(e.message || e) }], isError: true }); }
    }
    default:
      if (isRequest) return fail(id, -32601, 'Method not found: ' + msg.method);
  }
}

readline.createInterface({ input: process.stdin }).on('line', line => {
  if (!line.trim()) return;
  let msg;
  try { msg = JSON.parse(line); } catch (e) { return fail(null, -32700, 'Parse error'); }
  (Array.isArray(msg) ? msg : [msg]).forEach(handle);
});
