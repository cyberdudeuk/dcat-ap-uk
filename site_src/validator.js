/* DCAT-AP-UK record validator. Runs in the browser (record builder, validator page) and in Node (tests).
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
    // properties the record explains as missing, with a reason (see Q-02 below)
    var explained = {};
    asList(rec.missingValue).forEach(function (mv) {
      if (!mv || typeof mv !== 'object' || !mv.missingProperty || !present(mv.missingReason)) return;
      var full = expand(P, String(mv.missingProperty));
      Object.keys(P.props).forEach(function (k) { if (expand(P, P.props[k].uri) === full || k === String(mv.missingProperty)) explained[k] = 1; });
    });
    C.props.forEach(function (x) {
      known[x.p] = 1;
      var prop = P.props[x.p];
      var vals = asList(rec[x.p]);
      var has = present(rec[x.p]);
      var ob = (cda && x.cda) ? x.cda : x.ob;
      if (!has) {
        if (ob === 'M') add('error', x.p, cda && x.cda === 'M' && x.ob !== 'M' ? 'R-04' : 'M-01',
          (cda && x.cda === 'M' && x.ob !== 'M' ? 'Critical data assets must give ' : 'Give ') + prop.label.toLowerCase() + '.');
        else if (ob === 'R' && !explained[x.p]) add('warning', x.p, 'R-00', 'Recommended: ' + prop.label.toLowerCase() + '.');
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
    // Q-02: a missing-value statement explains an empty recommended or optional property. It never stands in for a mandatory one,
    // and it must not contradict a value the record gives.
    if (present(rec.missingValue)) {
      asList(rec.missingValue).forEach(function (mv, i) {
        if (!mv || typeof mv !== 'object' || !mv.missingProperty) return;
        var name = String(mv.missingProperty), full = expand(P, name);
        var key = Object.keys(P.props).filter(function (k) { var u = P.props[k].uri; return u === name || expand(P, u) === full || k === name; })[0];
        var where = 'missingValue' + (asList(rec.missingValue).length > 1 ? '[' + i + ']' : '') + '.missingProperty';
        var slot = key && C.props.filter(function (x) { return x.p === key; })[0];
        if (!slot) { add('warning', where, 'Q-02', name + ' is not a property of ' + C.label.toLowerCase() + ', so it cannot be missing from it.'); return; }
        var ob = (cda && slot.cda) ? slot.cda : slot.ob;
        if (ob === 'M') add('warning', where, 'Q-02', P.props[key].label + ' is mandatory: give a value. Saying why it is missing does not satisfy it.');
        if (present(rec[key])) add('warning', where, 'Q-02', 'The record says ' + P.props[key].label.toLowerCase() + ' is missing, but gives a value for it.');
      });
    }
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

  // Convert a record from the xGov MEM YAML/JSON form to DCAT-AP-UK, using the crosswalk. Returns {record, notes}.
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
        ['conforms', 'Conforms to DCAT-AP-UK', 30, res.ok]] : [
        ['format', 'Format', 20, anyVal('format') || anyVal('mediaType')],
        ['mediaType', 'Media type', 10, anyVal('mediaType')],
        ['mediaTypeIana', 'Media type from the IANA list', 10, anyVal('mediaType', function (v) { return expand(P, v).indexOf(IANA) === 0; })],
        ['open', 'Non-proprietary format', 20, anyVal('mediaType', function (v) { return OPEN_TYPES.test(expand(P, v)); })],
        ['machine', 'Machine-readable format', 20, anyVal('mediaType', function (v) { return MACHINE_TYPES.test(expand(P, v)); })],
        ['conforms', 'Conforms to DCAT-AP-UK', 30, res.ok]] },
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


  // ---- metadata weaver: other models in and out, with DCAT-AP-UK in the middle ---------------------------------
  // Each reader returns {record, notes, map}; map is a list of [their field, DCAT-AP-UK property or null] threads.
  // Each writer returns {out, map}. Mappings follow profile/crosswalks.yaml (provenance K). Email addresses are never carried.
  var EMAIL_RX = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
  var FREQ_ISO = { 'R/PT1S': 'CONT', 'R/PT1H': 'HOURLY', 'R/P1D': 'DAILY', 'R/P1W': 'WEEKLY', 'R/P2W': 'BIWEEKLY', 'R/P0.5M': 'MONTHLY_2', 'R/P1M': 'MONTHLY',
    'R/P2M': 'BIMONTHLY', 'R/P3M': 'QUARTERLY', 'R/P4M': 'ANNUAL_3', 'R/P6M': 'ANNUAL_2', 'R/P1Y': 'ANNUAL', 'R/P2Y': 'BIENNIAL', 'R/P3Y': 'TRIENNIAL', 'irregular': 'IRREG' };
  var LANG3 = { en: 'ENG', cy: 'CYM', gd: 'GLA', ga: 'GLE', sco: 'SCO', kw: 'COR', eng: 'ENG', cym: 'CYM', wel: 'CYM' };
  var LIC = { 'uk-ogl': 'ogl-3', 'ogl-uk-3.0': 'ogl-3', 'ogl': 'ogl-3', 'cc-by': 'cc-by-4', 'cc-by-4.0': 'cc-by-4', 'cc-zero': 'cc0', 'cc0-1.0': 'cc0', 'cc0': 'cc0' };
  function freqFrom(P, v) {
    if (!v) return undefined;
    var s = String(v).trim(), c = FREQ_ISO[s] || s.toUpperCase().replace(/[^A-Z_0-9]/g, '_');
    var hit = P.codelists.frequency.concepts.filter(function (x) { return x.code === c; })[0];
    return hit ? hit.compact : undefined;
  }
  function langFrom(P, v) {
    return asList(v).map(function (l) { var c = LANG3[String(l).toLowerCase().slice(0, 3)] || LANG3[String(l).toLowerCase().slice(0, 2)] || String(l).toUpperCase(); return P.codelists.language.concepts.filter(function (x) { return x.code === c; }).map(function (x) { return x.compact; })[0]; }).filter(Boolean);
  }
  function licFrom(P, v) {
    if (!v) return undefined;
    var s = String(v).trim(), code = LIC[s.toLowerCase()];
    var cs = P.codelists.licences.concepts;
    var byIri = cs.filter(function (c) { return c.iri === s || c.iri.replace(/^https?:/, '') === s.replace(/^https?:/, ''); })[0];
    if (byIri) return byIri.iri;
    if (code) { var c = cs.filter(function (x) { return x.code === code; })[0]; if (c) return c.iri; }
    return URL_RE.test(s) ? s : undefined;
  }
  function agentFrom(v) {
    if (!v) return undefined;
    if (typeof v === 'string') return URL_RE.test(v) ? v : { 'class': 'Agent', name: v };
    var id = v['@id'] || v.url || v.uri;
    if (id && URL_RE.test(id)) return id;
    var n = v.name || v.title || v.fn;
    return n ? { 'class': 'Agent', name: first(n) } : undefined;
  }
  function contactFrom(v, notes) {
    var c = Array.isArray(v) ? v[0] : v;
    if (!c) return undefined;
    var o = {}, url = c.hasURL || c.url || c.contactUrl || c.contact_uri;
    if (c.fn || c.name) o.fn = c.fn || c.name; else notes.push('The contact has no team name. Add one; a name was not made up (RQ-22).');
    if (c.hasEmail || c.email || EMAIL_RX.test(JSON.stringify(c))) notes.push('A contact email address was not carried. Give a contact form address instead.');
    if (url && URL_RE.test(url) && !/^mailto:/.test(url)) o.hasURL = url;
    return o.hasURL ? [o] : (notes.push('No contact form address was found. Add one.'), undefined);
  }
  function periodFrom(start, end) {
    var o = {}; if (start) o.startDate = String(start).slice(0, 10); if (end) o.endDate = String(end).slice(0, 10);
    return (o.startDate || o.endDate) ? [o] : undefined;
  }
  function mediaFrom(v) {
    if (!v) return undefined;
    var s = String(v).trim();
    if (/^https?:/.test(s)) return s;
    return /\//.test(s) ? IANA + s.toLowerCase() : undefined;
  }
  function put(rec, map, src, k, v) { if (v === undefined || v === null || (Array.isArray(v) && !v.length) || v === '') { map.push([src, null]); return; } rec[k] = v; map.push([src, k]); }
  function finishRec(rec, notes) {
    var s = JSON.stringify(rec);
    if (EMAIL_RX.test(s)) { notes.push('An email address in the source was removed.'); rec = JSON.parse(s.replace(new RegExp(EMAIL_RX.source, 'g'), '')); }
    return rec;
  }

  // Apache Atlas entity model, as used by Microsoft Purview's data map (RQ-21). Built from Atlas's published v2 entity model;
  // nothing is invented: a value the entity does not hold stays missing, with a note saying where to get it.
  var ATLAS_THEME = { 'microsoft.government': 'government', 'government': 'government', 'transport': 'transport', 'environment': 'environment',
    'health': 'health', 'education': 'education', 'crime and justice': 'crime-and-justice', 'defence': 'defence', 'mapping': 'mapping',
    'business and economy': 'business-and-economy', 'microsoft.financial': 'business-and-economy', 'government spending': 'government-spending', 'society': 'society',
    'towns and cities': 'towns-and-cities' };
  function epochDate(v) {
    if (v === undefined || v === null || v === '') return undefined;
    var n = Number(v);
    if (isFinite(n) && n > 0) return new Date(n).toISOString().slice(0, 10);
    return DATE.test(String(v).slice(0, 10)) ? String(v).slice(0, 10) : undefined;
  }
  function classificationFrom(P, label, notes) {
    if (!label) { notes.push('No sensitivity label: give the security classification. It is not assumed to be OFFICIAL.'); return undefined; }
    var k = String(label).toUpperCase().replace(/[^A-Z]+/g, ' ').trim();
    if (k === 'OFFICIAL') return 'ukcl:security-classification/official';
    if (k === 'OFFICIAL SENSITIVE') return 'ukcl:security-classification/official-sensitive';
    if (k === 'SECRET' || k === 'TOP SECRET' || k === 'HIGHLY CONFIDENTIAL') { notes.push('The label "' + label + '" suggests data above OFFICIAL. Records about SECRET or TOP SECRET data do not belong in an OFFICIAL catalogue: check before publishing.'); return undefined; }
    notes.push('The label "' + label + '" is not a Government Security Classification. Map it with your information assurance team; it was not guessed.');
    return undefined;
  }

  var READERS = {
    ukap: function (P, x) { return { record: x, notes: [], map: Object.keys(x).filter(function (k) { return k !== 'class'; }).map(function (k) { return [k, P.props[k] || k === 'id' ? k : null]; }) }; },
    mem: function (P, x) {
      var c = fromMem(P, x), map = [];
      Object.keys(x).forEach(function (k) {
        var hit = Object.keys(P.props).filter(function (p) { return P.props[p].mem_slot === k; })[0];
        map.push([k, hit && c.record[hit] !== undefined ? hit : (c.record[k] !== undefined ? k : null)]);
      });
      return { record: c.record, notes: c.notes, map: map };
    },
    ckan: function (P, x) {
      var rec = { 'class': 'Dataset' }, notes = [], map = [], ex = {};
      (x.extras || []).forEach(function (e) { if (e && e.key) ex[e.key] = e.value; });
      put(rec, map, 'title', 'title', x.title);
      put(rec, map, 'notes', 'description', x.notes);
      put(rec, map, 'tags', 'keyword', (x.tags || []).map(function (t) { return t && (t.display_name || t.name); }).filter(Boolean));
      put(rec, map, 'license_id', 'licence', licFrom(P, x.license_url || x.license_id));
      put(rec, map, 'url', 'landingPage', x.url && URL_RE.test(x.url) ? [x.url] : undefined);
      put(rec, map, 'version', 'version', x.version);
      put(rec, map, 'organization', 'publisher', agentFrom(ex.publisher_uri || x.organization));
      put(rec, map, 'extras.identifier', 'identifier', ex.identifier || x.name);
      put(rec, map, 'extras.issued', 'issued', ex.issued || (x.metadata_created || '').slice(0, 10) || undefined);
      put(rec, map, 'extras.modified', 'modified', ex.modified || (x.metadata_modified || '').slice(0, 10) || undefined);
      put(rec, map, 'extras.frequency', 'accrualPeriodicity', freqFrom(P, ex.frequency));
      put(rec, map, 'extras.spatial_uri', 'spatial', ex.spatial_uri ? [ex.spatial_uri] : undefined);
      put(rec, map, 'extras.temporal_start', 'temporal', periodFrom(ex.temporal_start, ex.temporal_end));
      put(rec, map, 'extras.language', 'language', langFrom(P, ex.language));
      put(rec, map, 'extras.conforms_to', 'conformsTo', ex.conforms_to ? [ex.conforms_to] : undefined);
      put(rec, map, 'extras.contact_uri', 'contactPoint', contactFrom({ name: ex.contact_name, url: ex.contact_uri }, notes));
      if (x.maintainer || x.author) notes.push('The maintainer and author names were not carried: records name teams and roles, not people.');
      if (x.id) rec.id = x.url && URL_RE.test(x.url) ? x.url : undefined;
      var res = (x.resources || []).map(function (r) {
        var d = { 'class': 'Distribution' }, a = r.access_url || r.url, dl = r.download_url || (r.url && !r.access_url ? r.url : undefined);
        if (r.name) d.title = r.name; if (a) d.accessURL = [a]; if (dl) d.downloadURL = [dl];
        var mt = mediaFrom(r.mimetype); if (mt) d.mediaType = mt;
        if (r.size) d.byteSize = String(r.size);
        return d;
      });
      put(rec, map, 'resources', 'distribution', res);
      notes.push('Add access rights and security classification: CKAN does not hold them by default.');
      Object.keys(x).forEach(function (k) { if (['title', 'notes', 'tags', 'license_id', 'license_url', 'url', 'version', 'organization', 'extras', 'resources', 'name', 'id', 'metadata_created', 'metadata_modified', 'maintainer', 'author'].indexOf(k) < 0) map.push([k, null]); });
      return { record: finishRec(rec, notes), notes: notes, map: map };
    },
    atlas: function (P, x) {
      var e = (x && x.entity) || (x && x.entities && x.entities[0]) || x || {}, a = e.attributes || {}, notes = [], map = [];
      var svc = /api|service|endpoint/i.test(e.typeName || '');
      var rec = { 'class': svc ? 'DataService' : 'Dataset' };
      map.push(['typeName', null]);
      if (e.typeName) notes.push('The Atlas type ' + e.typeName + ' became a ' + (svc ? 'data service' : 'dataset') + '. Check that is right.');
      put(rec, map, 'attributes.name', 'title', a.name);
      put(rec, map, 'attributes.description', 'description', a.description || a.userDescription);
      if (!a.description && !a.userDescription) notes.push('No description in the source. Write one: a placeholder description is not given.');
      put(rec, map, 'guid', 'identifier', e.guid);
      if (e.guid) notes.push('The Atlas GUID is kept as the identifier. Give the record a persistent web identifier (an https address) as its id.');
      put(rec, map, 'attributes.createTime', 'issued', epochDate(a.createTime || e.createTime));
      put(rec, map, 'attributes.updateTime', 'modified', epochDate(a.updateTime || e.updateTime));
      put(rec, map, 'labels', 'keyword', asList(e.labels).filter(Boolean));
      var themes = [], unmapped = [];
      asList(e.classifications).forEach(function (c) {
        var n = String((c && c.typeName) || c || ''), key = n.toLowerCase().replace(/^custom:\s*/, '');
        if (/personal/i.test(n)) { notes.push('The classification ' + n + ' suggests personal data. Answer personal data; it was not set for you.'); return; }
        var hit = ATLAS_THEME[key] || ATLAS_THEME[key.split('.').slice(0, 2).join('.')];
        if (hit) themes.push('ukcl:theme/' + hit); else if (n) unmapped.push(n);
      });
      if (unmapped.length) notes.push('Not mapped to a theme: ' + unmapped.join(', ') + '. Add them to your mapping, or choose themes by hand.');
      put(rec, map, 'classifications', 'theme', themes.filter(function (t, i) { return themes.indexOf(t) === i; }));
      put(rec, map, 'sensitivityLabel', 'securityClassification', classificationFrom(P, e.sensitivityLabel || a.sensitivityLabel || (e.label && e.label.name), notes));
      notes.push('Access rights are not taken from the sensitivity label: who may have the data is a separate decision. Add them.');
      ['owner', 'experts', 'expert', 'stewards', 'steward', 'createdBy', 'contacts'].forEach(function (k) {
        if (a[k] || e[k] || (k === 'createdBy' && e.createdBy)) { map.push([k, null]); notes.push('The ' + k + ' field names people, so it was not carried. Give a publisher organisation and a team contact form.'); }
      });
      var qn = a.qualifiedName;
      if (qn && URL_RE.test(qn)) {
        var d = { 'class': 'Distribution', accessURL: [qn] }, mt = mediaFrom(a.mimeType || a.contentType);
        if (mt) d.mediaType = mt;
        if (a.size !== undefined && /^\d+$/.test(String(a.size))) d.byteSize = String(a.size);
        if (svc) put(rec, map, 'attributes.qualifiedName', 'endpointURL', [qn]); else put(rec, map, 'attributes.qualifiedName', 'distribution', [d]);
      } else if (qn) { map.push(['attributes.qualifiedName', null]); notes.push('The qualified name ' + qn + ' is not a web address, so no access address was made from it. Give one by hand.'); }
      if (String(e.status || '').toUpperCase() === 'DELETED') notes.push('The entity is deleted in the source. Do not publish it.');
      notes.push('Atlas does not hold publisher, update frequency, licence, temporal or spatial coverage. Add them, or say why they are missing.');
      Object.keys(a).forEach(function (k) { if (['name', 'description', 'userDescription', 'createTime', 'updateTime', 'qualifiedName', 'mimeType', 'contentType', 'size', 'sensitivityLabel', 'owner', 'experts', 'expert', 'stewards', 'steward', 'contacts'].indexOf(k) < 0) map.push(['attributes.' + k, null]); });
      return { record: finishRec(rec, notes), notes: notes, map: map };
    },
    dcatus: function (P, x) {
      var rec = { 'class': 'Dataset' }, notes = [], map = [];
      put(rec, map, 'title', 'title', x.title);
      put(rec, map, 'description', 'description', x.description);
      put(rec, map, 'keyword', 'keyword', asList(x.keyword));
      put(rec, map, 'modified', 'modified', x.modified && String(x.modified).slice(0, 10));
      put(rec, map, 'issued', 'issued', x.issued && String(x.issued).slice(0, 10));
      put(rec, map, 'publisher', 'publisher', agentFrom(x.publisher));
      put(rec, map, 'contactPoint', 'contactPoint', contactFrom(x.contactPoint, notes));
      put(rec, map, 'identifier', 'identifier', x.identifier);
      var al = String(x.accessLevel || '').toLowerCase();
      put(rec, map, 'accessLevel', 'accessRights', al === 'public' ? 'ukcl:access-rights/open' : al ? 'ukcl:access-rights/internal' : undefined);
      if (al && al !== 'public') notes.push('Access level "' + al + '" was read as internal; check it, and give a rights statement.');
      put(rec, map, 'license', 'licence', licFrom(P, x.license));
      put(rec, map, 'rights', 'rights', x.rights);
      put(rec, map, 'spatial', 'spatial', x.spatial && URL_RE.test(x.spatial) ? [x.spatial] : undefined);
      var t = String(x.temporal || '').split('/');
      put(rec, map, 'temporal', 'temporal', x.temporal ? periodFrom(t[0], t[1]) : undefined);
      put(rec, map, 'accrualPeriodicity', 'accrualPeriodicity', freqFrom(P, x.accrualPeriodicity));
      put(rec, map, 'landingPage', 'landingPage', x.landingPage ? [x.landingPage] : undefined);
      put(rec, map, 'language', 'language', langFrom(P, x.language));
      put(rec, map, 'conformsTo', 'conformsTo', x.conformsTo ? asList(x.conformsTo) : undefined);
      put(rec, map, 'distribution', 'distribution', asList(x.distribution).map(function (r) {
        var d = { 'class': 'Distribution' }; if (r.title) d.title = r.title; if (r.accessURL) d.accessURL = [r.accessURL]; if (r.downloadURL) d.downloadURL = [r.downloadURL];
        if (!d.accessURL && d.downloadURL) d.accessURL = d.downloadURL; var mt = mediaFrom(r.mediaType); if (mt) d.mediaType = mt; return d;
      }));
      if (x.theme) map.push(['theme', null]), notes.push('Themes were not carried: map them to the data.gov.uk themes.');
      notes.push('Add the security classification: DCAT-US does not hold it.');
      return { record: finishRec(rec, notes), notes: notes, map: map };
    },
    schemaorg: function (P, x) {
      var rec = { 'class': /WebAPI/.test(x['@type'] || '') ? 'DataService' : 'Dataset' }, notes = [], map = [];
      if (x['@id'] && URL_RE.test(x['@id'])) rec.id = x['@id'];
      put(rec, map, 'name', 'title', first(x.name));
      put(rec, map, 'description', 'description', first(x.description));
      put(rec, map, 'keywords', 'keyword', typeof x.keywords === 'string' ? x.keywords.split(/\s*,\s*/) : asList(x.keywords));
      put(rec, map, 'license', 'licence', licFrom(P, typeof x.license === 'object' ? x.license.url || x.license['@id'] : x.license));
      put(rec, map, 'url', 'landingPage', x.url ? [x.url] : undefined);
      put(rec, map, 'identifier', 'identifier', typeof x.identifier === 'object' ? x.identifier.value : x.identifier);
      put(rec, map, 'datePublished', 'issued', x.datePublished && String(x.datePublished).slice(0, 10));
      put(rec, map, 'dateModified', 'modified', x.dateModified && String(x.dateModified).slice(0, 10));
      var tc = String(x.temporalCoverage || '').split('/');
      put(rec, map, 'temporalCoverage', 'temporal', x.temporalCoverage ? periodFrom(tc[0] !== '..' ? tc[0] : '', tc[1] !== '..' ? tc[1] : '') : undefined);
      put(rec, map, 'spatialCoverage', 'spatial', asList(x.spatialCoverage).map(function (s) { return typeof s === 'string' ? s : s && (s['@id'] || s.url); }).filter(function (s) { return s && URL_RE.test(s); }));
      put(rec, map, 'publisher', 'publisher', agentFrom(x.publisher));
      put(rec, map, 'inLanguage', 'language', langFrom(P, x.inLanguage));
      put(rec, map, 'version', 'version', x.version !== undefined ? String(x.version) : undefined);
      put(rec, map, 'conditionsOfAccess', 'rights', x.conditionsOfAccess);
      put(rec, map, 'isAccessibleForFree', 'accessRights', x.isAccessibleForFree === true ? 'ukcl:access-rights/open' : undefined);
      put(rec, map, 'distribution', 'distribution', asList(x.distribution).map(function (r) {
        var d = { 'class': 'Distribution' }, u = r.contentUrl || r.url; if (r.name) d.title = first(r.name); if (u) { d.accessURL = [u]; d.downloadURL = [u]; }
        var mt = mediaFrom(r.encodingFormat); if (mt) d.mediaType = mt; if (r.contentSize) d.byteSize = String(r.contentSize).replace(/\D/g, '') || undefined; return d;
      }));
      if (x.creator) map.push(['creator', null]), notes.push('Creators were not carried: give organisation addresses as creators if needed.');
      notes.push('Add the contact point, security classification and frequency: schema.org records rarely hold them.');
      return { record: finishRec(rec, notes), notes: notes, map: map };
    },
    dc: function (P, x) {
      var rec = { 'class': 'Dataset' }, notes = [], map = [];
      function g(k) { return x[k] !== undefined ? x[k] : x['dc:' + k] !== undefined ? x['dc:' + k] : x['dc.' + k]; }
      function srcName(k) { return x[k] !== undefined ? k : x['dc:' + k] !== undefined ? 'dc:' + k : 'dc.' + k; }
      var seen = {};
      function take(k, dst, v) { seen[srcName(k)] = 1; if (g(k) === undefined) return; put(rec, map, srcName(k), dst, v); }
      take('title', 'title', first(g('title')));
      take('description', 'description', first(g('description')));
      take('subject', 'keyword', asList(g('subject')));
      take('publisher', 'publisher', agentFrom(first(g('publisher'))));
      take('creator', 'creator', asList(g('creator')).map(agentFrom).filter(function (a) { return typeof a === 'string'; }));
      take('identifier', 'identifier', first(g('identifier')));
      take('language', 'language', langFrom(P, g('language')));
      take('rights', 'rights', first(g('rights')));
      take('date', 'issued', g('date') && String(first(g('date'))).slice(0, 10));
      take('format', 'mediaType', undefined);
      take('coverage', 'spatial', asList(g('coverage')).filter(function (s) { return URL_RE.test(s); }));
      take('relation', 'relation', undefined);
      take('source', 'relation', undefined);
      take('type', 'class', undefined);
      take('contributor', 'qualifiedAttribution', undefined);
      Object.keys(x).forEach(function (k) { if (!seen[k]) map.push([k, null]); });
      notes.push('Dublin Core has no contact point, access rights, security classification, licence or frequency: add them.');
      if (g('format')) notes.push('Format belongs on a distribution: add one with the media type.');
      return { record: finishRec(rec, notes), notes: notes, map: map };
    },
    ddi: function (P, x) {
      var rec = { 'class': 'Dataset' }, notes = [], map = [];
      put(rec, map, 'titl', 'title', first(x.titl));
      put(rec, map, 'IDNo', 'identifier', first(x.IDNo));
      put(rec, map, 'abstract', 'description', first(x.abstract));
      put(rec, map, 'keyword', 'keyword', asList(x.keyword));
      put(rec, map, 'producer', 'publisher', agentFrom(first(x.producer)));
      put(rec, map, 'AuthEnty', 'creator', undefined);
      var tp = x.timePrd || {};
      put(rec, map, 'timePrd', 'temporal', periodFrom(tp.start || (Array.isArray(tp) ? tp[0] : ''), tp.end || (Array.isArray(tp) ? tp[1] : '')));
      put(rec, map, 'geogCover', 'spatial', asList(x.geogCover).filter(function (s) { return URL_RE.test(s); }));
      put(rec, map, 'restrctn', 'rights', first(x.restrctn) || first(x.conditions));
      put(rec, map, 'accsPlac', 'landingPage', x.accsPlac && URL_RE.test(first(x.accsPlac)) ? [first(x.accsPlac)] : undefined);
      put(rec, map, 'version', 'version', first(x.version));
      put(rec, map, 'prodDate', 'created', x.prodDate && String(first(x.prodDate)).slice(0, 10));
      put(rec, map, 'distDate', 'issued', x.distDate && String(first(x.distDate)).slice(0, 10));
      ['nation', 'universe', 'topcClas', 'distrbtr', 'contact', 'conditions'].forEach(function (k) { if (x[k] !== undefined) map.push([k, null]); });
      if (x.universe) notes.push('The universe was not carried; with the health extension it becomes population covered.');
      if (x.contact) notes.push('DDI contact details were not carried. Give a contact form address.');
      notes.push('Add access rights, security classification, licence and frequency.');
      return { record: finishRec(rec, notes), notes: notes, map: map };
    }
  };

  var WRITERS = {
    ukap: function (P, r) { return { out: r, map: Object.keys(r).filter(function (k) { return k !== 'class'; }).map(function (k) { return [k, k]; }) }; },
    jsonld: function (P, r) { return { out: Object.assign({ '@context': 'https://cyberdudeuk.github.io/dcat-ap-uk/downloads/dcat-ap-uk.context.jsonld' }, r), map: Object.keys(r).filter(function (k) { return k !== 'class'; }).map(function (k) { return [k, k]; }) }; },
    turtle: function (P, r) { return { out: toTurtle(P, r), map: Object.keys(r).filter(function (k) { return P.props[k]; }).map(function (k) { return [k, P.props[k].uri]; }) }; },
    schemaorg: function (P, r) { return { out: toSchemaOrg(P, r), map: SDO_MAP(r) }; },
    croissant: function (P, r) { return { out: toCroissant(P, r), map: SDO_MAP(r) }; },
    ckan: function (P, r) {
      var o = { title: first(r.title), notes: first(r.description), tags: asList(r.keyword).map(function (k) { return { name: String(k) }; }), url: first(r.landingPage), version: r.version,
        license_url: r.licence ? expand(P, first(r.licence)) : undefined, extras: [], resources: [] }, map = [['title', 'title'], ['description', 'notes'], ['keyword', 'tags'], ['landingPage', 'url'], ['version', 'version'], ['licence', 'license_url']];
      function ex(k, v, src) { if (v !== undefined && v !== null && v !== '') { o.extras.push({ key: k, value: String(v) }); map.push([src, 'extras.' + k]); } }
      ex('identifier', r.identifier, 'identifier'); ex('issued', r.issued, 'issued'); ex('modified', r.modified, 'modified');
      ex('frequency', r.accrualPeriodicity && expand(P, first(r.accrualPeriodicity)), 'accrualPeriodicity'); ex('access_rights', r.accessRights && expand(P, first(r.accessRights)), 'accessRights');
      ex('publisher_uri', typeof r.publisher === 'string' ? r.publisher : undefined, 'publisher');
      var cp = first(r.contactPoint); if (cp) { ex('contact_name', cp.fn, 'contactPoint'); ex('contact_uri', cp.hasURL, 'contactPoint'); }
      var t = first(r.temporal); if (t) { ex('temporal_start', t.startDate, 'temporal'); ex('temporal_end', t.endDate, 'temporal'); }
      ex('spatial_uri', first(r.spatial), 'spatial'); ex('security_classification', r.securityClassification && expand(P, first(r.securityClassification)), 'securityClassification');
      o.resources = asList(r.distribution).filter(function (d) { return d && typeof d === 'object'; }).map(function (d) { return clean({ name: first(d.title), url: first(d.downloadURL) || first(d.accessURL), access_url: first(d.accessURL), download_url: first(d.downloadURL), mimetype: mediaShort(P, d.mediaType), size: d.byteSize }); });
      if (o.resources.length) map.push(['distribution', 'resources']);
      return { out: clean(o), map: map };
    },
    dcatus: function (P, r) {
      var t = first(r.temporal), freq = r.accrualPeriodicity ? expand(P, first(r.accrualPeriodicity)).split('/').pop() : '';
      var iso = Object.keys(FREQ_ISO).filter(function (k) { return FREQ_ISO[k] === freq; })[0];
      var cp = first(r.contactPoint);
      var o = { '@type': 'dcat:Dataset', title: first(r.title), description: first(r.description), keyword: asList(r.keyword), modified: r.modified, issued: r.issued,
        publisher: typeof r.publisher === 'object' ? { name: first(r.publisher.name) } : r.publisher ? { '@id': r.publisher } : undefined,
        contactPoint: cp ? { fn: cp.fn, hasURL: cp.hasURL } : undefined, identifier: r.identifier,
        accessLevel: r.accessRights ? (/\/open$/.test(expand(P, first(r.accessRights))) ? 'public' : 'non-public') : undefined,
        license: r.licence ? expand(P, first(r.licence)) : undefined, rights: first(r.rights), spatial: first(r.spatial),
        temporal: t ? (t.startDate || '') + '/' + (t.endDate || '') : undefined, accrualPeriodicity: iso, landingPage: first(r.landingPage), conformsTo: first(r.conformsTo),
        distribution: asList(r.distribution).filter(function (d) { return d && typeof d === 'object'; }).map(function (d) { return clean({ '@type': 'dcat:Distribution', title: first(d.title), accessURL: first(d.accessURL), downloadURL: first(d.downloadURL), mediaType: mediaShort(P, d.mediaType) }); }) };
      var map = ['title', 'description', 'keyword', 'modified', 'issued', 'publisher', 'contactPoint', 'identifier', ['accessRights', 'accessLevel'], ['licence', 'license'], 'rights', 'spatial', 'temporal', 'accrualPeriodicity', 'landingPage', 'conformsTo', 'distribution']
        .filter(function (k) { return r[Array.isArray(k) ? k[0] : k] !== undefined; }).map(function (k) { return Array.isArray(k) ? k : [k, k]; });
      return { out: clean(o), map: map };
    },
    dc: function (P, r) {
      var o = { 'dc:title': first(r.title), 'dc:description': first(r.description), 'dc:subject': asList(r.keyword), 'dc:publisher': typeof r.publisher === 'object' ? first(r.publisher.name) : r.publisher,
        'dc:creator': asList(r.creator).map(function (a) { return typeof a === 'object' ? first(a.name) : a; }), 'dc:date': r.issued || r.modified, 'dc:type': r['class'] === 'DataService' ? 'Service' : 'Dataset',
        'dc:format': asList(r.distribution).map(function (d) { return d && mediaShort(P, d.mediaType); }).filter(Boolean), 'dc:identifier': r.identifier || r.id,
        'dc:language': asList(r.language).map(function (l) { return expand(P, l).split('/').pop(); }), 'dc:relation': asList(r.relation).map(function (x) { return typeof x === 'string' ? x : x && x.relation; }).filter(Boolean),
        'dc:coverage': asList(r.spatial).filter(function (s) { return typeof s === 'string'; }), 'dc:rights': first(r.rights) || (r.licence ? expand(P, first(r.licence)) : undefined) };
      var map = [['title', 'dc:title'], ['description', 'dc:description'], ['keyword', 'dc:subject'], ['publisher', 'dc:publisher'], ['creator', 'dc:creator'], ['issued', 'dc:date'], ['distribution', 'dc:format'], ['identifier', 'dc:identifier'], ['language', 'dc:language'], ['relation', 'dc:relation'], ['spatial', 'dc:coverage'], ['rights', 'dc:rights'], ['licence', 'dc:rights']]
        .filter(function (m) { return r[m[0]] !== undefined; });
      return { out: clean(o), map: map };
    },
    ddi: function (P, r) {
      var t = first(r.temporal) || {};
      var o = { titl: first(r.title), IDNo: r.identifier, abstract: first(r.description), keyword: asList(r.keyword), producer: typeof r.publisher === 'object' ? first(r.publisher.name) : r.publisher,
        timePrd: (t.startDate || t.endDate) ? clean({ start: t.startDate, end: t.endDate }) : undefined, geogCover: asList(r.spatial).filter(function (s) { return typeof s === 'string'; }),
        restrctn: first(r.rights), accsPlac: first(r.landingPage), version: r.version, prodDate: r.created, distDate: r.issued };
      var map = [['title', 'titl'], ['identifier', 'IDNo'], ['description', 'abstract'], ['keyword', 'keyword'], ['publisher', 'producer'], ['temporal', 'timePrd'], ['spatial', 'geogCover'], ['rights', 'restrctn'], ['landingPage', 'accsPlac'], ['version', 'version'], ['created', 'prodDate'], ['issued', 'distDate']]
        .filter(function (m) { return r[m[0]] !== undefined; });
      return { out: clean(o), map: map };
    }
  };
  function SDO_MAP(r) {
    var m = { title: 'name', description: 'description', abstract: 'abstract', identifier: 'identifier', landingPage: 'url', licence: 'license', accessRights: 'isAccessibleForFree', keyword: 'keywords',
      temporal: 'temporalCoverage', spatial: 'spatialCoverage', issued: 'datePublished', modified: 'dateModified', created: 'dateCreated', version: 'version', language: 'inLanguage', publisher: 'publisher',
      creator: 'creator', rights: 'conditionsOfAccess', hasPolicy: 'usageInfo', distribution: 'distribution' };
    return Object.keys(r).filter(function (k) { return m[k]; }).map(function (k) { return [k, m[k]]; });
  }

  // Read a record in one model and write it in another, checking it as DCAT-AP-UK on the way.
  function weave(P, from, to, input) {
    if (!READERS[from]) throw new Error('Unknown source model ' + from);
    if (!WRITERS[to]) throw new Error('Unknown target model ' + to);
    var a = READERS[from](P, input), b = WRITERS[to](P, a.record);
    return { record: a.record, out: b.out, mapIn: a.map, mapOut: b.map, notes: a.notes, validation: validate(P, a.record) };
  }

  return { weave: weave, readers: Object.keys(READERS), writers: Object.keys(WRITERS), validate: validate, completeness: completeness, fromMem: fromMem, expand: expand, withExtensions: withExtensions, fair: fair,
    conformance: conformance, parseCSV: parseCSV, fromCSV: fromCSV, fromOpenAPI: fromOpenAPI, toSchemaOrg: toSchemaOrg, toCroissant: toCroissant, toTurtle: toTurtle };
}));
