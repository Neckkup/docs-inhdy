/* dc-lite.js — runtime ขนาดเล็กสำหรับแสดงไฟล์ .dc.html (Claude Design) นอก claude.ai
 * รองรับ: {{path}}, <sc-if>, <sc-for>, class Component extends DCLogic { renderVals() },
 *         data-props defaults (ทับได้ด้วย URL เช่น ?dark=1), onX="{{fn}}", setState,
 *         <dc-import name="X" prop="..."> (โหลด X.html แล้ว render เป็น component ย่อย ส่ง props ผ่าน attribute)
 */
(function () {
  'use strict';
  var hide = document.createElement('style');
  hide.textContent = 'x-dc{display:none!important}';
  document.head.appendChild(hide);

  var WHOLE = /^\s*\{\{([^}]+)\}\}\s*$/;
  var ANY = /\{\{([^}]+)\}\}/g;
  var defs = {}; // name -> Promise<def>

  function DCLogic(props) { this.props = props; this.state = {}; }
  DCLogic.prototype.setState = function (p) {
    Object.assign(this.state, typeof p === 'function' ? p(this.state, this.props) : p);
    if (this.__dc) render(this.__dc);
  };
  DCLogic.prototype.forceUpdate = function () { if (this.__dc) render(this.__dc); };
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

  // อ่าน template + logic + props spec จากเอกสาร .dc.html หนึ่งไฟล์
  function parseDef(doc) {
    var tpl = doc.querySelector('x-dc');
    if (!tpl) return null;
    var script = doc.querySelector('script[data-dc-script]');
    var spec = {};
    try { spec = JSON.parse(script && script.getAttribute('data-props') || '{}'); } catch (e) {}
    var Component = DCLogic;
    if (script) {
      try { Component = new Function('DCLogic', script.textContent + '\n;return Component;')(DCLogic); }
      catch (e) { console.error('dc-lite: logic error', e); }
    }
    var helmet = tpl.querySelector('helmet');
    return { tpl: tpl, spec: spec, Component: Component, helmet: helmet ? Array.prototype.slice.call(helmet.childNodes) : [] };
  }

  function defaults(spec) {
    var props = {};
    Object.keys(spec).forEach(function (k) { if (k[0] !== '$' && spec[k] && 'default' in spec[k]) props[k] = spec[k].default; });
    return props;
  }

  function loadDef(name) {
    if (!defs[name]) {
      defs[name] = fetch(name + '.html').then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      }).then(function (text) {
        var def = parseDef(new DOMParser().parseFromString(text, 'text/html'));
        if (!def) throw new Error('no <x-dc> in ' + name + '.html');
        // ฟอนต์/สไตล์ของ component ย่อย — เพิ่มเข้า <head> ครั้งเดียว
        var have = {};
        Array.prototype.forEach.call(document.head.children, function (n) { have[n.outerHTML] = 1; });
        def.helmet.forEach(function (n) {
          if (n.nodeType !== 1 || have[n.outerHTML]) return;
          have[n.outerHTML] = 1;
          document.head.appendChild(document.importNode(n, true));
        });
        return def;
      });
    }
    return defs[name];
  }

  function mount(def, props, host) {
    var inst = new def.Component(props);
    if (!inst.state) inst.state = {};
    if (!inst.props) inst.props = props;
    var ctx = { def: def, inst: inst, root: host, kids: [], k: 0 };
    inst.__dc = ctx;
    render(ctx);
    if (inst.componentDidMount) inst.componentDidMount();
    return ctx;
  }

  function importNode(n, scope, out, ctx) {
    var name = n.getAttribute('name');
    var props = {};
    Array.prototype.forEach.call(n.attributes, function (a) {
      if (a.name === 'name' || a.name.indexOf('hint-') === 0) return;
      var m = a.value.match(WHOLE);
      props[a.name] = m ? get(scope, m[1]) : interp(a.value, scope);
    });
    var i = ctx.k++;
    var kid = ctx.kids[i];
    if (!kid || kid.name !== name) {
      var host = document.createElement('div');
      host.setAttribute('data-dc-import', name);
      host.style.display = 'contents';
      kid = ctx.kids[i] = { name: name, host: host, props: props, ctx: null };
      loadDef(name).then(function (def) {
        kid.ctx = mount(def, Object.assign(defaults(def.spec), kid.props), host);
      }, function (e) { console.error('dc-lite: <dc-import name="' + name + '"> failed: ' + e.message); });
    } else {
      kid.props = props;
      if (kid.ctx) {
        kid.ctx.inst.props = Object.assign(defaults(kid.ctx.def.spec), props);
        render(kid.ctx);
      }
    }
    out.appendChild(kid.host);
  }

  function build(node, scope, out, ctx) {
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
        if (c && get(scope, c[1])) build(n, scope, out, ctx);
        return;
      }
      if (tag === 'sc-for') {
        var l = (n.getAttribute('list') || '').match(WHOLE);
        var list = l ? get(scope, l[1]) : null;
        var as = n.getAttribute('as') || 'item';
        (Array.isArray(list) ? list : []).forEach(function (it, i) {
          var s = Object.create(scope); s[as] = it; s.$index = i;
          build(n, s, out, ctx);
        });
        return;
      }
      if (tag === 'dc-import') { importNode(n, scope, out, ctx); return; }

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
      build(n, scope, el, ctx);
      out.appendChild(el);
    });
  }

  function render(ctx) {
    var vals = ctx.inst.renderVals ? ctx.inst.renderVals() : {};
    var frag = document.createDocumentFragment();
    ctx.k = 0;
    build(ctx.def.tpl, vals || {}, frag, ctx);
    ctx.kids.length = ctx.k;
    ctx.root.replaceChildren(frag);
  }

  function boot() {
    var def = parseDef(document);
    if (!def) return;
    def.helmet.forEach(function (n) { document.head.appendChild(n); });

    var spec = def.spec;
    var props = defaults(spec);
    new URLSearchParams(location.search).forEach(function (v, k) {
      if (!(k in spec)) return;
      var t = spec[k].editor;
      props[k] = t === 'boolean' ? (v === '1' || v === 'true') : (t === 'int' || t === 'float' || t === 'range') ? +v : v;
    });

    var root = document.createElement('div');
    def.tpl.parentNode.insertBefore(root, def.tpl);
    mount(def, props, root);

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
