// ทดสอบ canvas viewer: node canvas.mjs (โฟลเดอร์โปรเจกต์ mount ที่ /site)
import { JSDOM, VirtualConsole } from 'jsdom';
import fs from 'fs';
const errs = []; const vc = new VirtualConsole();
vc.on('error', e => errs.push(String(e))); vc.on('jsdomError', e => errs.push(e.message));
const json = fs.readFileSync('/site/canvas.json', 'utf8');
const hashes = ['', ...(JSON.parse(json).pages || []).slice(1).map(p => '#' + p.id)];
for (const hash of hashes) {
  const dom = new JSDOM(fs.readFileSync('/site/index.html', 'utf8'), {
    runScripts: 'dangerously', url: 'https://x/' + hash, virtualConsole: vc, pretendToBeVisual: true,
    beforeParse(w) { w.fetch = async () => ({ json: async () => JSON.parse(json) }); },
  });
  await new Promise(r => setTimeout(r, 100));
  const d = dom.window.document;
  console.log(`page=${hash || '(first)'} title="${d.title}" tabs=[${[...d.querySelectorAll('#tabs button')].map(t => t.textContent + (t.getAttribute('aria-pressed') === 'true' ? '*' : '')).join(' | ')}]`);
  console.log('  notes:', [...d.querySelectorAll('.note')].map(n => n.textContent).join(', ') || '-');
  for (const b of d.querySelectorAll('.board'))
    console.log(`  board: ${b.querySelector('.lbl').textContent}  ${b.dataset.href} @${b.style.left},${b.style.top} ${b.style.width}x${b.style.height}`);
}
console.log('errors:', errs.length ? errs : 0);
