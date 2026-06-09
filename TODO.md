# TODO / Roadmap — Projecteur Bermuda

## ✅ Fait
- v1.1 : respect du contrôle manuel, garde-fou reboot HA, notif « maison ré-occupée »
- Action générique : scripts optionnels à l'arrivée / l'extinction (`on_actions` / `off_actions`)
- Messages de notif configurables (départ / arrivée) + `{{ trigger_name }}` (nom du badge) + format Telegram au choix
- Variante pyscript (base)

## 🔜 Backlog

### Scripts d'arrivée / extinction — usages étendus
Les scripts `on_actions` / `off_actions` peuvent faire **plus** qu'allumer une lumière :
- **fermer / ouvrir les volets**
- **enclencher / désactiver l'alarme**
- jouer une scène, ajuster le chauffage, verrouiller des portes, etc.

→ Déjà possible techniquement ; à **documenter avec des exemples de scripts** prêts à l'emploi.

### « Maison vide » → check de sécurité
Quand plus aucun badge K n'est présent, **vérifier (et alerter / corriger)** que la maison est bien sécurisée :
- [ ] **alarme enclenchée**
- [ ] **toutes les lumières éteintes**
- [ ] **volets fermés**
- [ ] (à définir : portes verrouillées, chauffage en mode éco, garage fermé…)

→ Notifier ce qui n'est pas conforme, et/ou déclencher un script « fermeture maison ».

### Fonctionnalités prévues
- **[8]** Notif actionnable (boutons appli mobile : « garder allumé 30 min » / « ignorer ») — *en attente*
- **[11]** Multi-lumières **par zone** (vraie version : lumière différente selon le proxy d'arrivée) — plutôt en **pyscript**
- **Associations véhicule ↔ personne** pour le mode d'allumage « ensemble » (paires précises)
- Capteur **lux** + **offset d'élévation solaire** (vraie obscurité plutôt que `below_horizon` brut)
- **Profil de luminosité horaire** (100 % en soirée, réduit après minuit)
- **Avertissement avant extinction** (dim 30 % pendant 20 s)
- **Interrupteur « pause »** (vacances / soirée) qui neutralise tout
- **Resynchroniser la variante pyscript** avec les dernières features du blueprint

## 🌅 Horizon
- Passage en **pyscript piloté par helpers / labels** (config en UI, logique en Python)
- Éventuelle **intégration HACS** (config_flow + entités exposées) si publication
