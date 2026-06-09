# ha-blueprints

Blueprints Home Assistant personnels.

## Projecteur extérieur - présence Bermuda (badges K / C)

`automation/projecteur_bermuda.yaml`

Pilote une lumière extérieure à partir de trackers BLE [Bermuda](https://github.com/agittins/bermuda) :

- **Allumage** à l'arrivée la nuit (mode au choix : véhicule C, personne K, les deux ensemble, ou n'importe lequel).
- **Extinction** quand une personne (badge K) qui vient d'arriver entre dans la maison (proxy ≠ allée).
- **Filet de sécurité** : extinction après un timeout ou au lever du soleil.
- **Respect du contrôle manuel** : n'éteint pas une lumière allumée à la main (UI).
- **Notification « maison ré-occupée »** quand le premier badge K rentre dans une maison vide.
- **Notification(s) « maison vide »** vers une ou plusieurs entités `notify` (sélectionnables dans une liste) quand plus aucun badge K n'est présent.
- **Anti faux-positifs reboot WiFi** via le compteur de proxies Bermuda (`sensor.bermuda_global_active_proxy_count`).

Convention de badges : noms se terminant par **K** = personnes, par **C** = véhicules. Les véhicules ne comptent pas pour « maison vide ».

### Import dans Home Assistant

Paramètres → Automatisations & scènes → Blueprints → **Importer un blueprint**, puis colle l'URL :

```
https://github.com/GloubiMad/ha-blueprints/blob/main/automation/projecteur_bermuda.yaml
```

## Variante pyscript (logique en Python)

`pyscript/projecteur_bermuda.py`

Même comportement que le blueprint, mais écrit en Python via l'intégration
[pyscript](https://github.com/custom-components/pyscript) (HACS) — plus lisible/maintenable
quand la logique se complexifie (associations, multi-zones, état interne…).

Architecture **« cerveau + plomberie »** : la logique de décision est isolée dans des
fonctions pures, donc réutilisable telle quelle si on passe un jour à une intégration HACS.

Installation :
1. Intégration **pyscript** via HACS.
2. `configuration.yaml` :
   ```yaml
   pyscript:
     allow_all_imports: true
     hass_is_global: true
   ```
3. Copier le fichier dans `config/pyscript/projecteur_bermuda.py`, adapter la section `CONFIG`, recharger pyscript.

> Le blueprint reste la version « simple/partageable » ; la variante pyscript est la version « puissance ».
