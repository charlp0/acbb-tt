#!/usr/bin/env python3
"""Snapshot du classement OFFICIEL de la nouvelle saison (2026/2027) pour tous les
joueurs de l'annuaire -> data/officiel2627.json ({licence: points}).
Utilisé pendant l'intersaison : le récap 2025/2026 est figé, seule cette valeur
« nouvelle saison » est ajoutée aux fiches. Relançable sans risque (la FFTT peut
mettre à jour les valeurs progressivement début juillet).
Identifiants via FFTT_ID / FFTT_PWD. Usage : python3 scripts/fftt_officiel.py
"""
import re, json, time, datetime, importlib.util
spec=importlib.util.spec_from_file_location("fb","scripts/fftt_build.py")
fb=importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def main():
    if not fb.APPID or not fb.MDP: import sys; sys.exit("FFTT_ID / FFTT_PWD manquants")
    idx=json.load(open('data/players_index.json'))
    players=idx if isinstance(idx,list) else idx.get('players',[])
    out={}
    for i,p in enumerate(players):
        lic=str(p.get('lic') or '')
        if not lic.isdigit(): continue
        lb=fb.get('xml_licence_b.php?licence='+lic); time.sleep(0.08)
        m=re.search(r'<point>(\d+)</point>', lb)
        if m: out[lic]=int(m.group(1))
        if (i+1)%50==0: print(f"  {i+1}/{len(players)}")
    if len(out) < len(players)*0.8:
        import sys; sys.exit(f"ABORT: seulement {len(out)}/{len(players)} classements récupérés — API instable, aucune écriture.")
    payload={'built':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saison':'2026/2027','officiel':out}
    json.dump(payload, open('data/officiel2627.json','w'), ensure_ascii=False)
    print(f"OK — {len(out)} classements officiels 2026/2027 -> data/officiel2627.json")

if __name__=='__main__': main()
