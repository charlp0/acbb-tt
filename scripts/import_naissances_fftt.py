#!/usr/bin/env python3
"""
ACBB TT — réimport des dates de naissance depuis l'EXPORT FFTT (source de vérité).

Le fichier d'inscription Assoconnect avait ~25 % de dates décalées d'un jour. L'export FFTT
(« Licences-ACBB-...csv », séparateur « ; », colonnes « N° Licence » et « Date naissance »)
porte la date officielle de la licence, celle que le joueur saisit. On la hache
(sha256(ACBB_PEPPER:licence:AAAA-MM-JJ)) et on upsert dans `naissances` (source='fichier'),
uniquement pour les licences de l'effectif (`licences_valides`). La date n'est jamais stockée en clair.

Usage : python3 scripts/import_naissances_fftt.py --csv CHEMIN [--dry-run]
Secrets : ~/Documents/Claude/Context/.secrets.env (SUPA_SERVICE_KEY, ACBB_PEPPER).
"""
import argparse, csv, datetime as dt, hashlib, json, os, sys, urllib.request

SB_URL = "https://vhhmageufrcenruywawg.supabase.co"
SECRETS = os.path.expanduser("~/Documents/Claude/Context/.secrets.env")

def charger_secrets(path):
    if not os.path.isfile(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def http(url, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req) as r: return r.status, (r.read().decode() or "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    charger_secrets(SECRETS)
    pepper = os.environ.get("ACBB_PEPPER", ""); key = os.environ.get("SUPA_SERVICE_KEY", "")
    if len(pepper) < 16: sys.exit("ACBB_PEPPER absent/trop court")
    if not key: sys.exit("SUPA_SERVICE_KEY absent")
    H = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # effectif
    _, body = http(f"{SB_URL}/rest/v1/licences_valides?select=licence&limit=3000", headers=H)
    lv = {str(r["licence"]) for r in json.loads(body)}
    # hachés déjà en base (pour compter les changements)
    _, body = http(f"{SB_URL}/rest/v1/naissances?select=licence,hash,source&limit=3000", headers=H)
    stored = {str(r["licence"]): r for r in json.loads(body)}

    lignes, hors_effectif, illisibles = [], 0, []
    seen = set()
    with open(args.csv, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            lic = (r.get("N° Licence") or "").strip()
            d = (r.get("Date naissance") or "").strip()
            if not lic or lic in seen: continue
            if lic not in lv: hors_effectif += 1; continue
            try: iso = dt.datetime.strptime(d, "%d/%m/%Y").date().isoformat()
            except ValueError: illisibles.append((lic, d)); continue
            seen.add(lic)
            h = hashlib.sha256(f"{pepper}:{lic}:{iso}".encode()).hexdigest()
            lignes.append({"licence": lic, "hash": h, "source": "fichier",
                           "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()})

    nouveaux = sum(1 for l in lignes if l["licence"] not in stored)
    inchanges = sum(1 for l in lignes if stored.get(l["licence"], {}).get("hash") == l["hash"])
    corriges = len(lignes) - nouveaux - inchanges
    manquantes = sorted(lv - seen)
    print(f"CSV : {len(lignes)} licences de l'effectif avec date · hors effectif ignorées : {hors_effectif} · illisibles : {len(illisibles)}")
    print(f"  → nouveaux : {nouveaux} · corrigés (date changée) : {corriges} · inchangés : {inchanges}")
    print(f"  effectif sans date dans ce CSV : {len(manquantes)} {manquantes[:12]}")
    if illisibles: print("  illisibles :", illisibles[:8])
    if args.dry_run:
        print("\n[dry-run] rien écrit."); return

    # upsert par lots (merge-duplicates sur la PK licence)
    Hup = dict(H); Hup["Prefer"] = "resolution=merge-duplicates,return=minimal"
    n = 0
    for i in range(0, len(lignes), 200):
        lot = lignes[i:i+200]
        st, resp = http(f"{SB_URL}/rest/v1/naissances", "POST", lot, Hup)
        if st not in (200, 201, 204): sys.exit(f"échec upsert lot {i}: HTTP {st} {resp[:300]}")
        n += len(lot)
    print(f"\n✅ {n} dates upsertées (source='fichier').")

if __name__ == "__main__":
    main()
