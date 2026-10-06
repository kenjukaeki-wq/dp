(() => {
  'use strict';
  window.eduToast = (text, url) => {
    const box = document.createElement('div'); box.className = 'toast';
    const message = document.createElement('div'); message.textContent = text; box.append(message);
    if (url && url.startsWith('/') && !url.startsWith('//')) {
      const link = document.createElement('a'); link.href = url; link.textContent = 'Открыть →'; box.append(link);
    }
    document.getElementById('toasts').append(box); setTimeout(() => box.remove(), 12000);
  };
  if (document.body.dataset.authenticated !== '1') return;
  let stopped = false, retry = 1000, socket;
  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/notifications/`);
    socket.onopen = () => { retry = 1000; };
    socket.onmessage = e => {
      let data; try { data = JSON.parse(e.data); } catch { return; }
      if (data.event === 'notification.created') {
        const counter = document.getElementById('notification-count');
        counter.textContent = Number(counter.textContent || 0) + 1;
        window.eduToast(data.text, data.url);
      }
    };
    socket.onclose = e => {
      if ([4401, 4403].includes(e.code)) stopped = true;
      if (!stopped) { setTimeout(connect, retry); retry = Math.min(30000, retry * 2); }
    };
  };
  connect();
  window.addEventListener('pagehide', () => { stopped = true; if (socket) socket.close(); });
})();
