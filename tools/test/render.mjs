import { JSDOM, VirtualConsole } from 'jsdom';
import fs from 'fs';
const dir = '/site';
const lite = fs.readFileSync(dir + '/dc-lite.js', 'utf8');
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.html') && !['index.html', 'list.html'].includes(f))) {
  for (const dark of [0, 1]) {
    const errs = [];
    const vc = new VirtualConsole(); vc.on('error', e => errs.push(String(e))); vc.on('jsdomError', e => errs.push(e.message)); vc.on('warn', e => errs.push(String(e)));
    const html = fs.readFileSync(`${dir}/${f}`, 'utf8').replace('<script src="./dc-lite.js"></script>', () => '<script>' + lite + '</script>');
    const dom = new JSDOM(html, { runScripts: 'dangerously', url: `https://x/${f}?dark=${dark}`, virtualConsole: vc });
    await new Promise(r => setTimeout(r, 50));
    const d = dom.window.document;
    const body = d.body.innerHTML.replace(/<x-dc>[\s\S]*<\/x-dc>/, '').replace(/<script[\s\S]*?<\/script>/g, '');
    const left = (body.match(/\{\{[^}]*\}\}/g) || []).length;
    const root = [...d.body.children].find(e => e.tagName === 'DIV')?.firstElementChild;
    console.log(`${f.padEnd(14)} dark=${dark} rendered=${!!root} class="${root?.className}" leftover{{}}=${left} elements=${root?.querySelectorAll('*').length} styleInHead=${d.head.querySelectorAll('style').length} errors=${errs.length ? errs.join(' | ').slice(0,200) : 0}`);
  }
}
