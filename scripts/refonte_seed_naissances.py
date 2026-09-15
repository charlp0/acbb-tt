#!/usr/bin/env python3
"""
ACBB TT — refonte 2026/27 : seed des dates de naissance hachées (table `naissances`).

Lit le fichier des inscriptions (xlsx, onglet « 2026-2027 » : Nom, Prénom, Naissance, [LIC]),
apparie chaque ligne à une licence de l'effectif (https://team.acbb-tt.fr/data/scoring.json :
colonne LIC si présente, sinon nom/prénom normalisés sans accents ni casse, prénom composé
ou partiel toléré), calcule

    hash = sha256(ACBB_PEPPER + ':' + licence + ':' + 'AAAA-MM-JJ')

(même formule que la fonction Edge `api`) et upsert dans `naissances` (source='fichier')
via PostgREST avec la clé service (`Prefer: resolution=merge-duplicates`). Le fichier fait
foi : il remplace une éventuelle première saisie du joueur (source='saisie').

La date de naissance n'est JAMAIS stockée ni affichée en clair.

Usage :
  python3 scripts/refonte_seed_naissances.py [--dry-run] [--xlsx CHEMIN] [--sheet NOM] [--verbose]

Secrets : ~/Documents/Claude/Context/.secrets.env (SUPA_SERVICE_KEY, ACBB_PEPPER) —
ou variables d'environnement du même nom (prioritaires).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter

SB_URL = "https://vhhmageufrcenruywawg.supabase.co"
DATA_URL = "https://team.acbb-tt.fr/data"
DEFAULT_XLSX = os.path.expanduser("~/Downloads/Inscriptions compétiteurs 11.09.26.xlsx")
DEFAULT_SHEET = "2026-2027"
SECRETS = os.path.expanduser("~/Documents/Claude/Context/.secrets.env")


# ────────────────────────────── utilitaires ──────────────────────────────────
def charger_secrets(path: str) -> None:
    """Charge KEY=VALUE depuis .secrets.env sans écraser les variables déjà présentes."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            if ligne.startswith("export "):
                ligne = ligne[7:]
            k, v = ligne.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)


def norm(s) -> str:
    """Majuscules, sans accents, ponctuation → espace, espaces compactés."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).upper().strip()
    return re.sub(r"\s+", " ", s)


def tokens(s) -> list:
    return norm(s).split()


def proche(a: str, b: str) -> bool:
    """Coquille tolérée : distance de Damerau-Levenshtein ≤ 1 (« MEHDI » ~ « MEDHI »), jetons ≥ 4 lettres."""
    if len(a) < 4 or len(b) < 4:
        return False
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    court, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == court for i in range(len(long_)))


def prenom_compatible(a, b) -> bool:
    """« Jean-Pierre » ~ « Jean », « J.P. » ~ « Jean Pierre » (jeton commun, préfixe ≥ 3 lettres, coquille)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    for x in ta:
        for y in tb:
            if x == y or proche(x, y):
                return True
            if len(x) >= 3 and len(y) >= 3 and (x.startswith(y) or y.startswith(x)):
                return True
    return False


def to_date(v):
    """Cellule Excel → date, ou None. Accepte datetime/date, 'JJ/MM/AAAA', 'AAAA-MM-JJ'."""
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt).date()
        except ValueError:
            pass
    return None


def http_json(url: str, method: str = "GET", body=None, headers=None, timeout: int = 60):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw.strip() else None)


