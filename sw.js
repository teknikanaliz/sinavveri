// Service Worker — SinavVeri.com PWA (kanonik şablon: servermimari/assets/sw-template.js)
// Strateji: HTML network-first (offline'da cache), assets cache-first
// Offline fallback: /offline.html
const CACHE = 'sinavveri-v3';
const OFFLINE_URL = '/offline.html';

// Install: offline sayfasını ve kritik asset'leri precache et
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache =>
      cache.addAll([
        OFFLINE_URL,
        '/manifest.json',
      ])
    )
  );
  self.skipWaiting();
});

// Activate: eski cache'leri temizle
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: akıllı cache stratejisi
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);

  // Sadece kendi domain'imiz
  if (url.origin !== self.location.origin) return;

  const isAsset = /\.(png|jpe?g|svg|gif|webp|ico|woff2?|css|js)$/i.test(url.pathname);
  const isHTML = e.request.headers.get('accept')?.includes('text/html') ||
                 url.pathname.endsWith('/') ||
                 url.pathname.endsWith('.html');

  if (isAsset) {
    // Cache-first: asset'ler (logo, CSS, JS)
    e.respondWith(
      caches.match(e.request).then(cached => {
        if (cached) return cached;
        return fetch(e.request).then(resp => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return resp;
        }).catch(() => new Response('', { status: 404 }));
      })
    );
  } else if (isHTML) {
    // Network-first + offline fallback: HTML sayfaları
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() =>
        // Offline: önce cache'den dene, yoksa fallback sayfası
        caches.match(e.request).then(cached =>
          cached || caches.match(OFFLINE_URL)
        )
      )
    );
  } else {
    // Diğer (JSON vb.): network-first, cache fallback
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match(e.request))
    );
  }
});

// --- Korunan push bildirim handler'ları (siteye özel, standart dışı değil) ---
// Push bildirimi — sınav sonucu açıklandığında push-server (server.js) tetikler.
self.addEventListener('push',e=>{
  var data={}; try{ data=e.data?e.data.json():{}; }catch(err){}
  var title=data.title||'SınavVeri';
  var opts={
    body: data.body||'',
    icon: '/assets/brand/sinavveri-icon.png',
    badge: '/assets/brand/sinavveri-icon.png',
    data: { url: data.url||'/' },
    tag: data.tag||'sinavveri-duyuru'
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();
  var url=(e.notification.data&&e.notification.data.url)||'/';
  e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(function(list){
    for(var i=0;i<list.length;i++){ if(list[i].url.indexOf(url)>=0 && 'focus' in list[i]) return list[i].focus(); }
    if(clients.openWindow) return clients.openWindow(url);
  }));
});
