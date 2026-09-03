/* ACBB TT — service worker minimal : rend le site installable, sans mise en cache (toujours la version en ligne). */
self.addEventListener('install',function(e){ self.skipWaiting(); });
self.addEventListener('activate',function(e){ e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch',function(e){ /* passthrough : le navigateur gère normalement */ });
