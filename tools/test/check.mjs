// ตรวจทุกโปรเจกต์ใน sites/ ก่อน deploy (ใช้ใน GitHub Actions) — มีปัญหา = exit 1
//   node tools/test/check.mjs [sites]
// - ชื่อโฟลเดอร์ใช้เป็นซับโดเมนได้ และมี index.html
// - canvas.json อ่านได้ ไฟล์ใน boards มีจริง และ viewer เปิดได้ไม่มี error
// - หน้าที่ใช้ dc-lite.js render ได้ ไม่เหลือ {{…}} และไม่มี error ทั้งโหมดสว่าง/มืด
import { JSDOM, VirtualConsole } from 'jsdom';
import fs from 'fs';
import path from 'path';

const sites = process.argv[2] || 'sites';
const problems = [];
const bad = (p, msg) => { problems.push(`${p}: ${msg}`); console.log(`  ✗ ${msg}`); };
const wait = ms => new Promise(r => setTimeout(r, ms));
const collector = () => {
  const errs = [], vc = new VirtualConsole();
  vc.on('error', e => errs.push(String(e)));
  vc.on('jsdomError', e => errs.push(e.message));
  return { errs, vc };
};

for (const name of fs.readdirSync(sites).sort()) {
  const dir = path.join(sites, name);
  if (name.startsWith('_') || !fs.statSync(dir).isDirectory()) continue;
  console.log(name);
  if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(name)) { bad(name, 'ชื่อต้องเป็น a-z 0-9 และ - เท่านั้น'); continue; }
  if (!fs.existsSync(path.join(dir, 'index.html'))) { bad(name, 'ไม่มี index.html'); continue; }

  // ---- canvas viewer ----
  const cj = path.join(dir, 'canvas.json');
  if (fs.existsSync(cj)) {
    let canvas;
    try { canvas = JSON.parse(fs.readFileSync(cj, 'utf8')); }
    catch (e) { bad(name, `canvas.json อ่านไม่ได้: ${e.message}`); continue; }
    for (const b of canvas.boards || [])
      if (!fs.existsSync(path.join(dir, b.file))) bad(name, `canvas.json อ้างถึง ${b.file} แต่ไม่มีไฟล์`);
    const hashes = ['', ...(canvas.pages || []).slice(1).map(p => '#' + p.id)];
    for (const hash of hashes) {
      const { errs, vc } = collector();
      const dom = new JSDOM(fs.readFileSync(path.join(dir, 'index.html'), 'utf8'), {
        runScripts: 'dangerously', url: 'https://x/' + hash, virtualConsole: vc, pretendToBeVisual: true,
        beforeParse(w) { w.fetch = async () => ({ json: async () => canvas }); },
      });
      await wait(100);
      const n = dom.window.document.querySelectorAll('.board').length;
      dom.window.close();
      if (errs.length) bad(name, `viewer ${hash || '(หน้าแรก)'} มี error: ${errs.join(' | ').slice(0, 300)}`);
      else console.log(`  ✓ viewer ${hash || '(หน้าแรก)'} ${n} board`);
    }
  }

  // ---- หน้า design ที่ใช้ dc-lite.js ----
  const litePath = path.join(dir, 'dc-lite.js');
  if (fs.existsSync(litePath)) {
    const lite = fs.readFileSync(litePath, 'utf8');
    for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.html') && f !== 'index.html')) {
      const src = fs.readFileSync(path.join(dir, f), 'utf8');
      if (!src.includes('dc-lite.js')) continue;
      for (const dark of [0, 1]) {
        const { errs, vc } = collector();
        vc.on('warn', e => errs.push(String(e)));
        const html = src.replace('<script src="./dc-lite.js"></script>', () => '<script>' + lite + '</script>');
        const dom = new JSDOM(html, { runScripts: 'dangerously', url: `https://x/${f}?dark=${dark}`, virtualConsole: vc });
        await wait(50);
        const d = dom.window.document;
        const body = d.body.innerHTML.replace(/<x-dc>[\s\S]*<\/x-dc>/, '').replace(/<script[\s\S]*?<\/script>/g, '');
        const left = (body.match(/\{\{[^}]*\}\}/g) || []).length;
        const rendered = !![...d.body.children].find(e => e.tagName === 'DIV')?.firstElementChild;
        dom.window.close();
        const tag = `${f} ${dark ? 'มืด' : 'สว่าง'}`;
        if (!rendered) bad(name, `${tag}: render ไม่ออก`);
        else if (left) bad(name, `${tag}: เหลือ {{…}} ${left} จุด`);
        else if (errs.length) bad(name, `${tag}: ${errs.join(' | ').slice(0, 300)}`);
        else console.log(`  ✓ ${tag}`);
      }
    }
  }
}

console.log(problems.length ? `\nพบปัญหา ${problems.length} จุด` : '\nผ่านทั้งหมด');
process.exit(problems.length ? 1 : 0);
