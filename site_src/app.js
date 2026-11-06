/* DCAT-AP-UK portal behaviour. No network requests, no third-party code, nothing stored except per-viewer display choices
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

  /* ---- display options panel in the masthead (the estate pattern): text, spacing, colours, contrast, motion, links ---- */
  var DP = ['text', 'space', 'theme', 'contrast', 'motion', 'links'];
  if (store.get('theme') && !store.get('dp-theme')) store.set('dp-theme', store.get('theme'));
  if (store.get('size') === 'large' && !store.get('dp-text')) store.set('dp-text', 'l');
  if (store.get('spacing') === 'wide' && !store.get('dp-space')) store.set('dp-space', 'wide');
  function applyDisplay() { DP.forEach(function (k) { var v = store.get('dp-' + k); if (v) root.setAttribute('data-' + k, v); else root.removeAttribute('data-' + k); }); }
  applyDisplay();
  var dpBtn = $('#display-toggle'), dpPanel = $('#display-panel');
  if (dpBtn && dpPanel) {
    dpBtn.hidden = false;
    var syncDP = function () { DP.forEach(function (k) { $$('input[name="dp-' + k + '"]', dpPanel).forEach(function (r) { r.checked = r.value === (store.get('dp-' + k) || ''); }); }); };
    syncDP();
    dpPanel.addEventListener('change', function (e) {
      var n = e.target.name; if (!n || n.indexOf('dp-') !== 0) return;
      store.set(n, e.target.value); applyDisplay(); announce('Display changed');
    });
    $('#dp-reset').addEventListener('click', function () { DP.forEach(function (k) { store.set('dp-' + k, ''); }); applyDisplay(); syncDP(); announce('Display options reset'); });
    dpBtn.addEventListener('click', function () {
      var open = dpPanel.hidden; dpPanel.hidden = !open; dpBtn.setAttribute('aria-expanded', String(open));
      if (open) { var f = dpPanel.querySelector('input:checked') || dpPanel.querySelector('input'); if (f) f.focus(); }
    });
    doc.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !dpPanel.hidden) { dpPanel.hidden = true; dpBtn.setAttribute('aria-expanded', 'false'); dpBtn.focus(); } });
  }

  /* D-025: no form on the portal sends anything anywhere, and the content security policy says form-action 'none'.
     Pressing Enter in a one-field form tried to submit it, the policy blocked that and the page hung. Every submit is
     handled here; a form that does something on submit has its own handler (find-an-item on the lineage page). */
  doc.addEventListener('submit', function (e) { e.preventDefault(); }, true);

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
  /* D-024: a group folded into More is nested inside it, so closing every other open menu also closed More, the group's
     own parent, and the group could never open. Ancestors of the menu being opened now stay open. */
  function closeMenus(except) {
    $$('.gbar li.open').forEach(function (li) {
      if (except && li.contains(except)) return;
      li.classList.remove('open'); var b = $(':scope > button', li); if (b) b.setAttribute('aria-expanded', 'false');
    });
  }
  if (gbar) {
    gbar.addEventListener('click', function (e) {
      var b = e.target.closest('button[aria-expanded]'); if (!b || !gbar.contains(b)) return;
      var li = b.parentNode, open = !li.classList.contains('open');
      closeMenus(li); li.classList.toggle('open', open); b.setAttribute('aria-expanded', String(open));
      // a menu that would run past the right edge opens leftwards instead
      var sub = open && $(':scope > ul', li);
      if (sub) { sub.classList.remove('flip'); if (sub.getBoundingClientRect().right > root.clientWidth) sub.classList.add('flip'); }
      // D-027: a group opened inside More can sit below the part of More that is in view; bring its items into view
      var inMore = open && li.parentNode.closest('li.more'), first = inMore && $(':scope > ul > li > a', li);
      if (first) first.scrollIntoView({ block: 'nearest' });
      if (!open) $$('li.open', li).forEach(function (x) { x.classList.remove('open'); var xb = $(':scope > button', x); if (xb) xb.setAttribute('aria-expanded', 'false'); });
    });
    doc.addEventListener('click', function (e) { if (!e.target.closest('.gbar')) closeMenus(); });
    gbar.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var li = e.target.closest('li.open') || (e.target.closest('li') && e.target.closest('li').parentNode.closest('li.open'));
      if (!li) return;
      e.preventDefault(); e.stopPropagation();
      li.classList.remove('open'); var b = $(':scope > button', li); b.setAttribute('aria-expanded', 'false'); b.focus();
    });
    gbar.addEventListener('focusout', function (e) { if (e.relatedTarget && !gbar.contains(e.relatedTarget)) closeMenus(); });
    var top = $('ul.top', gbar), more = $('li.more', gbar), moreList = more && $('.sub', more);
    var originals = $$(':scope > li:not(.more)', top);
    gbar.classList.add('js-fold');
    var fold = function () {
      originals.forEach(function (li) { top.insertBefore(li, more); });
      gbar.classList.remove('folding'); more.classList.remove('current');
      if (top.scrollWidth <= top.clientWidth + 1) return;
      gbar.classList.add('folding');
      var items = $$(':scope > li:not(.more)', top);
      for (var i = items.length - 1; i > 0 && top.scrollWidth > top.clientWidth + 1; i--) moreList.insertBefore(items[i], moreList.firstChild);
      // D-026: when the current section is folded into More, More shows it, so the bar always says where you are
      more.classList.toggle('current', !!$('li.current, [aria-current="page"]', moreList));
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
      var was = b.getAttribute('data-was') || b.innerHTML; b.setAttribute('data-was', was);
      var done = function () { announce('Copied'); b.textContent = 'Copied'; setTimeout(function () { b.innerHTML = was; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { announce('Copy failed: select the text and copy it'); });
      return;
    }
    var s = e.target.closest('#share');
    if (s) {
      var url = location.href;
      if (navigator.share) navigator.share({ title: doc.title, url: url }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { announce('Link copied'); }, function () { announce('Copy the address from the address bar'); });
      else announce('Copy the address from the address bar');
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

  /* ---- guided tours: one step at a time, next to the part of the page it explains -------------------------------- */
  var tourData = $('#tour-data');
  if (tourData) {
    var steps = [];
    try { steps = JSON.parse(tourData.textContent).filter(function (s) { return $(s.sel); }); } catch (e) { steps = []; }
    var tb = $('#tour-start');
    if (tb && steps.length) {
      tb.hidden = false;
      var pop = null, cur = 0, lastFocus = null;
      var end = function () {
        if (!pop) return;
        $$('.tour-hl').forEach(function (x) { x.classList.remove('tour-hl'); });
        pop.remove(); pop = null; doc.removeEventListener('keydown', key);
        if (lastFocus) lastFocus.focus();
        announce('Tour ended');
      };
      var key = function (e) {
        if (e.key === 'Escape') { e.preventDefault(); end(); }
        else if (e.key === 'ArrowRight' && pop && !e.target.closest('input,textarea,select')) { e.preventDefault(); show(cur + 1); }
        else if (e.key === 'ArrowLeft' && pop && !e.target.closest('input,textarea,select')) { e.preventDefault(); show(cur - 1); }
      };
      var show = function (i) {
        if (i < 0) i = 0;
        if (i >= steps.length) return end();
        cur = i;
        $$('.tour-hl').forEach(function (x) { x.classList.remove('tour-hl'); });
        var s = steps[i], t = $(s.sel);
        // a target inside a hidden tab panel: show its panel first
        var tp = t.closest('[role="tabpanel"][hidden]'); if (tp) { var tab = $('#' + tp.getAttribute('aria-labelledby')); if (tab) tab.click(); }
        t.classList.add('tour-hl');
        t.scrollIntoView({ block: 'center', behavior: root.getAttribute('data-motion') === 'reduce' ? 'auto' : 'smooth' });
        if (!pop) {
          pop = el('div', { 'class': 'tour-pop', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'tour-h', tabindex: '-1' });
          doc.body.appendChild(pop); doc.addEventListener('keydown', key);
        }
        pop.innerHTML = '<p class="step">Step ' + (i + 1) + ' of ' + steps.length + '</p><h2 id="tour-h">' + esc(s.title) + '</h2><p>' + esc(s.text) + '</p>' +
          '<p class="btns">' + (i ? '<button type="button" class="btn secondary small" data-t="prev">Back</button>' : '') +
          '<button type="button" class="btn small" data-t="next">' + (i === steps.length - 1 ? 'Finish' : 'Next') + '</button>' +
          '<button type="button" class="btn secondary small" data-t="end">End tour</button></p>';
        var r = t.getBoundingClientRect(), top = window.scrollY + r.bottom + 12, left = Math.max(8, Math.min(window.scrollX + r.left, window.scrollX + doc.documentElement.clientWidth - 360));
        pop.style.top = top + 'px'; pop.style.left = left + 'px';
        pop.focus();
      };
      doc.addEventListener('click', function (e) {
        var b = e.target.closest('.tour-pop [data-t]'); if (!b) return;
        var a = b.getAttribute('data-t'); if (a === 'next') show(cur + 1); else if (a === 'prev') show(cur - 1); else end();
      });
      tb.addEventListener('click', function () { lastFocus = tb; show(0); });
      if (/[?&]tour=1/.test(location.search)) setTimeout(function () { lastFocus = tb; show(0); }, 300);
    }
  }

  /* ---- tutorials: tick steps, see progress (kept in this browser only) --------------------------------------------- */
  var tutBoxes = $$('input[data-tut]');
  if (tutBoxes.length) {
    var tutCount = function () {
      var by = {};
      tutBoxes.forEach(function (b) { var t = b.getAttribute('data-tut'); by[t] = by[t] || [0, 0]; by[t][1]++; if (b.checked) by[t][0]++; });
      Object.keys(by).forEach(function (t) {
        var bar = $('[data-tut-bar="' + t + '"]'), c = $('[data-tut-count="' + t + '"]');
        if (bar) bar.style.width = (100 * by[t][0] / by[t][1]) + '%';
        if (c) c.textContent = by[t][0] + ' of ' + by[t][1] + ' steps done' + (by[t][0] === by[t][1] ? '. Well done.' : '');
      });
    };
    tutBoxes.forEach(function (b) { b.checked = store.get('tut:' + b.id) === '1'; b.addEventListener('change', function () { store.set('tut:' + b.id, b.checked ? '1' : '0'); tutCount(); }); });
    tutCount();
  }

  /* ---- lineage explorer ------------------------------------------------------------------------------------------------ */
  var LG = window.UKAP_LINEAGE, trace = $('#trace');
  if (LG && trace) {
    var byId = {}, up = {}, down = {};
    LG.nodes.forEach(function (n) { byId[n.id] = n; up[n.id] = []; down[n.id] = []; });
    LG.edges.forEach(function (e) { if (byId[e[0]] && byId[e[1]]) { down[e[0]].push(e[1]); up[e[1]].push(e[0]); } });
    var KIND = { source: 'Source', mem: 'MEM slot', property: 'Property', 'class': 'Class', codelist: 'Codelist', rule: 'Rule', issue: 'Issue', example: 'Example', test: 'Test', extension: 'Extension', crosswalk: 'Crosswalk', defect: 'Defect', standard: 'Standard' };
    var tq = $('#tr-q'), tk = $('#tr-kind'), td = $('#tr-depth'), tres = $('#tr-results');
    var reach = function (start, map, depth) {
      var seen = {}, out = [], frontier = [start];
      for (var d = 0; d < depth; d++) {
        var next = [];
        frontier.forEach(function (id) { map[id].forEach(function (x) { if (!seen[x] && x !== start) { seen[x] = 1; out.push(x); next.push(x); } }); });
        frontier = next;
      }
      return out;
    };
    var btn = function (id, focus) {
      var n = byId[id];
      return '<button type="button" class="tnode k-' + esc(n.kind) + (focus ? ' focus' : '') + '" data-node="' + esc(id) + '" title="' + esc(n.desc) + '"><span>' + esc(n.label.length > 70 ? n.label.slice(0, 68) + '…' : n.label) + '</span><span class="kind">' + esc(KIND[n.kind] || n.kind) + '</span></button>';
    };
    var group = function (ids) {
      var by = {}; ids.forEach(function (id) { var k = byId[id].kind; (by[k] = by[k] || []).push(id); });
      return Object.keys(by).map(function (k) { return '<h3>' + esc(KIND[k] || k) + ' (' + by[k].length + ')</h3>' + by[k].slice(0, 40).map(function (id) { return btn(id); }).join('') + (by[k].length > 40 ? '<p class="small">and ' + (by[k].length - 40) + ' more</p>' : ''); }).join('');
    };
    var draw = function () {
      var old = $('svg.links', trace); if (old) old.remove();
      var f = $('.tnode.focus', trace); if (!f || window.innerWidth < 800) return;
      var tr = trace.getBoundingClientRect(), fr = f.getBoundingClientRect();
      var paths = $$('.col.up .tnode, .col.down .tnode', trace).map(function (b) {
        var r = b.getBoundingClientRect(), isUp = b.closest('.up');
        var x1 = isUp ? r.right - tr.left : fr.right - tr.left, y1 = (isUp ? r.top + r.height / 2 : fr.top + fr.height / 2) - tr.top;
        var x2 = isUp ? fr.left - tr.left : r.left - tr.left, y2 = (isUp ? fr.top + fr.height / 2 : r.top + r.height / 2) - tr.top;
        var mx = (x1 + x2) / 2;
        return '<path data-for="' + esc(b.getAttribute('data-node')) + '" d="M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2 + '"/>';
      }).join('');
      trace.insertAdjacentHTML('afterbegin', '<svg class="links" aria-hidden="true">' + paths + '</svg>');
    };
    var focusOn = function (id, push) {
      if (!byId[id]) return;
      var depth = Number(td.value || 1), u = reach(id, up, depth), d = reach(id, down, depth), n = byId[id];
      trace.innerHTML = '<div class="col up">' + (u.length ? group(u) : '<p class="small">Nothing comes before this.</p>') + '</div>' +
        '<div class="col mid"><h3>Selected</h3>' + btn(id, true) + '<p class="small">' + esc(n.desc) + '</p><p><a href="' + esc(n.href) + '">Open ' + esc((KIND[n.kind] || n.kind).toLowerCase()) + '</a></p></div>' +
        '<div class="col down">' + (d.length ? group(d) : '<p class="small">Nothing depends on this.</p>') + '</div>';
      $('#tr-sum').textContent = n.label + ': ' + u.length + ' before it, ' + d.length + ' after it, ' + depth + ' step' + (depth > 1 ? 's' : '') + ' away.';
      if (push !== false) { try { history.replaceState(null, '', '#n=' + encodeURIComponent(id)); } catch (e) { /* file: */ } }
      setTimeout(draw, 30);
    };
    trace.addEventListener('click', function (e) { var b = e.target.closest('[data-node]'); if (b) { focusOn(b.getAttribute('data-node')); var f = $('.tnode.focus', trace); if (f) f.focus(); } });
    trace.addEventListener('mouseover', function (e) { var b = e.target.closest('[data-node]'); $$('svg.links path', trace).forEach(function (p) { p.classList.toggle('hot', !!b && p.getAttribute('data-for') === b.getAttribute('data-node')); }); });
    var search = function () {
      var q = tq.value.trim().toLowerCase(), k = tk.value;
      if (q.length < 2 && !k) { tres.innerHTML = ''; return; }
      var hits = LG.nodes.filter(function (n) { return (!k || n.kind === k) && (!q || (n.label + ' ' + n.id).toLowerCase().indexOf(q) > -1); }).slice(0, 12);
      tres.innerHTML = hits.map(function (n) { return '<li><button type="button" class="tnode k-' + esc(n.kind) + '" data-pick="' + esc(n.id) + '"><span>' + esc(n.label.slice(0, 90)) + '</span><span class="kind">' + esc(KIND[n.kind] || n.kind) + '</span></button></li>'; }).join('') || '<li class="small">No matches.</li>';
    };
    tq.addEventListener('input', search); tk.addEventListener('change', search);
    td.addEventListener('change', function () { var f = $('.tnode.focus', trace); if (f) focusOn(f.getAttribute('data-node')); });
    tres.addEventListener('click', function (e) { var b = e.target.closest('[data-pick]'); if (b) { focusOn(b.getAttribute('data-pick')); tres.innerHTML = ''; tq.value = ''; } });
    $('#trace-form').addEventListener('submit', function (e) { e.preventDefault(); var b = $('[data-pick]', tres); if (b) b.click(); });
    window.addEventListener('resize', function () { setTimeout(draw, 50); });
    var m = /[#?&]n=([^&]+)/.exec(location.hash + '&' + location.search), start = m ? decodeURIComponent(m[1]) : 'prop:accessRights';
    focusOn(byId[start] ? start : LG.nodes[0].id, false);
  }

  /* ---- standards map: light up a standard's relationships; filter by relationship and group ---------------------------- */
  var smv = $('#std-svg');
  if (smv) {
    var smRel = $('#sm-rel'), smGrp = $('#sm-grp'), smSum = $('#sm-sum');
    var smApply = function (focus) {
      var r = smRel.value, g = smGrp.value, nOn = {};
      $$('.sm-l', smv).forEach(function (l) {
        var a = l.getAttribute('data-a'), b = l.getAttribute('data-b');
        var gA = $('.sm-n[data-id="' + a + '"]', smv).getAttribute('data-g'), gB = $('.sm-n[data-id="' + b + '"]', smv).getAttribute('data-g');
        var on = (!r || l.getAttribute('data-r') === r) && (!g || gA === g || gB === g) && (!focus || a === focus || b === focus);
        l.classList.toggle('off', !on); l.classList.toggle('hot', !!focus && on);
        if (on) { nOn[a] = 1; nOn[b] = 1; }
      });
      $$('.sm-n', smv).forEach(function (n) { n.classList.toggle('dim', (r || g || focus) && !nOn[n.getAttribute('data-id')]); });
      var c = $$('.sm-l:not(.off)', smv).length;
      smSum.textContent = (focus ? $('.sm-n[data-id="' + focus + '"] a', smv).getAttribute('aria-label') + ': ' : '') + c + ' relationship' + (c === 1 ? '' : 's') + ' shown.';
    };
    smRel.addEventListener('change', function () { smApply(); }); smGrp.addEventListener('change', function () { smApply(); });
    $$('.sm-n', smv).forEach(function (n) {
      var id = n.getAttribute('data-id');
      n.addEventListener('mouseenter', function () { smApply(id); }); n.addEventListener('focusin', function () { smApply(id); });
      n.addEventListener('mouseleave', function () { smApply(); });
    });
  }

  /* ---- metadata weaver --------------------------------------------------------------------------------------------------- */
  var wf = $('#weave-form');
  if (wf && P && V) {
    var wFrom = $('#w-from'), wTo = $('#w-to'), wIn = $('#w-in'), wOut = $('#w-out');
    var FAM = { title: 1, description: 1, abstract: 1, keyword: 2, theme: 2, spatial: 3, temporal: 3, publisher: 4, creator: 4, contactPoint: 4, licence: 5, rights: 5, accessRights: 5, distribution: 6, identifier: 7, issued: 8, modified: 8 };
    var ddiXml = function (t) {
      var x = new DOMParser().parseFromString(t, 'application/xml'), o = {};
      ['titl', 'IDNo', 'abstract', 'producer', 'AuthEnty', 'nation', 'geogCover', 'universe', 'restrctn', 'conditions', 'accsPlac', 'version', 'prodDate', 'distDate'].forEach(function (k) {
        var e = x.getElementsByTagName(k); if (e.length) o[k] = e[0].textContent.trim();
      });
      var kw = x.getElementsByTagName('keyword'); if (kw.length) o.keyword = Array.prototype.map.call(kw, function (e) { return e.textContent.trim(); });
      var tp = x.getElementsByTagName('timePrd'); if (tp.length) o.timePrd = { start: tp[0].getAttribute('date') || '', end: tp.length > 1 ? tp[1].getAttribute('date') || '' : '' };
      return o;
    };
    var threads = function (map, leftTitle, rightTitle) {
      var L = map.map(function (m) { return m[0]; }), R = [];
      map.forEach(function (m) { if (m[1] && R.indexOf(m[1]) < 0) R.push(m[1]); });
      var li = function (s, miss) { return '<li' + (miss ? ' class="miss"' : '') + '>' + esc(s) + '</li>'; };
      var html = '<div class="weave" data-w><div><h3 class="h4">' + esc(leftTitle) + '</h3><ul class="wl">' + map.map(function (m) { return li(m[0], !m[1]); }).join('') + '</ul></div>' +
        '<svg aria-hidden="true"></svg><div><h3 class="h4">' + esc(rightTitle) + '</h3><ul class="wr">' + R.map(function (r) { return li(r); }).join('') + '</ul></div></div>';
      return { html: html, map: map, R: R };
    };
    var drawThreads = function (box, map, R) {
      var svg = $('svg', box), ls = $$('.wl li', box), rs = $$('.wr li', box);
      if (!svg || !ls.length || window.innerWidth < 800) return;
      var sb = svg.getBoundingClientRect();
      svg.setAttribute('viewBox', '0 0 ' + sb.width + ' ' + sb.height);
      svg.innerHTML = map.map(function (m, i) {
        if (!m[1]) return '';
        var a = ls[i].getBoundingClientRect(), b = rs[R.indexOf(m[1])].getBoundingClientRect();
        var y1 = a.top + a.height / 2 - sb.top, y2 = b.top + b.height / 2 - sb.top, w = sb.width;
        var key = String(m[1]).replace(/^[a-z]+:/, ''), c = 'd' + (FAM[key] || FAM[m[0]] || ((i % 8) + 1));
        return '<path class="' + c + '" d="M0,' + y1 + ' C' + w / 2 + ',' + y1 + ' ' + w / 2 + ',' + y2 + ' ' + w + ',' + y2 + '"/>';
      }).join('');
    };
    var run = function () {
      var t = wIn.value.trim(), input;
      if (!t) { wOut.innerHTML = '<p>Paste a record, or try the example.</p>'; return; }
      try { input = wFrom.value === 'ddi' && t[0] === '<' ? ddiXml(t) : JSON.parse(t); } catch (e) { wOut.innerHTML = '<div class="panel warning"><h2>The record could not be read</h2><p>' + esc(e.message) + '</p></div>'; return; }
      var w;
      try { w = V.weave(P, wFrom.value, wTo.value, input); } catch (e) { wOut.innerHTML = '<div class="panel warning"><p>' + esc(e.message) + '</p></div>'; return; }
      var carried = w.mapIn.filter(function (m) { return m[1]; }).length;
      var a = threads(w.mapIn, wFrom.options[wFrom.selectedIndex].text, 'DCAT-AP-UK'), b = threads(w.mapOut, 'DCAT-AP-UK', wTo.options[wTo.selectedIndex].text);
      var outText = typeof w.out === 'string' ? w.out : JSON.stringify(w.out, null, 2);
      wOut.innerHTML = '<section class="panel ' + (w.validation.ok ? 'notice' : 'warning') + '"><h2>Woven</h2><p>' + carried + ' of ' + w.mapIn.length + ' source fields carried into DCAT-AP-UK; ' +
        (w.validation.ok ? 'the record conforms.' : w.validation.errors + ' to fix before it conforms.') + '</p>' + levelHtml(V.conformance(P, w.record)) +
        (w.notes.length ? '<h3 class="h4">Notes</h3><ul>' + w.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>' : '') + '</section>' +
        '<h3>Into DCAT-AP-UK</h3>' + a.html + (wTo.value !== 'ukap' ? '<h3>Out to ' + esc(wTo.options[wTo.selectedIndex].text) + '</h3>' + b.html : '') +
        '<details><summary>What to fix (' + w.validation.issues.length + ')</summary><ul class="results">' + w.validation.issues.map(function (i) { return '<li class="' + i.level + '"><strong>' + esc(plabel(i.prop)) + '</strong>: ' + esc(i.text) + ' <span class="small">(' + esc(i.rule) + ')</span></li>'; }).join('') + '</ul></details>' +
        '<h3>Result</h3><pre id="w-res" tabindex="0">' + esc(outText) + '</pre><p class="btns"><button type="button" class="btn small" id="w-dl">Download</button><button type="button" class="btn secondary small" data-copy="w-res">Copy</button></p>';
      var boxes = $$('[data-w]', wOut);
      drawThreads(boxes[0], a.map, a.R); if (boxes[1]) drawThreads(boxes[1], b.map, b.R);
      $('#w-dl').addEventListener('click', function () { download('record.' + (wTo.value === 'turtle' ? 'ttl' : 'json'), outText, wTo.value === 'turtle' ? 'text/turtle' : 'application/json'); });
      announce('Woven: ' + carried + ' fields carried');
    };
    $('#w-run').addEventListener('click', run);
    $('#w-sample').addEventListener('click', function () { var s = $('#w-sample-' + wFrom.value); if (s) { wIn.value = JSON.stringify(JSON.parse(s.textContent), null, 2); run(); } });
  }


  function meters(root) { $$('.meter span[data-w]', root).forEach(function (m) { m.style.width = m.getAttribute('data-w') + '%'; }); }
  function fairHtml(q) {
    return q.dimensions.map(function (d) {
      return '<h3 class="h4">' + esc(d.label) + ' <span class="small">' + d.score + ' of ' + d.max + '</span></h3><div class="meter" aria-hidden="true"><span data-w="' + Math.round(100 * d.score / d.max) + '"></span></div><ul class="results">' +
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
      var sug = (window.UKAP_SUGGEST || {})[x.p];
      if (sug && sug.length) {
        // Standards the Data Standards Authority endorses (reuse page): one press adds the address, on its own line.
        var box = el('div', { 'class': 'suggest', role: 'group', 'aria-label': 'Endorsed standards you can add' });
        box.appendChild(el('span', { 'class': 'small' }, 'Endorsed standards: '));
        sug.forEach(function (s) {
          var b = el('button', { type: 'button', 'class': 'chip', title: s.title, 'data-iri': s.iri }, esc(s.label));
          b.addEventListener('click', function () {
            var cur = input.value.trim(); if (input.tagName !== 'TEXTAREA') input.value = s.iri; else if (cur.split(/\s+/).indexOf(s.iri) < 0) input.value = cur ? cur + '\n' + s.iri : s.iri;
            input.dispatchEvent(new Event('input', { bubbles: true })); input.focus();
          });
          box.appendChild(b);
        });
        w.appendChild(box);
      }
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
      $('#b-jsonld').textContent = JSON.stringify(Object.assign({ '@context': 'https://cyberdudeuk.github.io/dcat-ap-uk/downloads/dcat-ap-uk.context.jsonld' }, rec), null, 2);
      $('#b-ttl').textContent = V.toTurtle(P, rec);
      $('#b-sdo').textContent = JSON.stringify(V.toSchemaOrg(P, rec), null, 2);
      $('#b-cr').textContent = JSON.stringify(V.toCroissant(P, rec), null, 2);
      var q = V.fair(P, rec);
      $('#b-level').innerHTML = levelHtml(V.conformance(P, rec));
      $('#b-fair-s').textContent = q.score + ' of ' + q.max + ' (' + q.rating.toLowerCase() + ')';
      $('#b-fair').innerHTML = fairHtml(q); meters($('#b-fair'));
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
        return '<section class="panel ' + (res.ok ? 'notice' : 'warning') + '"><h3>' + (recs.length > 1 ? 'Record ' + (n + 1) + ': ' : '') + (res.ok ? 'Conforms to DCAT-AP-UK' + (P.applied && P.applied.length ? ' with the ' + esc(P0.extensions[P.applied[0]].label.toLowerCase()) + ' extension' : '') : res.errors + ' to fix') + '</h3>' +
          levelHtml(V.conformance(P, r)) + '<details><summary>Quality score: ' + q.score + ' of ' + q.max + ' (' + esc(q.rating.toLowerCase()) + ')</summary>' + fairHtml(q) + '</details>' +
          (notes.length ? '<p><strong>Converted from the xGov MEM.</strong></p><ul>' + notes.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '') +
          '<ul class="results">' + res.issues.map(function (i) { return '<li class="' + i.level + '"><strong>' + esc(plabel(i.prop)) + '</strong>: ' + esc(i.text) + ' <span class="small">(' + esc(i.rule) + ')</span></li>'; }).join('') + '</ul>' +
          (mode.value === 'mem' ? '<h4>Converted record</h4><pre>' + esc(JSON.stringify(r, null, 2)) + '</pre>' : '') + '</section>';
      }).join('');
      meters(out);
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
      $('#bk-dl-jsonld').addEventListener('click', function () { download('records.jsonld', JSON.stringify({ '@context': 'https://cyberdudeuk.github.io/dcat-ap-uk/downloads/dcat-ap-uk.context.jsonld', '@graph': last }, null, 1), 'application/ld+json'); });
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
