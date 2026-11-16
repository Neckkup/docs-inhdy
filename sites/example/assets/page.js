// ธีม: ?dark=1 (จาก canvas) > ค่าที่ผู้ชมเลือกไว้ > ธีมของระบบ
(function () {
  var q = new URLSearchParams(location.search).get('dark');
  var saved = null;
  try { saved = localStorage.getItem('dc-dark'); } catch (e) {}
  var dark = q != null ? q === '1' : saved != null ? saved === '1' : matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (window.top === window) {
    addEventListener('DOMContentLoaded', function () {
      var a = document.createElement('a');
      a.className = 'back'; a.href = './'; a.textContent = '← canvas';
      document.body.appendChild(a);
    });
  }
})();
