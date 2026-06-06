/* つぎいつ？ — 通知用 Service Worker（ローカル通知＋Web Push） */
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

/* サーバーからのプッシュ（アプリを閉じていても届く。「そろそろ予定日」のお知らせ） */
self.addEventListener('push', e => {
  let title = '⏰ つぎいつ？', body = '';
  try { const d = e.data ? e.data.json() : {}; title = d.title || title; body = d.body || ''; }
  catch (_) { body = e.data ? e.data.text() : ''; }
  e.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: 'icons/icon-tsugi.png',
      badge: 'icons/icon-tsugi.png',
      tag: 'tsugi-due',
      renotify: true
    })
  );
});

/* 通知をタップしたらアプリを前面に */
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes('tsugi.html') && 'focus' in c) return c.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow('./tsugi.html');
    })
  );
});
