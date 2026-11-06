#!/usr/bin/env node
/* DCAT-AP-UK command-line checker. Uses the portal's validator, so its verdicts match the SHACL shapes and JSON Schema.
   Usage: node integrations/cli/validate.js [--profile site/downloads/profile.json] [--ext health] [--from ckan] [--format text|json|github] FILE...
   FILE may be JSON (one record or an array), or CSV in the spreadsheet template's columns. Exit code 1 if any record has an error.
   No network requests. Licence: MIT. DCAT-AP-UK is a proposal, not endorsed. */
'use strict';
const fs = require('fs');
const path = require('path');
const V = require(path.join(__dirname, '..', '..', 'site_src', 'validator.js'));

function arg(name, dflt) { const i = process.argv.indexOf('--' + name); return i > -1 ? process.argv[i + 1] : dflt; }
const flags = new Set(['--profile', '--ext', '--from', '--format']);
const files = process.argv.slice(2).filter((a, i, all) => !a.startsWith('--') && !flags.has(all[i - 1]));
const profile = arg('profile', process.env.DCAT_UK_AP_PROFILE || path.join(__dirname, '..', '..', 'site', 'downloads', 'profile.json'));
const P0 = JSON.parse(fs.readFileSync(profile, 'utf8'));
const exts = (arg('ext', '') || '').split(',').filter(Boolean);
const P = exts.length ? V.withExtensions(P0, exts) : P0;
const from = arg('from', 'ukap');
const format = arg('format', 'text');
if (!files.length) { process.stderr.write('Give one or more files to check.\n'); process.exit(2); }

let failed = 0;
const report = [];
for (const f of files) {
  const text = fs.readFileSync(f, 'utf8');
  let records;
  if (/\.csv$/i.test(f)) records = V.fromCSV(P, text).records;
  else { const d = JSON.parse(text); records = Array.isArray(d) ? d : (d['@graph'] || [d]); }
  records.forEach((r, i) => {
    const rec = from === 'ukap' ? r : V.weave(P, from, 'ukap', r).record;
    const res = V.validate(P, rec), lv = V.conformance(P, rec);
    if (!res.ok) failed++;
    report.push({ file: f, index: i, id: rec.id || null, ok: res.ok, level: lv.level, label: lv.label, score: lv.score, issues: res.issues });
  });
}
if (format === 'json') process.stdout.write(JSON.stringify(report, null, 1) + '\n');
else for (const r of report) {
  const where = r.file + (report.filter(x => x.file === r.file).length > 1 ? ' record ' + (r.index + 1) : '');
  if (format === 'github') r.issues.forEach(i => process.stdout.write('::' + (i.level === 'error' ? 'error' : 'warning') + ' file=' + r.file + ',title=DCAT-AP-UK ' + i.rule + '::' + (i.prop || '') + ': ' + i.text + '\n'));
  process.stdout.write((r.ok ? 'pass ' : 'FAIL ') + where + ': ' + r.label + ', quality ' + r.score + ' of 405\n');
  if (format === 'text') r.issues.forEach(i => process.stdout.write('  ' + i.level + ' ' + i.rule + ' ' + (i.prop || '') + ': ' + i.text + '\n'));
}
process.exit(failed ? 1 : 0);
