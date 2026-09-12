// Chiffre l'annuaire téléphonique des joueurs pour la page Compos journée.
// Usage : node scripts/encrypt_phones.mjs <annuaire.json (local, jamais commité)> <mot de passe sportive>
// Sortie : data/phones.enc.json (PBKDF2-SHA256 200 000 itérations -> AES-256-GCM). Clé = NOM|PRENOM normalisés (A-Z0-9).
import { readFileSync, writeFileSync } from 'node:fs';
import { webcrypto as wc } from 'node:crypto';
const [src, pwd] = process.argv.slice(2);
if (!src || !pwd) { console.error('usage: node scripts/encrypt_phones.mjs <annuaire.json> <mot de passe>'); process.exit(1); }
const nk = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
const raw = JSON.parse(readFileSync(src, 'utf8'));
const phones = {}, extra = {};
for (const [k, v] of Object.entries(raw.phones || {})) { const [n, p] = k.split('|'); phones[nk(n) + '|' + nk(p)] = v; }
for (const [k, v] of Object.entries(raw.extra || {})) { const [n, p] = k.split('|'); extra[nk(n) + '|' + nk(p)] = v; }
const plain = new TextEncoder().encode(JSON.stringify({ phones, extra, built: new Date().toISOString().slice(0, 10) }));
const salt = wc.getRandomValues(new Uint8Array(16)), iv = wc.getRandomValues(new Uint8Array(12));
const base = await wc.subtle.importKey('raw', new TextEncoder().encode(pwd), 'PBKDF2', false, ['deriveKey']);
const key = await wc.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: 200000, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
const ct = new Uint8Array(await wc.subtle.encrypt({ name: 'AES-GCM', iv }, key, plain));
const b64 = u => Buffer.from(u).toString('base64');
writeFileSync('data/phones.enc.json', JSON.stringify({ v: 1, kdf: 'PBKDF2-SHA256/200000', salt: b64(salt), iv: b64(iv), ct: b64(ct), n: Object.keys(phones).length, built: new Date().toISOString().slice(0, 10) }, null, 1));
console.log('data/phones.enc.json écrit ·', Object.keys(phones).length, 'numéros chiffrés');
