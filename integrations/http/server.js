#!/usr/bin/env node
/* DCAT-AP-UK reference HTTP API: check, score, weave and read the profile over HTTP, for products that cannot embed JavaScript.
   Uses the portal's validator, so its verdicts match the SHACL shapes. Node standard library only; no outbound requests; nothing stored.
   Run: node integrations/http/server.js [--profile path] [--port 8787] [--host 127.0.0.1]
   Described by downloads/integration-api.openapi.json. Licence: MIT. DCAT-AP-UK is a proposal, not endorsed; this is a reference, not a service. */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const V = require(path.join(__dirname, '..', '..', 'site_src', 'validator.js'));

function arg(name, dflt) { const i = process.argv.indexOf('--' + name); return i > -1 ? process.argv[i + 1] : dflt; }
const P0 = JSON.parse(fs.readFileSync(arg('profile', process.env.DCAT_UK_AP_PROFILE || path.join(__dirname, '..', '..', 'site', 'downloads', 'profile.json')), 'utf8'));
const MAX = 1024 * 1024;

function send(res, code, body) {
  const s = typeof body === 'string' ? body : JSON.stringify(body, null, 1);
  res.writeHead(code, { 'content-type': typeof body === 'string' ? 'text/turtle; charset=utf-8' : 'application/json; charset=utf-8', 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' });
  res.end(s);
}
function prof(q) { const e = (q.get('ext') || '').split(',').filter(Boolean); return e.length ? V.withExtensions(P0, e) : P0; }

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (req.method === 'GET') {
    if (u.pathname === '/health') return send(res, 200, { ok: true, profile: P0.meta.id, version: P0.meta.version });
    if (u.pathname === '/profile') return send(res, 200, { meta: P0.meta, classes: Object.keys(P0.classes), codelists: Object.keys(P0.codelists), extensions: Object.keys(P0.extensions || {}) });
    const m = /^\/codelists\/([a-z0-9-]+)$/.exec(u.pathname);
    if (m) return P0.codelists[m[1]] ? send(res, 200, P0.codelists[m[1]]) : send(res, 404, { error: 'No codelist ' + m[1] });
    return send(res, 404, { error: 'Not found' });
  }
  if (req.method !== 'POST') return send(res, 405, { error: 'Use GET or POST' });
  let size = 0, chunks = [];
  req.on('data', c => { size += c.length; if (size > MAX) { send(res, 413, { error: 'Body over 1 MiB' }); req.destroy(); } else chunks.push(c); });
  req.on('end', () => {
    if (size > MAX) return;
    let body;
    try { body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); } catch (e) { return send(res, 400, { error: 'The body is not JSON' }); }
    try {
      const P = prof(u.searchParams);
      if (u.pathname === '/validate') return send(res, 200, { validation: V.validate(P, body), conformance: V.conformance(P, body) });
      if (u.pathname === '/score') return send(res, 200, V.fair(P, body));
      if (u.pathname === '/weave') {
        const w = V.weave(P, u.searchParams.get('from') || 'ukap', u.searchParams.get('to') || 'ukap', body);
        return typeof w.out === 'string' && u.searchParams.get('to') === 'turtle' ? send(res, 200, w.out) : send(res, 200, w);
      }
      return send(res, 404, { error: 'Not found' });
    } catch (e) { return send(res, 400, { error: String(e.message || e) }); }
  });
});
const port = Number(arg('port', 8787)), host = arg('host', '127.0.0.1');
server.listen(port, host, () => process.stdout.write('DCAT-AP-UK reference API on http://' + host + ':' + server.address().port + '\n'));
