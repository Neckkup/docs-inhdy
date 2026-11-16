/* dc-lite.js — runtime ขนาดเล็กสำหรับแสดงไฟล์ .dc.html (Claude Design) นอก claude.ai
 * รองรับ: {{path}}, <sc-if>, <sc-for>, class Component extends DCLogic { renderVals() },
 *         data-props defaults (ทับได้ด้วย URL เช่น ?dark=1), onX="{{fn}}", setState
 * ไม่รองรับ: <dc-import>
 */
(function () {
  'use strict';
  var hide = document.createElement('style');
  hide.textContent = 'x-dc{display:none!important}';
  document.head.appendChild(hide);

  var WHOLE = /^\s*\{\{([^}]+)\}\}\s*$/;
  var ANY = /\{\{([^}]+)\}\}/g;
  var tpl, inst, root;

  function DCLogic(props) { this.props = props; this.state = {}; }
  DCLogic.prototype.setState = function (p) {
    Object.assign(this.state, typeof p === 'function' ? p(this.state, this.props) : p);
    render();
  };
  DCLogic.prototype.forceUpdate = function () { render(); };
  window.DCLogic = DCLogic;

  function get(scope, path) {
    path = path.trim();
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (path === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(path)) return +path;
    if (/^(['"]).*\1$/.test(path)) return path.slice(1, -1);
    return path.split('.').reduce(function (o, k) { return o == null ? undefined : o[k]; }, scope);
  }
  function interp(s, scope) {
    return s.replace(ANY, function (_, p) { var v = get(scope, p); return v == null ? '' : String(v); });
  }

  function build(node, scope, out) {
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) {
        out.appendChild(document.createTextNode(n.data.indexOf('{{') >= 0 ? interp(n.data, scope) : n.data));
        return;
      }
      if (n.nodeType !== 1) return;
      var tag = n.localName;
      if (tag === 'helmet') return;
      if (tag === 'sc-if') {
        var c = (n.getAttribute('value') || '').match(WHOLE);
        if (c && get(scope, c[1])) build(n, scope, out);
        return;
      }
      if (tag === 'sc-for') {
        var l = (n.getAttribute('list') || '').match(WHOLE);
        var list = l ? get(scope, l[1]) : null;
        var as = n.getAttribute('as') || 'item';
        (Array.isArray(list) ? list : []).forEach(function (it, i) {
          var s = Object.create(scope); s[as] = it; s.$index = i;
          build(n, s, out);
        });
        return;
      }
      if (tag === 'dc-import') { console.warn('dc-lite: <dc-import> not supported'); return; }

      var el = document.createElementNS(n.namespaceURI, n.localName);
      Array.prototype.forEach.call(n.attributes, function (a) {
        if (a.name.indexOf('hint-') === 0) return;
        var m = a.value.match(WHOLE);
        if (m) {
          var v = get(scope, m[1]);
          if (typeof v === 'function' && a.name.indexOf('on') === 0) { el.addEventListener(a.name.slice(2), v); return; }
          if (v === false || v == null) return;
          el.setAttribute(a.name, v === true ? '' : String(v));
        } else {
          el.setAttribute(a.name, a.value.indexOf('{{') >= 0 ? interp(a.value, scope) : a.value);
        }
      });
      build(n, scope, el);
      out.appendChild(el);
    });
  }

  function render() {
    var vals = inst.renderVals ? inst.renderVals() : {};
    var frag = document.createDocumentFragment();
    build(tpl, vals || {}, frag);
    root.replaceChildren(frag);
  }

  function boot() {
    tpl = document.querySelector('x-dc');
    var script = document.querySelector('script[data-dc-script]');
    if (!tpl) return;
    var helmet = tpl.querySelector('helmet');
    if (helmet) Array.prototype.slice.call(helmet.childNodes).forEach(function (n) { document.head.appendChild(n); });

    var props = {};
    var spec = {};
    try { spec = JSON.parse(script && script.getAttribute('data-props') || '{}'); } catch (e) {}
    Object.keys(spec).forEach(function (k) { if (k[0] !== '$' && 'default' in spec[k]) props[k] = spec[k].default; });
    new URLSearchParams(location.search).forEach(function (v, k) {
      if (!(k in spec)) return;
      var t = spec[k].editor;
      props[k] = t === 'boolean' ? (v === '1' || v === 'true') : (t === 'int' || t === 'float' || t === 'range') ? +v : v;
    });

    var Component = DCLogic;
    if (script) {
      try { Component = new Function('DCLogic', script.textContent + '\n;return Component;')(DCLogic); }
      catch (e) { console.error('dc-lite: logic error', e); }
    }
    inst = new Component(props);
    if (!inst.state) inst.state = {};
    root = document.createElement('div');
    tpl.parentNode.insertBefore(root, tpl);
    render();
    if (inst.componentDidMount) inst.componentDidMount();

    if (window.top === window && spec.dark) nav(props);
  }

  function nav(props) {
    var bar = document.createElement('div');
    bar.setAttribute('style', 'position:fixed;right:16px;bottom:16px;z-index:9999;display:flex;gap:6px;padding:6px;border-radius:999px;background:rgba(20,20,20,.78);backdrop-filter:blur(6px);font:13px/1 system-ui,sans-serif');
    var btn = 'color:#fff;text-decoration:none;padding:8px 12px;border-radius:999px;background:transparent;border:0;cursor:pointer;font:inherit';
    var q = new URLSearchParams(location.search);
    q.set('dark', props.dark ? '0' : '1');
    bar.innerHTML = '<a href="./" style="' + btn + '">← ทั้งหมด</a>' +
      '<a href="?' + q + '" style="' + btn + '">' + (props.dark ? '☀ สว่าง' : '☾ มืด') + '</a>';
    document.body.appendChild(bar);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
