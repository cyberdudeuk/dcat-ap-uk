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

  return { validate: validate, completeness: completeness, fromMem: fromMem, expand: expand };
}));