# ─────────────────────────────── lecture xlsx ────────────────────────────────
def lire_xlsx(path: str, sheet: str):
    try:
        import openpyxl  # noqa: WPS433 (dépendance optionnelle, présente sur le poste)
    except ImportError:
        sys.exit("openpyxl manquant : pip3 install openpyxl")
    if not os.path.isfile(path):
        sys.exit(f"Fichier introuvable : {path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        sys.exit(f"Onglet « {sheet} » absent ; onglets disponibles : {wb.sheetnames}")
    ws = wb[sheet]

    rows = []
    col = None
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = [c for c in r]
        if col is None:
            # Ligne d'en-tête : celle qui contient Nom + Prénom
            heads = {norm(c): idx for idx, c in enumerate(cells) if c is not None}
            if "NOM" in heads and "PRENOM" in heads:
                col = {
                    "nom": heads["NOM"],
                    "prenom": heads["PRENOM"],
                    "naissance": next((idx for k, idx in heads.items() if k.startswith("NAISS") or k in ("DATE DE NAISSANCE", "DDN", "NE LE")), None),
                    "lic": next((idx for k, idx in heads.items() if k in ("LIC", "LICENCE", "N LICENCE", "NO LICENCE", "NUM LICENCE")), None),
                }
                if col["naissance"] is None:
                    sys.exit(f"Colonne « Naissance » introuvable dans l'en-tête (ligne {i}) : {list(heads)}")
            continue

        def cell(k):
            idx = col.get(k)
            return cells[idx] if idx is not None and idx < len(cells) else None

        nom, prenom = cell("nom"), cell("prenom")
        if not nom and not prenom:
            continue  # ligne vide
        lic = cell("lic")
        if isinstance(lic, float) and lic.is_integer():
            lic = int(lic)
        lic = str(lic).strip() if lic not in (None, "") else None
        rows.append({"ligne": i, "nom": str(nom or "").strip(), "prenom": str(prenom or "").strip(),
                     "naissance": to_date(cell("naissance")), "lic": lic})
    if col is None:
        sys.exit("En-tête (Nom / Prénom) introuvable dans l'onglet")
    return rows


# ─────────────────────────────── appariement ─────────────────────────────────
class Effectif:
    def __init__(self, players):
        self.by_lic, self.by_lic_nz, self.by_full, self.by_nom = {}, {}, {}, {}
        for p in players:
            lic = str(p.get("lic") or "").strip()
            if not lic:
                continue  # joueurs sans licence : pas d'entrée possible par licence
            p = {"lic": lic, "nom": str(p.get("nom") or ""), "pre": str(p.get("pre") or "")}
            self.by_lic[lic] = p
            self.by_lic_nz.setdefault(lic.lstrip("0"), p)
            self.by_full.setdefault(f"{norm(p['nom'])}|{norm(p['pre'])}", []).append(p)
            self.by_nom.setdefault(norm(p["nom"]), []).append(p)

    def apparier(self, row, noms_fichier=None):
        """→ (joueur, méthode) ou (None, raison). noms_fichier : Counter des noms normalisés du fichier."""
        # 1) Numéro de licence du fichier s'il y en a un (≥ 5 chiffres ; dans le fichier 11.09.26 la
        #    colonne « LIC » est un simple drapeau 0/1 → ignorée). Tolère les zéros de tête perdus par Excel.
        if row["lic"] and re.fullmatch(r"\d{5,}", row["lic"]):
            p = self.by_lic.get(row["lic"]) or self.by_lic_nz.get(row["lic"].lstrip("0"))
            if p:
                return p, "lic"
        n, pr = norm(row["nom"]), norm(row["prenom"])
        # 2) Nom + prénom exacts
        c = self.by_full.get(f"{n}|{pr}", [])
        if len(c) == 1:
            return c[0], "nom+prenom"
        # 3) Nom exact, prénom composé/partiel/coquille
        c = [p for p in self.by_nom.get(n, []) if prenom_compatible(row["prenom"], p["pre"])]
        if len(c) == 1:
            return c[0], "prenom~"
        if len(c) > 1:
            return None, "ambigu (" + ", ".join(f"{p['pre']} {p['lic']}" for p in c) + ")"
        # 3b) Nom de famille unique des deux côtés (effectif ET fichier) : on apparie mais on signale
        c = self.by_nom.get(n, [])
        if len(c) == 1 and noms_fichier is not None and noms_fichier.get(n, 0) == 1 and pr:
            return c[0], "nom-unique"
        # 4) Colonnes Nom/Prénom inversées dans le fichier
        c = [p for p in self.by_nom.get(pr, []) if prenom_compatible(row["nom"], p["pre"])]
        if len(c) == 1:
            return c[0], "inverse"
        # 5) Nom composé (« DUPONT MARTIN » vs « DUPONT ») + prénom compatible
        c = [p for k, ps in self.by_nom.items() if k and (k in n or n in k) for p in ps
             if prenom_compatible(row["prenom"], p["pre"])]
        if len(c) == 1:
            return c[0], "nom~"
        return None, "aucune licence trouvée"


# ────────────────────────────────── main ─────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Seed des dates de naissance hachées (naissances, source=fichier)")
    ap.add_argument("--xlsx", default=DEFAULT_XLSX)
    ap.add_argument("--sheet", default=DEFAULT_SHEET)
    ap.add_argument("--dry-run", action="store_true", help="calcule et affiche, n'écrit rien")
    ap.add_argument("--verbose", action="store_true", help="détaille chaque appariement")
    ap.add_argument("--nom-unique", action="store_true",
                    help="accepte aussi les appariements sur le seul nom de famille (prénoms différents) — à n'utiliser qu'après contrôle")
    args = ap.parse_args()

    charger_secrets(SECRETS)
    pepper = os.environ.get("ACBB_PEPPER", "")
    key = os.environ.get("SUPA_SERVICE_KEY", "")
    if len(pepper) < 16:
        sys.exit(f"ACBB_PEPPER absent ou trop court (dans {SECRETS} ou l'environnement)")
    if not key and not args.dry_run:
        sys.exit(f"SUPA_SERVICE_KEY absent (dans {SECRETS} ou l'environnement)")

    print(f"Fichier : {args.xlsx} · onglet « {args.sheet} »")
    rows = lire_xlsx(args.xlsx, args.sheet)
    print(f"Lignes lues : {len(rows)}")

    # Effectif (public) + licences connues de la fonction
    try:
        _, scoring = http_json(f"{DATA_URL}/scoring.json")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        sys.exit(f"scoring.json indisponible : {e}")
    eff = Effectif(scoring.get("players", []))
    print(f"Effectif scoring.json : {len(eff.by_lic)} licences")

    licences_valides = None
    if key:
        try:
            _, lv = http_json(f"{SB_URL}/rest/v1/licences_valides?select=licence&limit=2000",
                              headers={"apikey": key, "Authorization": f"Bearer {key}"})
            licences_valides = {str(r["licence"]) for r in (lv or [])}
            print(f"licences_valides : {len(licences_valides)} licences")
        except (urllib.error.URLError, KeyError, TypeError) as e:
            print(f"⚠️  licences_valides illisible ({e}) — contrôle d'existence ignoré")

    apparies, sans_date, non_apparies, conflits = [], [], [], []
    par_methode = {}
    vus = {}  # licence → date (détecte les doublons contradictoires)
    noms_fichier = Counter(norm(r["nom"]) for r in rows)
    for row in rows:
        libelle = f"{row['nom']} {row['prenom']} (ligne {row['ligne']})"
        p, methode = eff.apparier(row, noms_fichier)
        if not p:
            non_apparies.append(f"{libelle} — {methode}")
            continue
        if methode == "nom-unique" and not args.nom_unique:
            # Prénoms différents : souvent un parent/enfant hors effectif → un faux positif écrirait un
            # mauvais haché pour un vrai joueur. On ne l'écrit pas sans --nom-unique.
            non_apparies.append(f"{libelle} — seul le nom de famille correspond à {p['nom']} {p['pre']} [{p['lic']}] (non écrit ; --nom-unique pour forcer)")
            continue
        if methode == "nom-unique":
            conflits.append(f"{libelle} → {p['nom']} {p['pre']} [{p['lic']}] apparié sur le seul nom de famille (--nom-unique) : à confirmer")
        if row["naissance"] is None:
            sans_date.append(f"{libelle} → {p['lic']}")
            continue
        iso = row["naissance"].isoformat()
        if p["lic"] in vus:
            if vus[p["lic"]] != iso:
                conflits.append(f"{libelle} → {p['lic']} : date différente d'une ligne précédente (première conservée)")
            continue
        vus[p["lic"]] = iso
        par_methode[methode] = par_methode.get(methode, 0) + 1
        if licences_valides is not None and p["lic"] not in licences_valides:
            conflits.append(f"{libelle} → {p['lic']} absente de licences_valides (le joueur ne pourra pas entrer)")
        h = hashlib.sha256(f"{pepper}:{p['lic']}:{iso}".encode("utf-8")).hexdigest()
        apparies.append({"licence": p["lic"], "hash": h, "source": "fichier",
                         "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        if args.verbose:
            print(f"  ✓ {libelle} → {p['nom']} {p['pre']} [{p['lic']}] via {methode}")

    print()
    print(f"Appariés : {len(apparies)}  ({', '.join(f'{k}: {v}' for k, v in sorted(par_methode.items()))})")
    print(f"Non appariés : {len(non_apparies)}")
    for s in non_apparies:
        print(f"  ✗ {s}")
    if sans_date:
        print(f"Sans date de naissance : {len(sans_date)}")
        for s in sans_date:
            print(f"  · {s}")
    if conflits:
        print(f"À vérifier : {len(conflits)}")
        for s in conflits:
            print(f"  ! {s}")

    if args.dry_run:
        print("\n--dry-run : rien n'a été écrit.")
        return
    if not apparies:
        sys.exit("Aucune ligne à écrire.")

    # Upsert par lots (PK licence) : le fichier remplace une éventuelle saisie joueur.
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    ecrits = 0
    for i in range(0, len(apparies), 100):
        lot = apparies[i:i + 100]
        try:
            status, _ = http_json(f"{SB_URL}/rest/v1/naissances", method="POST", body=lot, headers=headers)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            sys.exit(f"Écriture refusée (HTTP {e.code}) : {detail}\n"
                     "→ la table `naissances` existe-t-elle (01_refonte_schema.sql) ? clé service correcte ?")
        if status not in (200, 201, 204):
            sys.exit(f"Réponse inattendue HTTP {status}")
        ecrits += len(lot)
    print(f"\n✅ {ecrits} hachés écrits/mis à jour dans naissances (source=fichier).")


if __name__ == "__main__":
    main()
