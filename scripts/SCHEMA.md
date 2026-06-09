# Schéma profil joueur — data/players/<licence>.json

Généré par `scripts/fftt_build.py` (source : API FFTT SmartPing).

```jsonc
{
  "lic": "7824630",
  "nom": "PERROT", "prenom": "Charles", "club": "08920049",
  "classement": {
    "officiel": 953,   // points figés de la phase (xml_licence_b <point>)
    "mensuel": 1031,   // classement mensuel officiel (<pointm>)
    "debut":   896,    // 1er mensuel saison (<initm>)
    "avenir":  1042    // initm + tous points (validés réels + non-validés estimés grille)
  },
  "timeline": [ {"m":"Sept","v":896}, ... {"m":"Juil","v":1042,"avenir":true} ],  // escalier mensuel
  "saison": {
    "V":33,"D":24,"parties":57,"winpct":58,
    "perfs":9,"contre_perfs":9,                      // perf = battu mieux classé ; contre = perdu vs - classé
    "best":  {"delta":..,"opp":..,"opp_cls":..,"my":..,"date":..,"comp":..},
    "worst": {"delta":..,"opp":..,"opp_cls":..,"my":..,"date":..,"comp":..}
  },
  "competitions": [   // une entrée par compétition jouée (triée par nb matchs)
    {
      "key":"criterium","label":"Critérium fédéral",
      "V":16,"D":12,"winpct":57,
      "pg":197.2,"pl":-38.2,"solde":159.0,            // points gagnés / perdus / solde
      "perf":7,"cperf":1,
      "matches":[ {"date":..,"opp":..,"opp_cls":..,"won":true,"pts":..}, ... ]
    }
  ]
}
```

## Catégorisation (par nom d'épreuve API `<epreuve>`)
| mot-clé épreuve            | catégorie (`key`) |
|----------------------------|-------------------|
| `…Équipes…`                | `equipe`          |
| `…Critérium…`              | `criterium`       |
| `…Championnat de Paris…`   | `paris`           |
| `…TOURNOI…`                | `tournoi`         |
| `…Coupe…`                  | `coupe`           |
| (autre)                    | `autre`           |

## Précision
- Matchs **homologués** : points = `pointres` réels de l'API → **exact**.
- Matchs **non encore homologués** (récents) : points = **estimation grille FFTT** → se corrige automatiquement à l'homologation.
- `opp_cls` = classement **officiel courant** de l'adversaire (≈ niveau au match, à quelques points près).
