const CACHE='sinavveri-v2';
const ASSETS=['/','/index.html','/takvim.html','/assets/style.css'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp));return r;}).catch(()=>caches.match(e.request)));
});

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
