// ตรวจชื่อซับโดเมนสด, ยืนยันก่อนลบ, กรองรายการ, และติดตามสถานะงาน
(() => {
  const $ = id => document.getElementById(id);

  // ---- ตรวจชื่อ
  const name = $('name'), msg = $('name-msg');
  if (name) {
    let t;
    const check = async () => {
      const v = name.value.trim().toLowerCase();
      if (!v) { msg.textContent = 'a-z 0-9 และ -'; msg.className = 'muted'; return; }
      try {
        const r = await (await fetch('/api/name?name=' + encodeURIComponent(v))).json();
        msg.textContent = r.msg;
        msg.className = r.ok ? (r.update ? 'warn-text' : 'ok-text') : 'err-text';
      } catch { /* ออฟไลน์ ปล่อยให้ server ตรวจตอน submit */ }
    };
    name.addEventListener('input', () => {
      name.value = name.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
      clearTimeout(t); t = setTimeout(check, 250);
    });
    if (name.value) check();
  }

  // ---- ยืนยันก่อนลบ
  document.querySelectorAll('form.confirm').forEach(f =>
    f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));

  // ---- กรองรายการเอกสาร
  const filter = $('filter');
  if (filter) filter.addEventListener('input', () => {
    const q = filter.value.trim().toLowerCase();
    document.querySelectorAll('#projects tbody tr').forEach(tr =>
      tr.classList.toggle('hidden', q && !tr.textContent.toLowerCase().includes(q)));
  });

  // ---- สถานะงาน
  const job = $('job');
  if (job) {
    const live = ['queued', 'running', 'approved'];
    if (!live.includes(job.dataset.status)) return;
    const tick = async () => {
      let d;
      try { d = await (await fetch('/api/jobs/' + job.dataset.id)).json(); }
      catch { return setTimeout(tick, 5000); }
      const log = $('log');
      const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
      log.textContent = d.log || 'รอคิว…';
      if (atBottom) log.scrollTop = log.scrollHeight;
      $('status').textContent = d.status; $('status').className = 'st st-' + d.status;
      $('kind').textContent = d.kind || '—';
      if (live.includes(d.status)) setTimeout(tick, 2000);
      else location.reload();   // review/done/failed: ให้ server วาดปุ่มที่ถูกต้อง
    };
    setTimeout(tick, 1500);
  }
})();
