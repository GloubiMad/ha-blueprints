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
