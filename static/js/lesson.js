(() => {
  'use strict';
  const root = document.getElementById('lesson-root'); if (!root) return;
  const lessonId = root.dataset.lessonId, userId = Number(root.dataset.userId);
  const status = document.getElementById('connection-status');
  const errors = document.getElementById('lesson-error');
  const chatBox = document.getElementById('chat-messages');
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
  let socket, state, stopped = false, retry = 1000, connected = false;
  const labels = {scheduled: 'Запланировано', live: 'Идёт занятие', finished: 'Завершено', cancelled: 'Отменено'};
  const send = value => {
    if (socket && socket.readyState === WebSocket.OPEN) { socket.send(JSON.stringify(value)); return true; }
    errors.textContent = 'Соединение потеряно. Дождитесь переподключения.'; errors.hidden = false; return false;
  };
  const appendMessage = msg => {
    if (chatBox.querySelector(`[data-message-id="${Number(msg.id)}"]`)) return;
    const item = document.createElement('div'); item.className = 'chat-message'; item.dataset.messageId = msg.id;
    const author = document.createElement('strong'); author.textContent = msg.author;
    const text = document.createElement('p'); text.textContent = msg.text;
    item.append(author, text); chatBox.append(item);
    while (chatBox.children.length > 100) chatBox.firstChild.remove();
    chatBox.scrollTop = chatBox.scrollHeight;
  };
  const enableControls = () => {
    if (!state) return;
    const live = state.status === 'live';
    for (const id of ['chat-input', 'chat-send', 'hand-button']) {
      const item = document.getElementById(id); if (item) item.disabled = !live || !connected;
    }
  };
  const render = data => {
    state = data;
    const badge = document.getElementById('lesson-status'); badge.textContent = labels[data.status]; badge.className = `badge ${data.status}`;
    for (const [id, visible] of [['start-form', data.status === 'scheduled'], ['cancel-form', data.status === 'scheduled'], ['finish-form', data.status === 'live'], ['new-poll', data.status === 'live']]) {
      const item = document.getElementById(id); if (item) item.hidden = !visible;
    }
    const hands = document.getElementById('hands'); hands.replaceChildren();
    for (const hand of data.hands) { const p = document.createElement('p'); p.textContent = `✋ ${hand.name}`; hands.append(p); }
    if (!data.hands.length) { const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Пока никто не поднял руку.'; hands.append(p); }
    const handButton = document.getElementById('hand-button');
    if (handButton) handButton.textContent = data.hands.some(h => h.id === userId) ? 'Опустить руку' : '✋ Поднять руку';
    document.querySelectorAll('[data-presence]').forEach(el => { el.textContent = data.online_ids.includes(Number(el.dataset.presence)) ? '● На занятии' : '—'; });
    const oldIds = [...chatBox.children].map(el => Number(el.dataset.messageId));
    const newIds = data.messages.map(m => m.id);
    if (oldIds.join(',') !== newIds.join(',')) { chatBox.replaceChildren(); data.messages.forEach(appendMessage); }
    const polls = document.getElementById('polls'); polls.replaceChildren();
    for (const poll of data.polls) {
      const card = document.createElement('div'); card.className = 'poll';
      const title = document.createElement('h3'); title.textContent = poll.question; card.append(title);
      for (const option of poll.options) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'poll-option';
        button.textContent = option.text + (data.teacher ? ` — ${option.count}` : '');
        button.disabled = !poll.active || poll.voted || data.teacher || !connected;
        button.onclick = () => send({action: 'vote', poll: poll.id, option: option.id}); card.append(button);
      }
      const hint = document.createElement('small'); hint.textContent = !poll.active ? 'Опрос завершён' : poll.voted ? 'Ваш ответ принят' : data.teacher ? 'Результаты обновляются автоматически' : 'Выберите один ответ'; card.append(hint);
      if (data.teacher && poll.active) {
        const form = document.createElement('form'); form.method = 'post'; form.action = `/lessons/${lessonId}/polls/${poll.id}/close/`;
        const token = document.createElement('input'); token.type = 'hidden'; token.name = 'csrfmiddlewaretoken'; token.value = csrf;
        const button = document.createElement('button'); button.textContent = 'Завершить опрос'; button.className = 'secondary'; form.append(token, button); card.append(form);
      }
      polls.append(card);
    }
    if (!data.polls.length) { const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Здесь появится вопрос преподавателя.'; polls.append(p); }
    enableControls();
  };
  render(JSON.parse(document.getElementById('initial-state').textContent));
  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/lessons/${lessonId}/`);
    socket.onopen = () => { connected = true; retry = 1000; status.textContent = '● Соединение установлено'; errors.hidden = true; enableControls(); };
    socket.onmessage = e => {
      let data; try { data = JSON.parse(e.data); } catch { return; }
      if (data.event === 'state') render(data);
      else if (data.event === 'chat.message') appendMessage(data);
      else if (data.event === 'error') { errors.textContent = data.text; errors.hidden = false; }
      else if (data.event !== 'heartbeat.ok') {
        if (data.event === 'lesson.state_changed') send({action: 'heartbeat'});
        send({action: 'state'});
      }
    };
    socket.onclose = e => {
      connected = false; enableControls();
      if ([4401, 4403].includes(e.code)) { stopped = true; status.textContent = 'Доступ закрыт. Обновите страницу.'; }
      else { status.textContent = 'Соединение потеряно. Переподключаемся…'; if (!stopped) { setTimeout(connect, retry); retry = Math.min(retry * 2, 30000); } }
    };
  };
  document.getElementById('chat-form').addEventListener('submit', e => {
    e.preventDefault(); const input = document.getElementById('chat-input');
    if (input.value.trim() && send({action: 'chat', text: input.value})) input.value = '';
  });
  const handButton = document.getElementById('hand-button');
  if (handButton) handButton.onclick = () => send({action: 'hand', raised: !state.hands.some(h => h.id === userId)});
  connect();
  const timer = setInterval(() => { if (connected) { send({action: 'heartbeat'}); send({action: 'state'}); } }, 30000);
  window.addEventListener('pagehide', () => { stopped = true; clearInterval(timer); if (socket) socket.close(); });
})();
