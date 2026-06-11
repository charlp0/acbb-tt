# Archive saison 2025-2026 — Championnat par équipes (92 + IDF)

Sauvegarde des **résultats + compositions** de toutes les poules des divisions où l'ACBB est engagée (Dép. Hauts-de-Seine + Ligue Île-de-France), **phases 1 et 2**. National exclu.

⚠️ **Données irremplaçables** : l'API FFTT ne sert que la saison en cours → ces données ne seront plus récupérables après la bascule de saison (août-sept 2026). Conservées pour le projet V2 (assistant de composition d'équipes).

## Structure
```
2025-2026/
  phase-1/  &  phase-2/
    <DIVISION>/poule-<cx_poule>.json   ← championnat (8 divisions/phase)
    _autres-competitions/              ← (phase 1) coupes, critériums "Tableau", etc. — backup, hors périmètre V2
```

## Format d'une poule
```json
{
  "division": "L08_R2 Messieurs phase 2 Poule 4",
  "poule": 4, "cx_poule": 1142536,
  "classement": [{"clt","equipe","pts","joue","vic","nul","def","pg","pp"}],
  "rencontres": [{
    "date": "11/04/2026",
    "equa": "BOULOGNE BILLANCOURT 3",  "equb": "RAMBOUILLET TT 2",   // nom AVEC numéro d'équipe
    "scorea": "23", "scoreb": "19",
    "compo_a": [{"nom": "...", "pts": 1234}],   // pts = classement OFFICIEL (figé saison), pas le mensuel
    "compo_b": [{"nom": "...", "pts": 1180}]
  }]
}
```

## Notes
- `pts` = classement **officiel** de la saison (constant). Le mensuel-au-match n'est pas archivé (non nécessaire pour la projection).
- Pour anticiper l'an prochain : récupérer le **classement alors-actuel** des joueurs via l'API (toujours dispo en direct) = leur niveau de fin 2025-26.
- Généré par `scripts/fftt_archive.py`.
