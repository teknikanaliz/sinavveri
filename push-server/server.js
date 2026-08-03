/**
 * Push subscription endpoint + bildirim gönderici — SınavVeri.com
 * Port 3032'de çalışır (3030=resmitatilveri, 3031=ozelgunlerveri kullanıyor — çakışma yok),
 * nginx /api/push proxy yapacak.
 *
 * NEDEN: ÖSYM sınav sonucu açıkladığında (fetch_osym_duyuru.py cron'u tespit eder) aboneye
 * anında bildirim gitsin. Tek konu (topic) var — sınav bazlı abonelik YOK (kapsam dışı
 * bırakıldı, v1 basit tutuldu); "sınav sonucu açıklandı" bildirimlerinin tamamına abone olma/
 * olmama tercihi yeterli.
 *
 * Desen: OzelGunlerVeri.com/push-server/server.js ile AYNI (kanonik TrVeri push deseni).
 */
require('dotenv').config({ path: require('path').join(__dirname, '.env') });
const express = require('express');
const cors = require('cors');
const webpush = require('web-push');
const Database = require('better-sqlite3');
const path = require('path');

const PORT = process.env.PORT || 3032;
const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'subscriptions.db');

const VAPID_PUBLIC = process.env.VAPID_PUBLIC_KEY;
const VAPID_PRIVATE = process.env.VAPID_PRIVATE_KEY;
const VAPID_SUBJECT = process.env.VAPID_SUBJECT || 'mailto:info@sinavveri.com';

if (!VAPID_PUBLIC || !VAPID_PRIVATE) {
  console.error('❌ VAPID anahtarları yok. ecosystem.config.js / .env eksik.');
  process.exit(1);
}

webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC, VAPID_PRIVATE);

const db = new Database(DB_PATH);
db.exec(`
  CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    user_agent TEXT,
    created_at INTEGER DEFAULT (unixepoch()),
    last_sent INTEGER
  );
`);
// Aynı duyuru URL'i iki kez bildirim OLARAK gönderilmesin (fetch_osym_duyuru.py birden çok
// kez aynı yeni-duyuru satırını göndermeye çalışırsa — idempotentlik sunucu tarafında da garanti).
db.exec(`
  CREATE TABLE IF NOT EXISTS sent_log (
    duyuru_url TEXT PRIMARY KEY,
    sent_at INTEGER DEFAULT (unixepoch())
  );
`);

const app = express();
app.use(cors({ origin: ['https://sinavveri.com', 'http://localhost:3000', 'http://localhost:8791'] }));
app.use(express.json({ limit: '10kb' }));

app.get('/api/push/health', (req, res) => {
  const count = db.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n;
  res.json({ ok: true, subscriber_count: count, vapid_public: VAPID_PUBLIC });
});

app.get('/api/push/vapid-public-key', (req, res) => {
  res.json({ key: VAPID_PUBLIC });
});

app.post('/api/push/subscribe', (req, res) => {
  const { endpoint, keys } = req.body || {};
  if (!endpoint || !keys?.p256dh || !keys?.auth) {
    return res.status(400).json({ error: 'Geçersiz subscription' });
  }
  const ua = req.headers['user-agent'] || 'unknown';
  try {
    db.prepare(`
      INSERT OR REPLACE INTO subscriptions (endpoint, p256dh, auth, user_agent, created_at)
      VALUES (?, ?, ?, ?, unixepoch())
    `).run(endpoint, keys.p256dh, keys.auth, ua);
    const count = db.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n;
    console.log(`[${new Date().toISOString()}] ✓ Yeni abone (toplam ${count})`);
    res.json({ ok: true });
  } catch (e) {
    console.error('Subscribe hata:', e.message);
    res.status(500).json({ error: 'DB hatası' });
  }
});

app.post('/api/push/unsubscribe', (req, res) => {
  const { endpoint } = req.body || {};
  if (!endpoint) return res.status(400).json({ error: 'Endpoint gerek' });
  const result = db.prepare('DELETE FROM subscriptions WHERE endpoint = ?').run(endpoint);
  res.json({ ok: true, deleted: result.changes });
});

function broadcast(payload) {
  const subs = db.prepare('SELECT endpoint, p256dh, auth FROM subscriptions').all();
  const body = JSON.stringify(payload);
  let sent = 0, failed = 0;
  return Promise.all(subs.map(s =>
    webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, body)
      .then(() => { sent++; })
      .catch(err => {
        failed++;
        if (err.statusCode === 410 || err.statusCode === 404) {
          db.prepare('DELETE FROM subscriptions WHERE endpoint = ?').run(s.endpoint);
        }
      })
  )).then(() => ({ sent, failed, total: subs.length }));
}

// Manuel test bildirim (admin) — OzelGunlerVeri ile aynı desen.
app.post('/api/push/send-test', (req, res) => {
  const { secret, title, body, url } = req.body || {};
  if (secret !== process.env.ADMIN_SECRET) return res.status(403).json({ error: 'Yetki yok' });
  broadcast({ title: title || 'SınavVeri Test', body: body || 'Test bildirimi.', url: url || '/' })
    .then(r => res.json({ ok: true, ...r }));
});

// fetch_osym_duyuru.py bu uca POST atar: yeni "sonuc_aciklandi" duyurusu bulununca.
// `duyuru_url` ile idempotent — aynı duyuru iki kez tetiklerse ikinci bildirim SESSİZCE atlanır.
app.post('/api/push/sonuc-aciklandi', (req, res) => {
  const { secret, sinav, baslik, duyuru_url } = req.body || {};
  if (secret !== process.env.ADMIN_SECRET) return res.status(403).json({ error: 'Yetki yok' });
  if (!sinav || !baslik || !duyuru_url) return res.status(400).json({ error: 'sinav/baslik/duyuru_url gerekli' });

  const already = db.prepare('SELECT 1 FROM sent_log WHERE duyuru_url = ?').get(duyuru_url);
  if (already) return res.json({ ok: true, skipped: 'zaten gönderilmiş', sent: 0 });

  broadcast({
    title: `📢 ${sinav} Sonuçları Açıklandı`,
    body: baslik,
    url: '/duyurular.html',
  }).then(r => {
    db.prepare('INSERT OR IGNORE INTO sent_log (duyuru_url) VALUES (?)').run(duyuru_url);
    console.log(`[${new Date().toISOString()}] ✓ "${sinav}" bildirimi: ${r.sent}/${r.total} gönderildi`);
    res.json({ ok: true, ...r });
  });
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`🔔 SınavVeri push server hazır: http://127.0.0.1:${PORT}`);
});
