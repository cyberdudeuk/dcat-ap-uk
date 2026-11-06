/* DCAT-UK AP record validator. Runs in the browser (record builder, validator page) and in Node (tests).
   Reads the generated profile.json, so it applies the same obligations and rules as the SHACL shapes.
   Pure functions, no network, no storage. Licence: MIT. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.UKAPValidator = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var DATE = /^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$/;
  var URL_RE = /^https?:\/\/[^\s]+$/;
  var EMAIL = /^(mailto:)?[^@\s]+@[^@\s]+\.[^@\s]+$/;

  function asList(v) { return v === undefined || v === null || v === '' ? [] : (Array.isArray(v) ? v : [v]); }
  function present(v) { return asList(v).filter(function (x) { return x !== '' && x !== null; }).length > 0; }

  function expand(P, s) {
    s = String(s);
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(s) || s.indexOf('mailto:') === 0) return s;
    var i = s.indexOf(':');
    if (i > 0 && P.prefixes[s.slice(0, i)]) return P.prefixes[s.slice(0, i)] + s.slice(i + 1);
    return s;
  }

  function conceptOk(P, cl, v) {
    var list = P.codelists[cl];
    if (!list || list.open) return true;
    var full = expand(P, v);
    return list.concepts.some(function (c) { return c.iri === full; });
  }

  // Validate one compact record. Returns {ok, issues:[{level, prop, rule, text}]} where level is error|warning|info.
  function validate(P, rec, path) {
    var issues = [];
    path = path || '';
    function add(level, prop, rule, text) { issues.push({ level: level, prop: path + prop, rule: rule, text: text }); }
    if (!rec || typeof rec !== 'object') { add('error', '', 'S-01', 'The record is not an object.'); return finish(issues); }
    var ck = rec['class'];
    var C = P.classes[ck];
    if (!C) { add('error', 'class', 'S-02', 'Unknown or missing class "' + ck + '". Use one of: ' + Object.keys(P.classes).join(', ') + '.'); return finish(issues); }
    var known = { 'class': 1, id: 1 };
    var cda = String(rec.criticalDataAsset) === 'true';
    C.props.forEach(function (x) {
      known[x.p] = 1;
      var prop = P.props[x.p];
      var vals = asList(rec[x.p]);
      var has = present(rec[x.p]);
      var ob = (cda && x.cda) ? x.cda : x.ob;
      if (!has) {
        if (ob === 'M') add('error', x.p, cda && x.cda === 'M' && x.ob !== 'M' ? 'R-04' : 'M-01',
          (cda && x.cda === 'M' && x.ob !== 'M' ? 'Critical data assets must give ' : 'Give ') + prop.label.toLowerCase() + '.');
        else if (ob === 'R') add('warning', x.p, 'R-00', 'Recommended: ' + prop.label.toLowerCase() + '.');
        return;
      }
      if ((x.card === '1' || x.card === '0..1') && vals.length > 1) add('error', x.p, 'C-01', prop.label + ' takes one value, not ' + vals.length + '.');
      vals.forEach(function (v, i) {
        var where = x.p + (vals.length > 1 ? '[' + i + ']' : '');
        var s = typeof v === 'object' ? null : String(v);
        switch (prop.kind) {
          case 'date': if (!DATE.test(s)) add('error', where, 'D-01', prop.label + ' must be an ISO 8601 date, such as 2026-11-06.'); break;
          case 'url': if (!URL_RE.test(s)) add('error', where, 'U-01', prop.label + ' must be a web address starting https:// or http://.'); break;
          case 'email': if (!EMAIL.test(s)) add('error', where, 'R-06', 'A team email address must be a mailto address.'); break;
          case 'integer': if (!/^\d+$/.test(s)) add('error', where, 'N-01', prop.label + ' must be a whole number.'); break;
          case 'decimal': if (!/^\d+(\.\d+)?$/.test(s)) add('error', where, 'N-02', prop.label + ' must be a number.'); break;
          case 'boolean': if (s !== 'true' && s !== 'false') add('error', where, 'B-01', prop.label + ' must be true or false.'); break;
          case 'concept':
            if (!conceptOk(P, prop.codelist, s)) add('error', where, 'V-01', '"' + s + '" is not in the ' + P.codelists[prop.codelist].label.toLowerCase() + ' list.');
            if (prop.codelist === 'language' && expand(P, s).indexOf(P.prefixes.eulang) !== 0) add('error', where, 'V-02', 'Use a language from the EU language list.');
            break;
          case 'object':
            if (v && typeof v === 'object') {
              var sub = Object.assign({ 'class': prop.range }, v);
              validate(P, sub, where + '.').issues.forEach(function (it) { issues.push(it); });
            } else if (!s || /\s/.test(s)) add('error', where, 'U-02', prop.label + ' must be an identifier (a web address) or a description.');
            break;
          default:
            if (typeof v === 'object') add('error', where, 'S-03', prop.label + ' must be text, not a structure.');
        }
        if (prop.max_length && s && s.length > prop.max_length) add('error', where, 'R-05', prop.label + ' must be ' + prop.max_length + ' characters or fewer (it is ' + s.length + ').');
        var pat = x.pattern || prop.pattern || (P.codelists[prop.codelist] || {}).pattern;
        if (pat && s !== null && !(new RegExp(pat)).test(s)) add('error', where, 'P-01', prop.label + ' "' + s + '" is not in the expected form' + (x.pattern ? ' for this extension' : '') + '.');
        if (prop.codelist === 'checksum-algorithm' && s) {
          var cc = P.codelists[prop.codelist].concepts.filter(function (c) { return c.iri === expand(P, s); })[0];
          if (cc && cc.status === 'deprecated') add('warning', where, 'Q-01', cc.label + ' is weak. Use SHA-256 or stronger; SHA-384, SHA-512 or SHA3 for long-lived files.');
        }
      });
    });
    Object.keys(rec).forEach(function (k) { if (!known[k]) add('error', k, 'S-04', '"' + k + '" is not a property of ' + C.label.toLowerCase() + ' in this profile.'); });
    if (C.one_of && C.one_of.length) {
      if (!C.one_of.some(function (k) { return present(rec[k]); })) {
        var r = P.rules.filter(function (r) { return r['class'] === ck && (r.id === 'R-01' || r.id === 'R-02'); })[0];
        add('error', C.one_of.join(' or '), r ? r.id : 'R-01', r ? r.text : 'Give one of ' + C.one_of.join(', ') + '.');
      }
    }
    if ((ck === 'Dataset' || ck === 'DataService') && present(rec.accessRights) && !/\/open$/.test(expand(P, rec.accessRights)) && !present(rec.rights)) {
      add('error', 'rights', 'R-03', 'When access rights are commercial or internal, give a rights statement saying how to ask for the data.');
    }
    if ((ck === 'Dataset' || ck === 'DataService') && P.triggers && present(rec.personalData) && present(rec.jurisdiction) && !present(rec.transferMechanism)) {
      var pd = asList(rec.personalData).map(function (v) { return expand(P, v); });
      var outside = asList(rec.jurisdiction).filter(function (v) { return P.triggers.uk.indexOf(expand(P, v)) < 0; });
      if (pd.some(function (v) { return P.triggers.personal.indexOf(v) > -1; }) && outside.length)
        add('error', 'transferMechanism', 'R-08', 'The data contains personal data and is held in or sent to ' + outside.map(function (v) { return String(v).split('/').pop().toUpperCase(); }).join(', ') + ', outside the UK. Give the transfer safeguard.');
    }
    if (ck === 'PeriodOfTime' && present(rec.startDate) && present(rec.endDate) && String(rec.endDate) < String(rec.startDate)) {
      add('error', 'endDate', 'R-07', "A period's end date must not be before its start date.");
    }
    return finish(issues);
  }

  function finish(issues) {
    var errors = issues.filter(function (i) { return i.level === 'error'; }).length;
    return { ok: errors === 0, errors: errors, warnings: issues.length - errors, issues: issues };
  }

  // Completeness score: share of mandatory and recommended properties given (for the record builder's meter).
  function completeness(P, rec) {
    var C = P.classes[rec && rec['class']];
    if (!C) return { mandatory: [0, 0], recommended: [0, 0] };
    var cda = String(rec.criticalDataAsset) === 'true';
    var m = [0, 0], r = [0, 0];
    C.props.forEach(function (x) {
      var ob = (cda && x.cda) ? x.cda : x.ob;
      var t = ob === 'M' ? m : ob === 'R' ? r : null;
      if (!t) return;
      t[1]++;
      if (present(rec[x.p])) t[0]++;
    });
    return { mandatory: m, recommended: r };
  }

  // Convert a record from the xGov MEM YAML/JSON form to DCAT-UK AP, using the crosswalk. Returns {record, notes}.
  function fromMem(P, mem) {
    var notes = [];
    var map = { 'dcat:Dataset': 'Dataset', 'dcat:DataService': 'DataService', 'dcat:Distribution': 'Distribution' };
    var out = { 'class': map[mem.type] || 'Dataset' };
    if (mem.identifier) { if (/^https?:/.test(mem.identifier)) out.id = mem.identifier; out.identifier = String(mem.identifier); }
    var simple = { title: 'title', description: 'description', alternativeTitle: 'alternative', keyword: 'keyword', issued: 'issued', modified: 'modified',
      created: 'created', version: 'version', downloadURL: 'downloadURL', byteSize: 'byteSize', relatedResource: 'relation', summary: 'abstract',
      endpointDescription: 'endpointDescription', accessService: 'accessService' };
    Object.keys(simple).forEach(function (k) { if (mem[k] !== undefined) out[simple[k]] = mem[k]; });
    if (mem.summary) notes.push('summary became abstract (dct:abstract).');
    if (mem.endpointURL) out.endpointURL = [mem.endpointURL];
    if (mem.servesData) { out.servesDataset = mem.servesData; notes.push('servesData was renamed servesDataset.'); }
    function org(s) { return /^https?:/.test(s) ? s : 'https://www.gov.uk/government/organisations/' + s; }
    if (mem.publisher) out.publisher = org(mem.publisher);
    if (mem.creator) out.creator = asList(mem.creator).map(org);
    var codes = function (cl, v) {
      var c = (P.codelists[cl].concepts.filter(function (c) { return c.mem === v || c.code === String(v).toLowerCase().replace(/_/g, '-'); })[0]);
      return c ? c.compact : null;
    };
    if (mem.accessRights) out.accessRights = codes('access-rights', mem.accessRights) || mem.accessRights;
    if (mem.securityClassification) {
      if (mem.securityClassification === 'NOT_APPLICABLE') { out.securityClassification = 'ukcl:security-classification/official'; notes.push('NOT_APPLICABLE is withdrawn; set to OFFICIAL. Check this is right.'); }
      else out.securityClassification = 'ukcl:security-classification/' + String(mem.securityClassification).toLowerCase().replace(/_/g, '-');
    }
    if (mem.updateFrequency) {
      var f = P.codelists.frequency.concepts.filter(function (c) { return c.mem === mem.updateFrequency; })[0];
      out.accrualPeriodicity = f ? f.compact : mem.updateFrequency;
    }
    if (mem.licence) {
      if (/^(DATA_SHARE|DATA_SHARE_REQUEST|DATA_SHARE_AGREEMENT)$/.test(mem.licence)) { out.licence = 'ukcl:licences/data-sharing-agreement-required'; notes.push('The licence value became "data sharing agreement required". Add a rights statement.'); }
      else out.licence = mem.licence;
    }
    if (mem.theme) out.theme = asList(mem.theme).map(function (t) {
      var m = /topic%5D=([^&]+)/.exec(t);
      if (m) return 'ukcl:theme/' + decodeURIComponent(m[1]).replace(/\+/g, ' ').toLowerCase().replace(/ /g, '-');
      notes.push('Theme ' + t + ' is not a data.gov.uk topic. Choose a theme from the list.');
      return t;
    });
    if (mem.serviceStatus) out.serviceStatus = 'ukcl:service-status/' + String(mem.serviceStatus).toLowerCase().replace(/_/g, '-');
    if (mem.serviceType) out.serviceType = 'ukcl:service-type/' + String(mem.serviceType).toLowerCase();
    if (mem.mediaType) out.mediaType = /^https?:/.test(mem.mediaType) ? mem.mediaType : 'https://www.iana.org/assignments/media-types/' + mem.mediaType;
    if (mem.contactPoint) {
      var cp = { fn: mem.contactPoint.contactName };
      if (mem.contactPoint.email) { cp.hasEmail = 'mailto:' + mem.contactPoint.email; notes.push('The contact email was kept. A contact form is preferred; add one as the contact form.'); }
      if (mem.contactPoint.address && /^https?:/.test(mem.contactPoint.address)) cp.hasURL = mem.contactPoint.address;
      if (mem.contactPoint.telephone) cp.hasTelephone = mem.contactPoint.telephone;
      out.contactPoint = [cp];
    }
    if (mem.distribution) { out.distribution = asList(mem.distribution); }
    if (out['class'] === 'Distribution' && mem.downloadURL) out.accessURL = [mem.downloadURL];
    if (!out.id) delete out.id;
    return { record: out, notes: notes };
  }


  // ---- extensions ------------------------------------------------------------------------------------------
  // The base profile plus the named sector extensions. Same merge as tools/ukap.py Profile.with_extensions.
  function withExtensions(P, ids) {
    var Q = JSON.parse(JSON.stringify(P));
    Q.applied = [];
    (ids || []).forEach(function (id) {
      var e = P.extensions && P.extensions[id];
      if (!e) throw new Error('Unknown extension ' + id);
      Object.keys(e.props).forEach(function (k) { Q.props[k] = e.props[k]; });
      Object.keys(e.new_classes).forEach(function (k) { Q.classes[k] = e.new_classes[k]; });
      Object.keys(e.classes).forEach(function (ck) {
        var list = Q.classes[ck].props;
        e.classes[ck].forEach(function (x) {
          var cur = list.filter(function (y) { return y.p === x.p; })[0];
          if (cur) Object.keys(x).forEach(function (k) { cur[k] = x[k]; }); else list.push(JSON.parse(JSON.stringify(x)));
        });
      });
      Q.applied.push(id);
    });
    return Q;
  }

  // ---- quality score -------------------------------------------------------------------------------------
  // Modelled on the dimensions and points of the data.europa.eu Metadata Quality Assessment (405 points; provenance K).
  // Offline, so addresses are checked for form, not fetched. The weights are this profile's reading, not the EU's tool.
  var OPEN_TYPES = /\/(text\/csv|application\/json|application\/geo\+json|application\/ld\+json|text\/turtle|application\/rdf\+xml|application\/xml|text\/xml|application\/geopackage\+sqlite3|application\/vnd\.apache\.parquet|application\/x-netcdf|application\/n-triples|application\/x-ndjson|text\/plain|application\/zip|text\/html|application\/pdf)$/;
  var MACHINE_TYPES = /\/(text\/csv|application\/json|application\/geo\+json|application\/ld\+json|text\/turtle|application\/rdf\+xml|application\/xml|text\/xml|application\/geopackage\+sqlite3|application\/vnd\.apache\.parquet|application\/x-netcdf|application\/n-triples|application\/x-ndjson)$/;
  var IANA = 'https://www.iana.org/assignments/media-types/';
  function fair(P, rec) {
    rec = rec || {};
    var ck = rec['class'], service = ck === 'DataService';
    var dists = asList(rec.distribution).filter(function (d) { return d && typeof d === 'object'; });
    function any(f) { return dists.some(f); }
    function anyVal(k, test) { return any(function (d) { return asList(d[k]).some(function (v) { return test ? test(String(v)) : present(v); }); }); }
    var res = validate(P, rec);
    var licences = (P.codelists.licences || { concepts: [] }).concepts.map(function (c) { return c.iri; });
    var dims = [
      { id: 'findability', label: 'Findability', items: [['keyword', 'Keywords', 30, present(rec.keyword)], ['theme', 'Themes', 30, present(rec.theme)],
        ['spatial', 'Place covered', 20, present(rec.spatial)], ['temporal', 'Time covered', 20, present(rec.temporal)]] },
      { id: 'accessibility', label: 'Accessibility', items: service ? [
        ['endpointURL', 'Endpoint address', 50, asList(rec.endpointURL).some(function (v) { return URL_RE.test(v); })],
        ['endpointDescription', 'Endpoint description', 20, present(rec.endpointDescription)],
        ['https', 'Endpoint uses HTTPS', 30, asList(rec.endpointURL).some(function (v) { return /^https:/.test(v); })]] : [
        ['accessURL', 'Access address on a distribution', 50, anyVal('accessURL', function (v) { return URL_RE.test(v); })],
        ['downloadURL', 'Download address', 20, anyVal('downloadURL')],
        ['https', 'Download address uses HTTPS', 30, anyVal('downloadURL', function (v) { return /^https:/.test(v); })]] },
      { id: 'interoperability', label: 'Interoperability', items: service ? [
        ['conformsTo', 'Standard the service follows', 40, present(rec.conformsTo)],
        ['endpointDescription', 'Machine-readable description', 40, present(rec.endpointDescription)],
        ['conforms', 'Conforms to DCAT-UK AP', 30, res.ok]] : [
        ['format', 'Format', 20, anyVal('format') || anyVal('mediaType')],
        ['mediaType', 'Media type', 10, anyVal('mediaType')],
        ['mediaTypeIana', 'Media type from the IANA list', 10, anyVal('mediaType', function (v) { return expand(P, v).indexOf(IANA) === 0; })],
        ['open', 'Non-proprietary format', 20, anyVal('mediaType', function (v) { return OPEN_TYPES.test(expand(P, v)); })],
        ['machine', 'Machine-readable format', 20, anyVal('mediaType', function (v) { return MACHINE_TYPES.test(expand(P, v)); })],
        ['conforms', 'Conforms to DCAT-UK AP', 30, res.ok]] },
      { id: 'reusability', label: 'Reusability', items: [
        ['licence', 'Licence', 20, present(rec.licence) || anyVal('licence')],
        ['licenceList', 'Licence from the list', 10, asList(rec.licence).some(function (v) { return licences.indexOf(expand(P, v)) > -1 || /^ukcl:licences\//.test(v); })],
        ['accessRights', 'Access rights', 10, present(rec.accessRights)],
        ['accessRightsList', 'Access rights from the list', 5, present(rec.accessRights) && conceptOk(P, 'access-rights', asList(rec.accessRights)[0])],
        ['contactPoint', 'Contact point', 20, present(rec.contactPoint)],
        ['publisher', 'Publisher', 10, present(rec.publisher)]] },
      { id: 'contextuality', label: 'Contextuality', items: [
        ['rights', 'Rights statement or open access', 5, present(rec.rights) || /\/open$/.test(expand(P, asList(rec.accessRights)[0] || ''))],
        ['byteSize', 'File size', 5, service ? present(rec.documentation) : anyVal('byteSize')],
        ['issued', 'Date issued', 5, present(rec.issued)],
        ['modified', 'Date modified', 5, present(rec.modified)]] }
    ];
    var total = 0, max = 0;
    dims.forEach(function (d) {
      d.score = 0; d.max = 0;
      d.items = d.items.map(function (it) { d.max += it[2]; if (it[3]) d.score += it[2]; return { id: it[0], label: it[1], points: it[2], met: !!it[3] }; });
      total += d.score; max += d.max;
    });
    var rating = total >= 351 ? 'Excellent' : total >= 221 ? 'Good' : total >= 121 ? 'Sufficient' : 'Bad';
    return { score: total, max: max, rating: rating, dimensions: dims };
  }

  // Conformance levels: 1 Core (no errors), 2 Rich (and every recommended property), 3 Exemplary (and an excellent quality score).
  function conformance(P, rec) {
    var res = validate(P, rec), q = fair(P, rec);
    var recs = res.issues.filter(function (i) { return i.rule === 'R-00'; }).length;
    var level = !res.ok ? 0 : recs ? 1 : q.rating === 'Excellent' ? 3 : 2;
    var labels = ['Does not conform', 'Level 1: Core', 'Level 2: Rich', 'Level 3: Exemplary'];
    var next = level === 0 ? 'Fix ' + res.errors + ' error' + (res.errors === 1 ? '' : 's') + ' to reach level 1.'
      : level === 1 ? 'Give the ' + recs + ' recommended propert' + (recs === 1 ? 'y' : 'ies') + ' to reach level 2.'
      : level === 2 ? 'Raise the quality score from ' + q.score + ' to 351 or more to reach level 3.' : 'The highest level.';
    return { level: level, label: labels[level], next: next, errors: res.errors, recommended: recs, score: q.score, rating: q.rating };
  }

  // ---- converters ------------------------------------------------------------------------------------------
  // Read CSV (RFC 4180). Returns an array of rows (arrays of strings).
  function parseCSV(text) {
    var rows = [], row = [], cell = '', q = false, i, c;
    text = String(text).replace(/^﻿/, '');
    for (i = 0; i < text.length; i++) {
      c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
      else if (c === '"') q = true;
      else if (c === ',') { row.push(cell); cell = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
      else cell += c;
    }
    if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (x) { return x.trim() !== ''; }); });
  }

  // Spreadsheet rows to records: one row per record, columns named by property ("contactPoint.fn" for a part), repeats split by " | ".
  function fromCSV(P, text) {
    var rows = parseCSV(text), notes = [];
    if (!rows.length) return { records: [], notes: ['The file is empty.'] };
    var head = rows[0].map(function (h) { return h.trim(); });
    var records = rows.slice(1).map(function (r, n) {
      var rec = { 'class': 'Dataset' };
      head.forEach(function (h, i) {
        var v = (r[i] || '').trim(); if (!v) return;
        if (h === 'class' || h === 'id') { rec[h] = v; return; }
        var parts = h.split('.'), k = parts[0], prop = P.props[k];
        if (!prop) { if (n === 0) notes.push('Column "' + h + '" is not a property; it was ignored.'); return; }
        var C = P.classes[rec['class']] || P.classes.Dataset;
        var x = C.props.filter(function (y) { return y.p === k; })[0] || { card: '0..n' };
        if (parts.length === 1) {
          var multi = /n$/.test(x.card) && ['title', 'description', 'rights', 'versionNotes'].indexOf(k) < 0;
          rec[k] = multi ? v.split(/\s*\|\s*/).filter(Boolean) : v;
          return;
        }
        var sub = parts[1], R = P.classes[prop.range] || { props: [] };
        var sx = R.props.filter(function (y) { return y.p === sub; })[0] || { card: '0..1' };
        var obj = (rec[k] = rec[k] || [{}])[0];
        if (prop.range === 'Distribution') obj['class'] = 'Distribution';
        obj[sub] = /n$/.test(sx.card) ? v.split(/\s*\|\s*/).filter(Boolean) : v;
      });
      return rec;
    });
    return { records: records, notes: notes };
  }

  // An OpenAPI description (as parsed JSON) to a data service record. Returns {record, notes}. Email addresses are never copied.
  function fromOpenAPI(P, oas, opts) {
    opts = opts || {};
    var notes = [], info = (oas && oas.info) || {};
    if (!oas || !(oas.openapi || oas.swagger)) notes.push('This does not look like an OpenAPI description; it has no "openapi" field.');
    var rec = { 'class': 'DataService' };
    if (info.title) rec.title = info.title; else notes.push('The description has no title.');
    if (info.description || info.summary) rec.description = String(info.description || info.summary).trim();
    if (info.version) rec.version = String(info.version);
    var base = opts.url ? String(opts.url) : '';
    var servers = (oas && oas.servers || []).map(function (s) { var u = String(s.url || ''); if (/^\//.test(u) && base) { var m = /^(https?:\/\/[^/]+)/.exec(base); if (m) u = m[1] + u; } return u; });
    var abs = servers.filter(function (u) { return URL_RE.test(u); });
    if (abs.length) rec.endpointURL = abs; else notes.push('No absolute server address was found. Add the endpoint address.');
    if (servers.length > abs.length) notes.push(String(servers.length - abs.length) + ' relative server address(es) could not be made absolute.');
    if (base) rec.endpointDescription = [base];
    var ver = String(oas && (oas.openapi || oas.swagger) || '');
    if (/^3\.\d+\.\d+$/.test(ver)) rec.conformsTo = ['https://spec.openapis.org/oas/v' + ver];
    else if (/^2\./.test(ver)) rec.conformsTo = ['https://swagger.io/specification/v2/'];
    rec.serviceType = 'ukcl:service-type/rest';
    if (info.license && info.license.url) rec.licence = info.license.url;
    else notes.push('No licence address was found. Choose the licence.');
    var c = info.contact || {};
    var cp = { fn: c.name || ((info.title || 'API') + ' team') };
    if (c.url && URL_RE.test(c.url)) cp.hasURL = c.url;
    if (c.email) notes.push('The contact email address was not copied. Give a contact form address instead.');
    if (cp.hasURL) rec.contactPoint = [cp]; else notes.push('No contact form address was found. Add one.');
    var tags = (oas && oas.tags || []).map(function (t) { return t && t.name; }).filter(Boolean);
    if (tags.length) rec.keyword = tags;
    rec.identifier = opts.identifier || String(info.title || 'api').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    var sec = oas && ((oas.components && oas.components.securitySchemes) || oas.securityDefinitions);
    if (sec && Object.keys(sec).length) notes.push('The API declares security schemes (' + Object.keys(sec).join(', ') + '), so it is probably not open. Choose the access rights and give a rights statement.');
    notes.push('Add the publisher, access rights, security classification and service status: an OpenAPI description does not hold them.');
    return { record: rec, notes: notes };
  }

  // ---- exports ------------------------------------------------------------------------------------------------
  var LANG2 = { ENG: 'en', CYM: 'cy', GLA: 'gd', GLE: 'ga', SCO: 'sco', COR: 'kw' };
  function first(v) { return asList(v)[0]; }
  function agentLD(P, a) {
    if (a && typeof a === 'object') return { '@type': 'Organization', name: first(a.name), identifier: a.identifier };
    return a ? { '@id': expand(P, a) } : undefined;
  }
  function period(v) {
    var t = first(v); if (!t || typeof t !== 'object') return undefined;
    return (t.startDate || '..') + '/' + (t.endDate || '..');
  }
  function clean(o) { Object.keys(o).forEach(function (k) { if (o[k] === undefined || (Array.isArray(o[k]) && !o[k].length)) delete o[k]; }); return o; }
  function mediaShort(P, v) { return v ? expand(P, v).replace(IANA, '') : undefined; }

  // schema.org JSON-LD, for search engines and for AI crawlers that read schema.org. A DataService becomes a WebAPI.
  function toSchemaOrg(P, rec) {
    var service = rec['class'] === 'DataService';
    var o = { '@context': 'https://schema.org/', '@type': service ? 'WebAPI' : 'Dataset', '@id': rec.id, name: first(rec.title), description: first(rec.description),
      abstract: rec.abstract, identifier: rec.identifier, url: first(rec.landingPage) || rec.id, license: rec.licence ? expand(P, first(rec.licence)) : undefined,
      isAccessibleForFree: rec.accessRights ? /\/open$/.test(expand(P, first(rec.accessRights))) : undefined, keywords: asList(rec.keyword),
      temporalCoverage: period(rec.temporal), spatialCoverage: asList(rec.spatial).map(function (s) { return typeof s === 'string' ? { '@id': expand(P, s) } : undefined; }).filter(Boolean),
      datePublished: rec.issued, dateModified: rec.modified, dateCreated: rec.created, version: rec.version,
      inLanguage: asList(rec.language).map(function (l) { var c = expand(P, l).split('/').pop(); return LANG2[c] || c.toLowerCase(); }),
      publisher: agentLD(P, rec.publisher), creator: asList(rec.creator).map(function (a) { return agentLD(P, a); }),
      conditionsOfAccess: first(rec.rights), usageInfo: asList(rec.hasPolicy).map(function (x) { return expand(P, x); })[0],
      documentation: service ? first(rec.endpointDescription) : undefined };
    if (!service) o.distribution = asList(rec.distribution).filter(function (d) { return d && typeof d === 'object'; }).map(function (d) {
      return clean({ '@type': 'DataDownload', name: first(d.title), contentUrl: first(d.downloadURL) || first(d.accessURL), encodingFormat: mediaShort(P, d.mediaType), contentSize: d.byteSize });
    });
    return clean(o);
  }

  // Croissant 1.1, dataset level only: the record sets (columns and types) must be added with Croissant tools. Provenance K.
  function toCroissant(P, rec) {
    var o = toSchemaOrg(P, rec);
    o['@context'] = { '@language': 'en', '@vocab': 'https://schema.org/', sc: 'https://schema.org/', cr: 'http://mlcommons.org/croissant/',
      rai: 'http://mlcommons.org/croissant/RAI/', dct: 'http://purl.org/dc/terms/' };
    o['@type'] = 'sc:Dataset';
    o['dct:conformsTo'] = 'http://mlcommons.org/croissant/1.1';
    o.distribution = asList(rec.distribution).filter(function (d) { return d && typeof d === 'object'; }).map(function (d, i) {
      var ck = d.checksum && (Array.isArray(d.checksum) ? d.checksum[0] : d.checksum);
      var sha = ck && /sha256$/.test(expand(P, ck.algorithm || '')) ? ck.checksumValue : undefined;
      return clean({ '@type': 'cr:FileObject', '@id': d.id || 'file-' + (i + 1), name: first(d.title) || 'file-' + (i + 1),
        contentUrl: first(d.downloadURL) || first(d.accessURL), encodingFormat: mediaShort(P, d.mediaType), contentSize: d.byteSize, sha256: sha });
    });
    if (rec.dataCard) o['rai:dataCollection'] = 'See the data card: ' + first(rec.dataCard);
    return clean(o);
  }

  // Turtle, for the record builder and the bulk converter.
  function toTurtle(P, rec) {
    var used = {};
    function iri(s) { var e = expand(P, s); return '<' + e.replace(/[<>"{}|^`\\\s]/g, encodeURIComponent) + '>'; }
    function lit(s) { return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n') + '"'; }
    function curie(c) { used[String(c).split(':')[0]] = 1; return c; }
    function val(prop, v, ind) {
      if (prop.kind === 'object' && v && typeof v === 'object') return node(v, prop.range, ind + '    ');
      if (/iri|url|concept|object|email/.test(prop.kind)) return iri(prop.kind === 'email' && !/^mailto:/.test(v) ? 'mailto:' + v : v);
      used.xsd = 1;
      if (prop.kind === 'date') return lit(v) + '^^xsd:' + (/T/.test(v) ? 'dateTime' : /^\d{4}-\d{2}-\d{2}$/.test(v) ? 'date' : /^\d{4}-\d{2}$/.test(v) ? 'gYearMonth' : 'gYear');
      if (prop.kind === 'integer') return lit(v) + '^^xsd:nonNegativeInteger';
      if (prop.kind === 'boolean') return lit(v) + '^^xsd:boolean';
      if (prop.kind === 'decimal') return lit(v) + '^^xsd:decimal';
      return lit(v);
    }
    function body(r, ck, ind) {
      var C = P.classes[ck] || P.classes.Dataset;
      var lines = ['a ' + curie(C.uri)];
      Object.keys(r).forEach(function (k) {
        if (k === 'class' || k === 'id' || !P.props[k]) return;
        var vs = Array.isArray(r[k]) ? r[k] : [r[k]];
        lines.push(curie(P.props[k].uri) + ' ' + vs.map(function (v) { return val(P.props[k], v, ind); }).join(', '));
      });
      return lines.join(' ;\n' + ind);
    }
    var later = [];
    // A nested node with its own address is written as its own statement, so none of its properties are lost (D-015).
    function node(r, rng, ind) {
      var ck = r['class'] || rng;
      if (r.id) { later.push(iri(r.id) + '\n    ' + body(r, ck, '    ') + ' .\n'); return iri(r.id); }
      return '[\n' + ind + body(r, ck, ind) + '\n' + ind.slice(4) + ']';
    }
    var main = (rec.id ? iri(rec.id) : '[]') + '\n    ' + body(rec, rec['class'], '    ') + ' .\n';
    for (var li = 0; li < later.length; li++) main += '\n' + later[li];
    var head = Object.keys(used).filter(function (p) { return P.prefixes[p]; }).sort().map(function (p) { return '@prefix ' + p + ': <' + P.prefixes[p] + '> .'; }).join('\n');
    return head + '\n\n' + main;
  }

  return { validate: validate, completeness: completeness, fromMem: fromMem, expand: expand, withExtensions: withExtensions, fair: fair,
    conformance: conformance, parseCSV: parseCSV, fromCSV: fromCSV, fromOpenAPI: fromOpenAPI, toSchemaOrg: toSchemaOrg, toCroissant: toCroissant, toTurtle: toTurtle };
}));
