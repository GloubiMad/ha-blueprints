# Gestion Cumulus + Pilotage Solaire

Pilotage du chauffe-eau (cumulus) sous Home Assistant : chauffe HC/HP de base,
sécurités, et préparation d'un pilotage sur **surplus solaire** (autoconsommation).

## Contenu

```
automation/cumulus/
├── README.md                          ← ce fichier (état du projet + stratégie)
├── gestion_globale_cumulus_4.yaml     ← l'automation principale (HC/HP, sécurités, marche forcée)
└── packages/                          ← capteurs solaires (à charger via packages HA)
    ├── solaire_zendure.yaml           ← 2 PV clean du Hyper #1 (glagla)
    ├── solaire_apsystems.yaml         ← 4 PV clean des 2 APsystems EZ1 (Est + Sud)
    ├── solaire_total.yaml             ← sensor.production_solaire_totale (somme des 6)
    └── solaire_surplus.yaml           ← surplus brut + lissé (démasque le buffer batterie)
```

> Les fichiers `packages/` supposent `homeassistant: packages: !include_dir_named packages`
> côté config HA. L'automation se colle dans l'éditeur d'automations (mode YAML).

---

## Helpers à créer (UI → Paramètres → Appareils → Helpers)

| Helper | Type | Rôle |
|---|---|---|
| `input_boolean.cumulus_a_chauffer` | Booléen | l'eau doit être chauffée (conso > 200L ou sécurité 36h) |
| `input_boolean.cumulus_force` | Booléen | marche forcée (manuelle / future commande solaire) |
| `input_datetime.cumulus_derniere_chauffe` | Date+heure | date persistante de la dernière chauffe (survit aux reboots HA) |
| `sensor.cumulus_heures_sans_chauffe` | Template (num) | heures depuis dernière chauffe (couleur seuil) |
| `sensor.cumulus_temps_sans_chauffe` | Template (texte) | format "1h48" pour l'affichage |

Templates des 2 capteurs (basés sur `input_datetime.cumulus_derniere_chauffe`) :

```jinja
# sensor.cumulus_heures_sans_chauffe (unité "h")
{{ ((now().timestamp() - state_attr('input_datetime.cumulus_derniere_chauffe','timestamp')) / 3600) | round(1) }}

# sensor.cumulus_temps_sans_chauffe (sans unité)
{% set total = now().timestamp() - state_attr('input_datetime.cumulus_derniere_chauffe','timestamp') %}
{{ (total // 3600) | int }}h{{ '%02d' | format(((total % 3600) // 60) | int) }}
```

---

## Logique de l'automation (gestion_globale_cumulus_4.yaml)

`mode: queued`, `max: 3`. Les boucles `repeat: 5` sur `light.cumulus` sont
**volontaires** (l'appareil reçoit mal les ordres ON/OFF) — ne pas les retirer.

| Bloc | Déclencheur | Effet |
|---|---|---|
| HP actif | fin HC | coupe cumulus_a_chauffer (si on) + éteint |
| Arrêt anticipé | 03:37 | coupe avant fin HC |
| HC actif | début HC | sécurité 36h si pas chauffé / sinon chauffe si cumulus_a_chauffer on |
| Seuil >200L | conso eau | active cumulus_a_chauffer (+ démarrage immédiat si HC déjà active) |
| Reset matin | 07:00 | remet cumulus_a_chauffer à off (seulement si on) |
| Check 21:37 | 21:37 | éteint si cumulus_a_chauffer off avant entrée HC |
| Sécurité HP | allumage light | éteint un allumage intempestif en HP (si force off) |
| Force ON / 2h / OFF | cumulus_force | marche forcée + enregistrement chauffe si >= 2h |
| Chauffe terminée | cumulus_a_chauffer ON→OFF | enregistre la date dans input_datetime |

### Points clés / bugs corrigés
- **`cumulus_a_chauffer` jamais remis OFF s'il est déjà OFF** → préserve le compteur 36h.
- **`last_changed` se reset au reboot HA** → on utilise `input_datetime.cumulus_derniere_chauffe` (persistant), mis à jour sur fin de chauffe.
- **Marche forcée** chauffe via `light.cumulus` sans passer par `cumulus_a_chauffer`
  → enregistrement de la chauffe uniquement au **passage des 2h** (bloc Force 2h).
  Une marche forcée **< 2h ne compte PAS** comme une chauffe (pas d'enregistrement dans Force OFF).

---

## Installation solaire (contexte)

- **Zendure Hyper #1** (entités `hyper_2000_glagla`) : 2 MPPT (~1600W+, 2000Wc), 5760 Wh batt, sortie 1200W, plancher SOC 15%.
- **Zendure Hyper #2** (entités `hyper_2000_up`) : pas de PV, 3840 Wh batt, sortie 1200W, plancher 15%.
- **APsystems EZ1 Est** : `sensor.solar_power_of_p1/p2`, 980W max.
- **APsystems EZ1 Sud** : `sensor.solar_1_sud_ok_power_of_p1/p2`, 980W max.
- **Shelly Pro 3EM** `sensor.shellypro3em_9454c5b8aaf0_phase_c_active_power` : sert à la régul Zendure. Import = +, injection = −.
- Autoconsommation (pas de vente EDF), injection tolérée ~3000W courte durée.
- Les Zendure régulent le réseau à ~0W via charge/décharge batteries.

### Capteur clé : `bat_in_out`
`sensor.hyper_2000_<nom>_bat_in_out` = puissance batterie **signée : + décharge / − charge**.
C'est le bon signal pour le surplus (les noms `output_pack_power` / `pack_input_power`
sont **inversés** par rapport à leur sens, à éviter).

---

## Stratégie pilotage solaire (validée, pas encore implémentée)

Tarifs : **HP 0,1727 €/kWh · HC 0,1376 €/kWh**.

- Cumulus = charge **2400W non modulable**, à ne pas cycler (l'abîme) → cycle engagé **1h30–2h30**.
- **Surplus pur UNIQUEMENT, jamais drainer les batteries** :
  - surplus pur → cumulus = gain 0,1376 €/kWh (HC nuit évitée),
  - batterie → cumulus = perte 0,0351 €/kWh (la batterie vaut mieux pour effacer le HP).
- Décider sur **signaux lents** (surplus lissé, SOC batteries, forecast) — jamais l'instantané (bruit régul + nuages).
- Modèle **one-shot** : 1 cycle/jour, lancé midi quand batteries pleines + prod forte soutenue + forecast OK + HP. Pas d'arrêt mid-cycle. Hiver : conditions jamais réunies → fallback HC nuit (auto-régulé).
- **Solar Production Forecast** : `sensor.energy_production_today_remaining` = capteur clé pour valider qu'il reste assez de soleil pour le cycle + recharge.

---

## Suite / TODO

1. Créer les helpers + capteurs ci-dessus, charger les packages.
2. Vérifier `sensor.surplus_solaire_lisse` sur quelques jours, ajuster la fenêtre du filtre.
3. Choisir l'outil de pilotage multi-charges (cumulus + future VE + SolarFlow) :
   - **Solar Optimizer** (`jmcollin78/solar_optimizer`) — routeur surplus temps réel, durée min d'activation (idéal cumulus). Lui donner `sensor.surplus_solaire_lisse`.
   - **EMHASS** (`davidusb-geek/emhass`) — optimiseur prévisionnel (forecast + HC/HP + batterie). Plus puissant, plus exigeant. Install via add-on.
   - **PV Excess Control** (`InventoCasa/ha-pv-excess-control`) — blueprint intermédiaire.
