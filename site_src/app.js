/* DCAT-UK AP portal behaviour. No network requests, no third-party code, nothing stored except per-viewer display choices
   (inside try/catch with an in-memory fallback). Every page works without this script; it adds convenience. Licence: MIT. */
(function () {
  'use strict';
  var doc = document, root = doc.documentElement;
  var mem = {};
  var store = {
    get: function (k) { try { return window.localStorage.getItem('ukap:' + k); } catch (e) { return mem[k] || null; } },
    set: function (k, v) { try { window.localStorage.setItem('ukap:' + k, v); } catch (e) { mem[k] = v; } }
  };
  function $(s, c) { return (c || doc).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(tag, attrs, html) { var e = doc.createElement(tag); Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); }); if (html != null) e.innerHTML = html; return e; }
  function announce(msg) { var l = $('#live'); if (l) { l.textContent = ''; setTimeout(function () { l.textContent = msg; }, 50); } }

  /* ---- display options: theme, text size, spacing ------------------------------------------------------- */
  ['theme', 'size', 'spacing'].forEach(function (k) { var v = store.get(k); if (v) root.setAttribute('data-' + k, v); });
  var themeBtn = $('#theme');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var cur = root.getAttribute('data-theme') || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next); store.set('theme', next); announce(next === 'dark' ? 'Dark mode on' : 'Light mode on');
  });
  $$('[data-display]').forEach(function (s) {
    var k = s.getAttribute('data-display'); s.value = store.get(k) || s.value;
    s.addEventListener('change', function () { root.setAttribute('data-' + k, s.value); store.set(k, s.value); });
  });

  /* ---- drawer: in-page navigation, retractable, independent of the masthead ----------------------------- */
  var drawer = $('#drawer'), dt = $('#drawer-toggle');
  function setDrawer(open) {
    if (!drawer || !dt) return;
    drawer.hidden = !open; dt.setAttribute('aria-expanded', String(open));
    $('.tlabel', dt).textContent = open ? 'Hide page contents' : 'Show page contents';
    store.set('drawer', open ? '1' : '0');
  }
  if (drawer && dt) {
    var pref = store.get('drawer');
    setDrawer(pref === null ? window.innerWidth > 960 : pref === '1');
    dt.addEventListener('click', function () { setDrawer(drawer.hidden); });
  }

  /* ---- global bar: grouped menus, and folding before it would overflow --------------------------------- */
  var gbar = $('.gbar');
  function closeMenus(except) { $$('.gbar li.open').forEach(function (li) { if (li !== except) { li.classList.remove('open'); $('button', li).setAttribute('aria-expanded', 'false'); } }); }
  if (gbar) {
    gbar.addEventListener('click', function (e) {
      var b = e.target.closest('button[aria-expanded]'); if (!b) return;
      var li = b.parentNode, open = !li.classList.contains('open');
      closeMenus(li); li.classList.toggle('open', open); b.setAttribute('aria-expanded', String(open));
    });
    doc.addEventListener('click', function (e) { if (!e.target.closest('.gbar')) closeMenus(); });
    var top = $('ul.top', gbar), more = $('li.more', gbar), moreList = more && $('.sub', more);
    var originals = $$(':scope > li:not(.more)', top);
    gbar.classList.add('js-fold');
    var fold = function () {
      originals.forEach(function (li) { top.insertBefore(li, more); });
      gbar.classList.remove('folding');
      if (top.scrollWidth <= top.clientWidth + 1) return;
      gbar.classList.add('folding');
      var items = $$(':scope > li:not(.more)', top);
      for (var i = items.length - 1; i > 0 && top.scrollWidth > top.clientWidth + 1; i--) moreList.insertBefore(items[i], moreList.firstChild);
    };
    if (top && more) { fold(); window.addEventListener('resize', fold); }
  }

  /* ---- tabs: GOV.UK pattern, arrow keys, deep links, remembers the last tab ---------------------------- */
  $$('.tabs').forEach(function (box) {
    var tabs = $$('[role="tab"]', box), key = 'tab:' + (box.id || location.pathname);
    function show(t, focus) {
      tabs.forEach(function (x) { var on = x === t; x.setAttribute('aria-selected', String(on)); x.tabIndex = on ? 0 : -1; doc.getElementById(x.getAttribute('aria-controls')).hidden = !on; });
      if (focus) t.focus(); store.set(key, t.id);
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { show(t); });
      t.addEventListener('keydown', function (e) {
        var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : null;
        if (j === null) return; e.preventDefault(); show(tabs[(j + tabs.length) % tabs.length], true);
      });
    });
    var byHash = location.hash && tabs.filter(function (t) { return '#' + t.getAttribute('aria-controls') === location.hash; })[0];
    var saved = doc.getElementById(store.get(key) || '');
    show(byHash || (saved && tabs.indexOf(saved) > -1 ? saved : tabs[0]));
  });

  /* ---- tables: sort, filter, count, download what you see ------------------------------------------------ */
  $$('table[data-sortable]').forEach(function (t) {
    $$('thead th', t).forEach(function (th, ci) {
      var label = th.textContent; th.textContent = '';
      var b = el('button', { type: 'button', 'class': 'sort' }, esc(label) + ' <span aria-hidden="true">&#8693;</span>');
      th.appendChild(b); th.setAttribute('aria-sort', 'none');
      b.addEventListener('click', function () {
        var asc = th.getAttribute('aria-sort') !== 'ascending';
        $$('thead th', t).forEach(function (x) { x.setAttribute('aria-sort', 'none'); });
        th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
        var rows = $$('tbody tr', t);
        rows.sort(function (a, b) {
          var x = (a.cells[ci].getAttribute('data-sort') || a.cells[ci].textContent).trim(), y = (b.cells[ci].getAttribute('data-sort') || b.cells[ci].textContent).trim();
          var nx = parseFloat(x), ny = parseFloat(y);
          var r = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y, 'en-GB', { numeric: true });
          return asc ? r : -r;
        });
        rows.forEach(function (r) { r.parentNode.appendChild(r); });
        announce('Sorted by ' + label + (asc ? ', ascending' : ', descending'));
      });
    });
  });
  $$('.filters[data-for]').forEach(function (f) {
    var t = doc.getElementById(f.getAttribute('data-for')), out = $('output', f);
    var run = function () {
      var q = ($('input[type="search"]', f) || {}).value; q = (q || '').toLowerCase();
      var sels = $$('select[data-col]', f);
      var n = 0;
      $$('tbody tr', t).forEach(function (r) {
        var ok = !q || r.textContent.toLowerCase().indexOf(q) > -1;
        sels.forEach(function (s) { if (s.value && (r.getAttribute('data-' + s.getAttribute('data-col')) || '').split(' ').indexOf(s.value) < 0) ok = false; });
        r.hidden = !ok; if (ok) n++;
      });
      if (out) out.textContent = n + ' shown';
    };
    $$('input,select', f).forEach(function (i) { i.addEventListener(i.tagName === 'SELECT' ? 'change' : 'input', run); });
    run();
    var dl = $('button[data-csv]', f);
    if (dl) dl.addEventListener('click', function () {
      var rows = [$$('thead th', t).map(function (th) { return th.textContent.replace(/⇵/g, '').trim(); })];
      $$('tbody tr', t).forEach(function (r) { if (!r.hidden) rows.push($$('td,th', r).map(function (c) { return c.textContent.trim(); })); });
      var csv = rows.map(function (r) { return r.map(function (c) { return '"' + c.replace(/"/g, '""') + '"'; }).join(','); }).join('\n');
      download(dl.getAttribute('data-csv'), csv, 'text/csv');
    });
  });
  function download(name, text, type) {
    var a = el('a', { href: URL.createObjectURL(new Blob([text], { type: type + ';charset=utf-8' })), download: name });
    doc.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    announce('Downloaded ' + name);
  }

  /* ---- tooltips from the glossary and data-tip ----------------------------------------------------------- */
  var tip = null;
  function hideTip() { if (tip) { tip.remove(); tip = null; } }
  function showTip(t) {
    hideTip(); var text = t.getAttribute('data-tip'); if (!text) return;
    tip = el('div', { 'class': 'tip', role: 'tooltip', id: 'tip' }); tip.textContent = text; doc.body.appendChild(tip);
    var r = t.getBoundingClientRect(); var x = Math.min(window.scrollX + r.left, window.scrollX + doc.documentElement.clientWidth - tip.offsetWidth - 8);
    tip.style.left = Math.max(8, x) + 'px'; tip.style.top = (window.scrollY + r.bottom + 6) + 'px';
    t.setAttribute('aria-describedby', 'tip');
  }
  doc.addEventListener('mouseover', function (e) { var t = e.target.closest('[data-tip]'); if (t) showTip(t); });
  doc.addEventListener('mouseout', function (e) { if (e.target.closest('[data-tip]')) hideTip(); });
  doc.addEventListener('focusin', function (e) { var t = e.target.closest('[data-tip]'); if (t) showTip(t); else hideTip(); });

  /* ---- copy and share ------------------------------------------------------------------------------------ */
  doc.addEventListener('click', function (e) {
    var b = e.target.closest('[data-copy]');
    if (b) {
      var src = doc.getElementById(b.getAttribute('data-copy')); var text = src ? (src.value || src.textContent) : '';
      var done = function () { announce('Copied'); b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy'; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { announce('Copy failed: select the text and copy it'); });
      return;
    }
    var s = e.target.closest('#share');
    if (s) {
      var url = location.href;
      if (navigator.share) navigator.share({ title: doc.title, url: url }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { announce('Link copied'); });
    }
  });

  /* ---- command palette and search ------------------------------------------------------------------------ */
  var pal = $('#palette'), palIn = $('#pal-q'), palList = $('#pal-list'), sel = 0, hits = [];
  function openPal() { if (!pal || !pal.showModal) return; pal.showModal(); palIn.value = ''; render(''); palIn.focus(); }
  function render(q) {
    var idx = window.UKAP_SEARCH || [];
    q = q.toLowerCase().trim();
    var words = q.split(/\s+/).filter(Boolean);
    hits = idx.map(function (x) {
      var hay = (x.t + ' ' + x.s + ' ' + x.k).toLowerCase(), score = 0;
      if (!words.length) return { x: x, s: x.k === 'Page' ? 2 : 0 };
      for (var i = 0; i < words.length; i++) { if (hay.indexOf(words[i]) < 0) return null; score += x.t.toLowerCase().indexOf(words[i]) > -1 ? 3 : 1; }
      return { x: x, s: score };
    }).filter(Boolean).sort(function (a, b) { return b.s - a.s; }).slice(0, 40);
    sel = 0;
    palList.innerHTML = hits.map(function (h, i) { return '<li><a role="option" id="pal-' + i + '" href="' + esc(h.x.u) + '" aria-selected="' + (i === 0) + '">' + esc(h.x.t) + '<small>' + esc(h.x.k) + (h.x.s ? ' · ' + esc(h.x.s) : '') + '</small></a></li>'; }).join('') || '<li>No matches. Try fewer words.</li>';
    palIn.setAttribute('aria-activedescendant', hits.length ? 'pal-0' : '');
    $('#pal-count').textContent = hits.length + (hits.length === 1 ? ' result' : ' results');
  }
  if (pal) {
    palIn.addEventListener('input', function () { render(palIn.value); });
    palIn.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); if (!hits.length) return;
        sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
        $$('a', palList).forEach(function (a, i) { a.setAttribute('aria-selected', String(i === sel)); if (i === sel) a.scrollIntoView({ block: 'nearest' }); });
        palIn.setAttribute('aria-activedescendant', 'pal-' + sel);
      } else if (e.key === 'Enter' && hits[sel]) { location.href = hits[sel].x.u; }
      else if (e.key === 'Escape') { e.preventDefault(); pal.close(); }
    });
    $$('[data-open="palette"]').forEach(function (b) { b.addEventListener('click', openPal); });
    $('#pal-close').addEventListener('click', function () { pal.close(); });
  }
  doc.addEventListener('keydown', function (e) {
    var typing = /INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || '');
    if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); openPal(); }
    else if (!typing && e.key === '/') { e.preventDefault(); openPal(); }
    else if (!typing && e.key === '?') { var k = $('#keys'); if (k && k.showModal) k.showModal(); }
    else if (e.key === 'Escape') { hideTip(); closeMenus(); if (drawer && window.innerWidth <= 960 && !drawer.hidden) setDrawer(false); }
  });
  var kc = $('#keys-close'); if (kc) kc.addEventListener('click', function () { $('#keys').close(); });

  /* ---- knowledge graph: filter by kind, highlight neighbours ---------------------------------------------- */
  var kg = $('#kg');
  if (kg) {
    $$('input[data-kind]').forEach(function (cb) {
      cb.addEventListener('change', function () { $$('[data-k="' + cb.getAttribute('data-kind') + '"]', kg).forEach(function (n) { n.style.display = cb.checked ? '' : 'none'; }); });
    });
    kg.addEventListener('focusin', function (e) { var g = e.target.closest('[data-n]'); if (g) hl(g.getAttribute('data-n')); });
    kg.addEventListener('mouseover', function (e) { var g = e.target.closest('[data-n]'); if (g) hl(g.getAttribute('data-n')); });
    function hl(id) { $$('line', kg).forEach(function (l) { var on = l.getAttribute('data-a') === id || l.getAttribute('data-b') === id; l.style.strokeWidth = on ? 3 : 1; l.style.opacity = on ? 1 : .25; }); }
  }

  /* ---- record builder ------------------------------------------------------------------------------------- */
  var P0 = window.UKAP_PROFILE, P = P0, V = window.UKAPValidator;
  // The profile in use: the base, or the base plus a sector extension chosen in a select.
  function useExt(id) { P = id ? V.withExtensions(P0, [id]) : P0; return P; }
  var qext = (/[?&]ext=([a-z-]+)/.exec(location.search) || [])[1];
  var bform = $('#builder-form');
  if (bform && P && V) builder();
  var vbox = $('#validate-form');
  if (vbox && P && V) validator();
  if ($('#bulk-form') && P && V) bulk();
  if ($('#oas-form') && P && V) openapi();
  var ckf = $('#checklist-form');
  if (ckf) checklist(ckf);

  function fairHtml(q) {
    return q.dimensions.map(function (d) {
      return '<h3 class="h4">' + esc(d.label) + ' <span class="small">' + d.score + ' of ' + d.max + '</span></h3><div class="meter" aria-hidden="true"><span style="width:' + (100 * d.score / d.max) + '%"></span></div><ul class="results">' +
        d.items.map(function (it) { return '<li class="' + (it.met ? 'ok' : 'warning') + '">' + (it.met ? 'Has ' : 'Missing: ') + esc(it.label.toLowerCase()) + ' <span class="small">(' + it.points + ')</span></li>'; }).join('') + '</ul>';
    }).join('') + '<p class="small">Modelled on the five dimensions of the EU metadata quality assessment. Addresses are checked for form, not fetched.</p>';
  }
  function levelHtml(c) {
    var cls = ['err', 'warn', 'ok', 'ok'][c.level];
    return '<p><span class="tag ' + cls + '">' + esc(c.label) + '</span> ' + esc(c.next) + ' <a href="adopt.html#levels" class="small">About levels</a></p>';
  }

  function plabel(path) {
    if (!path) return 'Record';
    return String(path).split('.').filter(Boolean).map(function (seg) { var k = seg.replace(/\[\d+\]$/, ''); return P.props[k] ? P.props[k].label : seg; }).join(' \u203a ');
  }

  function compactValue(prop, raw, multi) {
    raw = (raw || '').trim(); if (!raw) return undefined;
    if (!multi) return raw;
    return raw.split(/\n|;/).map(function (s) { return s.trim(); }).filter(Boolean);
  }

  function builder() {
    var clsSel = $('#b-class'), fields = $('#b-fields'), cdaBox = $('#b-cda');
    var state = {};
    function build() {
      var ck = clsSel.value, C = P.classes[ck];
      cdaBox.closest('.field').hidden = !C.props.some(function (x) { return x.p === 'criticalDataAsset'; });
      var cda = cdaBox.checked && !cdaBox.closest('.field').hidden;
      fields.innerHTML = '';
      var groups = { M: [], C: [], R: [], O: [] };
      C.props.forEach(function (x) { if (x.p === 'criticalDataAsset') return; var ob = (cda && x.cda) ? x.cda : x.ob; groups[ob].push(x); });
      [['M', 'Mandatory'], ['C', 'Conditional'], ['R', 'Recommended'], ['O', 'Optional']].forEach(function (g) {
        if (!groups[g[0]].length) return;
        var fs = el('fieldset'); fs.appendChild(el('legend', {}, esc(g[1]) + ' <span class="tag ' + g[0] + '">' + groups[g[0]].length + '</span>'));
        if (g[0] === 'O') { var d = el('details'); d.appendChild(el('summary', {}, 'Show optional properties')); d.appendChild(fs); fields.appendChild(d); }
        else fields.appendChild(fs);
        groups[g[0]].forEach(function (x) { fs.appendChild(field(ck, x, g[0])); });
      });
      update();
    }
    function field(ck, x, ob) {
      var prop = P.props[x.p], id = 'f-' + x.p, multi = /n$/.test(x.card);
      var w = el('div', { 'class': 'field ' + ob, 'data-p': x.p });
      var hintText = prop.definition + (x.condition ? ' ' + x.condition : '') + (multi && prop.kind !== 'object' && prop.kind !== 'concept' ? ' One per line for more than one.' : '');
      w.appendChild(el('label', { 'for': id }, esc(prop.label) + ' <span class="tag ' + ob + '">' + ({ M: 'Mandatory', R: 'Recommended', O: 'Optional', C: 'Conditional' })[ob] + '</span>' + (prop.provisional ? ' <span class="tag warn">Provisional</span>' : '') + ' <a href="properties.html#p-' + x.p + '" class="small">about this</a>'));
      w.appendChild(el('p', { 'class': 'hint', id: id + '-h' }, esc(hintText)));
      var input;
      if (prop.kind === 'concept' && P.codelists[prop.codelist] && !P.codelists[prop.codelist].open) {
        input = el('select', { id: id, 'aria-describedby': id + '-h' });
        if (multi) { input.multiple = true; input.size = Math.min(6, P.codelists[prop.codelist].concepts.length); }
        input.innerHTML = (multi ? '' : '<option value="">Choose</option>') + P.codelists[prop.codelist].concepts.map(function (c) { return '<option value="' + esc(c.compact) + '">' + esc(c.label) + '</option>'; }).join('');
      } else if (prop.kind === 'iri' && prop.codelist === 'licences') {
        input = el('select', { id: id, 'aria-describedby': id + '-h' });
        input.innerHTML = '<option value="">Choose</option>' + P.codelists.licences.concepts.map(function (c) { return '<option value="' + esc(c.iri) + '">' + esc(c.label) + '</option>'; }).join('');
      } else if (prop.kind === 'object' && prop.range === 'ContactPoint') {
        input = el('div', { id: id, 'class': 'sub' });
        input.innerHTML = '<label for="' + id + '-fn">Team name</label><input type="text" id="' + id + '-fn" autocomplete="off">' +
          '<label for="' + id + '-url">Contact form address</label><input type="url" id="' + id + '-url" placeholder="https://">' +
          '<label for="' + id + '-mail">Team mailbox (optional; a form is preferred)</label><input type="text" id="' + id + '-mail" placeholder="mailto:">';
      } else if (prop.kind === 'object' && prop.range === 'PeriodOfTime') {
        input = el('div', { id: id, 'class': 'sub' });
        input.innerHTML = '<label for="' + id + '-s">Start date</label><input type="date" id="' + id + '-s"><label for="' + id + '-e">End date</label><input type="date" id="' + id + '-e">';
      } else if (prop.kind === 'date') {
        input = el('input', { type: 'text', id: id, inputmode: 'numeric', placeholder: 'yyyy-mm-dd', 'aria-describedby': id + '-h' });
      } else if (prop.kind === 'boolean') {
        input = el('select', { id: id }); input.innerHTML = '<option value="">Choose</option><option value="true">Yes</option><option value="false">No</option>';
      } else if (prop.kind === 'text' && /description|rights|versionNotes/.test(x.p)) {
        input = el('textarea', { id: id, 'aria-describedby': id + '-h' });
      } else if (multi) {
        input = el('textarea', { id: id, rows: '2', 'aria-describedby': id + '-h', placeholder: prop.example || '' }); input.style.minHeight = '3rem';
      } else {
        input = el('input', { type: /url|iri|object/.test(prop.kind) ? 'url' : 'text', id: id, 'aria-describedby': id + '-h', placeholder: prop.example || '', autocomplete: 'off' });
      }
      w.appendChild(input);
      if (prop.kind === 'object' && prop.range === 'Agent') {
        var dl = $('#orgs-list'); if (dl) input.setAttribute('list', 'orgs-list');
      }
      $$('input,select,textarea', w).forEach(function (i) {
        var k = id + (i.id === id ? '' : i.id.slice(id.length)); if (state[k] !== undefined) setVal(i, state[k]);
        i.addEventListener(i.tagName === 'SELECT' ? 'change' : 'input', function () { state[k] = getVal(i); update(); });
      });
      return w;
    }
    function getVal(i) { return i.multiple ? $$('option', i).filter(function (o) { return o.selected; }).map(function (o) { return o.value; }) : i.value; }
    function setVal(i, v) {
      if (i.multiple) { var vs = (v || []).map(function (x) { return [x, V.expand(P, x)]; }); $$('option', i).forEach(function (o) { o.selected = vs.some(function (p2) { return p2.indexOf(o.value) > -1 || p2.indexOf(V.expand(P, o.value)) > -1; }); }); return; }
      i.value = v;
      if (i.tagName === 'SELECT' && i.value !== v) { var full = V.expand(P, v); $$('option', i).forEach(function (o) { if (V.expand(P, o.value) === full) i.value = o.value; }); }
    }
    function record() {
      var ck = clsSel.value, C = P.classes[ck], rec = { 'class': ck };
      var idv = ($('#b-id').value || '').trim(); if (idv) rec.id = idv;
      if (cdaBox.checked && !cdaBox.closest('.field').hidden) rec.criticalDataAsset = 'true';
      C.props.forEach(function (x) {
        var prop = P.props[x.p], id = 'f-' + x.p, multi = /n$/.test(x.card), node = doc.getElementById(id); if (!node) return;
        var v;
        if (prop.range === 'ContactPoint') {
          var cp = {}; var fn = $('#' + id + '-fn').value.trim(), u = $('#' + id + '-url').value.trim(), m = $('#' + id + '-mail').value.trim();
          if (fn) cp.fn = fn; if (u) cp.hasURL = u; if (m) cp.hasEmail = /^mailto:/.test(m) ? m : 'mailto:' + m;
          if (Object.keys(cp).length) v = [cp];
        } else if (prop.range === 'PeriodOfTime') {
          var pt = {}; var s = $('#' + id + '-s').value, e = $('#' + id + '-e').value; if (s) pt.startDate = s; if (e) pt.endDate = e;
          if (Object.keys(pt).length) v = [pt];
        } else if (node.multiple) { v = getVal(node); if (!v.length) v = undefined; }
        else v = compactValue(prop, node.value, multi && node.tagName === 'TEXTAREA' && !/description|rights|versionNotes/.test(x.p));
        if (v !== undefined) rec[x.p] = v;
      });
      return rec;
    }
    function update() {
      var rec = record(), res = V.validate(P, rec), comp = V.completeness(P, rec);
      $('#b-json').textContent = JSON.stringify(rec, null, 2);
      $('#b-jsonld').textContent = JSON.stringify(Object.assign({ '@context': 'https://cyberdudeuk.github.io/dcat-uk-ap/downloads/dcat-uk-ap.context.jsonld' }, rec), null, 2);
      $('#b-ttl').textContent = V.toTurtle(P, rec);
      $('#b-sdo').textContent = JSON.stringify(V.toSchemaOrg(P, rec), null, 2);
      $('#b-cr').textContent = JSON.stringify(V.toCroissant(P, rec), null, 2);
      var q = V.fair(P, rec);
      $('#b-level').innerHTML = levelHtml(V.conformance(P, rec));
      $('#b-fair-s').textContent = q.score + ' of ' + q.max + ' (' + q.rating.toLowerCase() + ')';
      $('#b-fair').innerHTML = fairHtml(q);
      var m = comp.mandatory, r = comp.recommended;
      $('#b-m').style.width = (m[1] ? 100 * m[0] / m[1] : 0) + '%'; $('#b-m-t').textContent = m[0] + ' of ' + m[1] + ' mandatory';
      $('#b-r').style.width = (r[1] ? 100 * r[0] / r[1] : 0) + '%'; $('#b-r-t').textContent = r[0] + ' of ' + r[1] + ' recommended';
      var errs = res.issues.filter(function (i) { return i.level === 'error'; });
      $('#b-status').innerHTML = res.ok ? '<span class="tag ok">Conforms</span> No errors. ' + res.warnings + ' recommendations.' : '<span class="tag err">' + errs.length + ' to fix</span>';
      $('#b-issues').innerHTML = res.issues.slice(0, 30).map(function (i) { return '<li class="' + i.level + '"><strong>' + esc(plabel(i.prop)) + '</strong>: ' + esc(i.text) + ' <span class="small">(' + esc(i.rule) + ')</span></li>'; }).join('');
      $$('.field', fields).forEach(function (f) { f.classList.toggle('bad', errs.some(function (i) { return i.prop.split(/[.[]/)[0] === f.getAttribute('data-p'); })); });
    }
    clsSel.addEventListener('change', build); cdaBox.addEventListener('change', build); $('#b-id').addEventListener('input', update);
    var bext = $('#b-ext');
    if (bext) { if (qext) bext.value = qext; useExt(bext.value); bext.addEventListener('change', function () { useExt(bext.value); build(); announce(bext.value ? 'Extension applied' : 'Extension removed'); }); }
    var NAMES = { json: 'record.json', jsonld: 'record.jsonld', ttl: 'record.ttl', sdo: 'record.schema.jsonld', cr: 'record.croissant.jsonld' };
    $$('[data-dl]').forEach(function (b) { b.addEventListener('click', function () { var k = b.getAttribute('data-dl'); download(NAMES[k], $('#b-' + k).textContent, k === 'ttl' ? 'text/turtle' : 'application/ld+json'); }); });
    var ex = $('#b-example');
    if (ex) ex.addEventListener('change', function () {
      var e = (window.UKAP_EXAMPLES || {})[ex.value]; if (!e) return;
      clsSel.value = e['class']; cdaBox.checked = String(e.criticalDataAsset) === 'true'; $('#b-id').value = e.id || ''; state = {};
      Object.keys(e).forEach(function (k) {
        var v = e[k], id = 'f-' + k, prop = P.props[k]; if (!prop) return;
        if (prop.range === 'ContactPoint') { var cp = (v[0] || v); state[id + '-fn'] = cp.fn || ''; state[id + '-url'] = cp.hasURL || ''; state[id + '-mail'] = cp.hasEmail || ''; }
        else if (prop.range === 'PeriodOfTime') { var pt = (v[0] || v); state[id + '-s'] = pt.startDate || ''; state[id + '-e'] = pt.endDate || ''; }
        else if (prop.kind === 'concept' && Array.isArray(v)) state[id] = v;
        else if (typeof v === 'object' && !Array.isArray(v)) return;
        else state[id] = Array.isArray(v) ? v.filter(function (x) { return typeof x !== 'object'; }).join('\n') : String(v);
      });
      build(); announce('Example loaded');
    });
    build();
  }

  function validator() {
    var ta = $('#v-input'), out = $('#v-out'), mode = $('#v-mode'), vext = $('#v-ext');
    if (vext && qext) vext.value = qext;
    function run() {
      var text = ta.value.trim(); if (!text) { out.innerHTML = '<p>Paste a record to check it.</p>'; return; }
      var data, notes = [];
      try { data = /^\s*[{[]/.test(text) ? JSON.parse(text) : miniYaml(text); }
      catch (e) { out.innerHTML = '<div class="panel warning"><h3>The text could not be read</h3><p>' + esc(e.message) + '</p></div>'; return; }
      useExt(vext ? vext.value : '');
      if (mode.value === 'mem') { var c = V.fromMem(P, data); data = c.record; notes = c.notes; }
      var recs = Array.isArray(data) ? data : [data];
      out.innerHTML = recs.map(function (r, n) {
        var res = V.validate(P, r), q = V.fair(P, r);
        return '<section class="panel ' + (res.ok ? 'notice' : 'warning') + '"><h3>' + (recs.length > 1 ? 'Record ' + (n + 1) + ': ' : '') + (res.ok ? 'Conforms to DCAT-UK AP' + (P.applied && P.applied.length ? ' with the ' + esc(P0.extensions[P.applied[0]].label.toLowerCase()) + ' extension' : '') : res.errors + ' to fix') + '</h3>' +
          levelHtml(V.conformance(P, r)) + '<details><summary>Quality score: ' + q.score + ' of ' + q.max + ' (' + esc(q.rating.toLowerCase()) + ')</summary>' + fairHtml(q) + '</details>' +
          (notes.length ? '<p><strong>Converted from the xGov MEM.</strong></p><ul>' + notes.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '') +
          '<ul class="results">' + res.issues.map(function (i) { return '<li class="' + i.level + '"><strong>' + esc(plabel(i.prop)) + '</strong>: ' + esc(i.text) + ' <span class="small">(' + esc(i.rule) + ')</span></li>'; }).join('') + '</ul>' +
          (mode.value === 'mem' ? '<h4>Converted record</h4><pre>' + esc(JSON.stringify(r, null, 2)) + '</pre>' : '') + '</section>';
      }).join('');
      announce(out.textContent.slice(0, 120));
    }
    $('#v-run').addEventListener('click', run);
    $$('[data-sample]').forEach(function (b) { b.addEventListener('click', function () { ta.value = doc.getElementById(b.getAttribute('data-sample')).textContent.trim(); mode.value = b.getAttribute('data-mode'); run(); }); });
  }


  function bulk() {
    var out = $('#bk-out'), ta = $('#bk-text'), fi = $('#bk-file'), ext = $('#bk-ext');
    if (ext && qext) ext.value = qext;
    var last = [];
    function run() {
      var text = ta.value;
      if (!text.trim()) { out.innerHTML = '<p>Choose a file or paste CSV first.</p>'; return; }
      useExt(ext.value);
      var conv = V.fromCSV(P, text);
      last = conv.records;
      var rows = conv.records.map(function (r, i) {
        var res = V.validate(P, r), c = V.conformance(P, r), q = V.fair(P, r);
        var first = res.issues.filter(function (x) { return x.level === 'error'; }).slice(0, 3).map(function (x) { return esc(plabel(x.prop)) + ': ' + esc(x.text); }).join('<br>');
        return { c: c, html: '<tr data-level="' + c.level + '"><th scope="row">' + (i + 2) + '</th><td>' + esc(r.title || '(no title)') + '</td><td><span class="tag ' + ['err', 'warn', 'ok', 'ok'][c.level] + '">' + esc(c.label) + '</span></td><td class="num">' + res.errors + '</td><td class="num">' + q.score + '</td><td>' + (first || 'None') + '</td></tr>' };
      });
      var counts = [0, 0, 0, 0]; rows.forEach(function (r) { counts[r.c.level]++; });
      out.innerHTML = '<section class="panel notice"><h2>' + rows.length + ' record' + (rows.length === 1 ? '' : 's') + ' checked</h2><p>' + counts[0] + ' do not conform, ' + counts[1] + ' at level 1, ' + counts[2] + ' at level 2, ' + counts[3] + ' at level 3.</p>' +
        (conv.notes.length ? '<ul>' + conv.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>' : '') +
        '<p class="btns"><button type="button" class="btn small" id="bk-dl-jsonld">Download all as JSON-LD</button><button type="button" class="btn secondary small" id="bk-dl-ttl">Download all as Turtle</button><button type="button" class="btn secondary small" id="bk-dl-json">Download all as JSON</button></p></section>' +
        '<div class="table-wrap" role="region" aria-labelledby="bk-cap" tabindex="0"><table id="bk-t"><caption id="bk-cap">Every record, by spreadsheet row</caption><thead><tr><th scope="col">Row</th><th scope="col">Title</th><th scope="col">Level</th><th scope="col" class="num">Errors</th><th scope="col" class="num">Quality</th><th scope="col">First errors</th></tr></thead><tbody>' +
        rows.map(function (r) { return r.html; }).join('') + '</tbody></table></div>';
      $('#bk-dl-jsonld').addEventListener('click', function () { download('records.jsonld', JSON.stringify({ '@context': 'https://cyberdudeuk.github.io/dcat-uk-ap/downloads/dcat-uk-ap.context.jsonld', '@graph': last }, null, 1), 'application/ld+json'); });
      $('#bk-dl-ttl').addEventListener('click', function () { download('records.ttl', last.map(function (r) { return V.toTurtle(P, r); }).join('\n'), 'text/turtle'); });
      $('#bk-dl-json').addEventListener('click', function () { download('records.json', JSON.stringify(last, null, 1), 'application/json'); });
      announce(rows.length + ' records checked');
    }
    fi.addEventListener('change', function () { var file = fi.files && fi.files[0]; if (!file) return; var rd = new FileReader(); rd.onload = function () { ta.value = String(rd.result); run(); }; rd.readAsText(file); });
    $('#bk-run').addEventListener('click', run);
    $('#bk-sample').addEventListener('click', function () {
      var x = new XMLHttpRequest(); x.open('GET', 'downloads/template.csv'); x.onload = function () { if (x.status === 200) { ta.value = x.responseText; run(); } else out.innerHTML = '<p>The template could not be loaded. Download it with the button above.</p>'; };
      x.onerror = function () { out.innerHTML = '<p>The template could not be loaded from this copy of the portal. Download it with the button above.</p>'; }; x.send();
    });
  }

  function openapi() {
    var out = $('#oas-out'), ta = $('#oas-text'), url = $('#oas-url');
    function run() {
      var oas;
      try { oas = JSON.parse(ta.value); } catch (e) { out.innerHTML = '<div class="panel warning"><h2>The description could not be read</h2><p>It must be JSON. ' + esc(e.message) + '</p></div>'; return; }
      useExt('');
      var c = V.fromOpenAPI(P, oas, { url: url.value.trim() }), res = V.validate(P, c.record);
      out.innerHTML = '<section class="panel ' + (res.ok ? 'notice' : 'warning') + '"><h2>Draft data service record</h2>' + levelHtml(V.conformance(P, c.record)) +
        '<h3 class="h4">What to add or check</h3><ul>' + c.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>' +
        '<ul class="results">' + res.issues.map(function (i) { return '<li class="' + i.level + '"><strong>' + esc(plabel(i.prop)) + '</strong>: ' + esc(i.text) + ' <span class="small">(' + esc(i.rule) + ')</span></li>'; }).join('') + '</ul>' +
        '<pre id="oas-rec" tabindex="0">' + esc(JSON.stringify(c.record, null, 2)) + '</pre><p class="btns"><button type="button" class="btn small" id="oas-dl">Download JSON</button><button type="button" class="btn secondary small" data-copy="oas-rec">Copy</button></p></section>';
      $('#oas-dl').addEventListener('click', function () { download('data-service.json', JSON.stringify(c.record, null, 2), 'application/json'); });
      announce('Record drafted');
    }
    $('#oas-run').addEventListener('click', run);
    $('#oas-sample').addEventListener('click', function () { ta.value = $('#oas-s').textContent.trim(); url.value = 'https://api.example.org/bus-stops/openapi.json'; run(); });
  }

  function checklist(form) {
    var boxes = $$('input[data-check]', form);
    function count() { var n = boxes.filter(function (b) { return b.checked; }).length; var c = $('#ck-count'); if (c) c.textContent = n + ' of ' + boxes.length + ' done'; }
    boxes.forEach(function (b) {
      b.checked = store.get('check:' + b.getAttribute('data-check')) === '1';
      b.addEventListener('change', function () { store.set('check:' + b.getAttribute('data-check'), b.checked ? '1' : '0'); count(); });
    });
    count();
  }

  // A small YAML reader for flat records like the xGov MEM examples: key: value, lists, one level of nesting, block text.
  function miniYaml(text) {
    var lines = text.replace(/\r/g, '').split('\n').filter(function (l) { return !/^\s*(#|---\s*$)/.test(l) && l.trim(); });
    var out = {}, i = 0;
    function scalar(s) { s = s.trim().replace(/\s+#.*$/, ''); if (/^".*"$|^'.*'$/.test(s)) return s.slice(1, -1); if (/^\[.*\]$/.test(s)) return s.slice(1, -1).split(',').map(function (x) { return scalar(x); }).filter(function (x) { return x !== ''; }); return s; }
    while (i < lines.length) {
      var m = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(lines[i]);
      if (!m) throw new Error('Line ' + (i + 1) + ' is not "name: value": ' + lines[i]);
      var k = m[1], v = m[2]; i++;
      if (/^[|>]-?$/.test(v)) { var buf = []; while (i < lines.length && /^\s+/.test(lines[i])) buf.push(lines[i++].trim()); out[k] = buf.join(v[0] === '|' ? '\n' : ' '); }
      else if (v === '') {
        if (i < lines.length && /^\s*-\s/.test(lines[i])) { out[k] = []; while (i < lines.length && /^\s*-\s/.test(lines[i])) out[k].push(scalar(lines[i++].replace(/^\s*-\s/, ''))); }
        else { out[k] = {}; while (i < lines.length && /^\s+\S/.test(lines[i])) { var n = /^\s+([\w-]+):\s*(.*)$/.exec(lines[i++]); if (n) out[k][n[1]] = scalar(n[2]); } }
      } else out[k] = scalar(v);
    }
    return out;
  }
})();
