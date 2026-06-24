"""
Projecteur extérieur - présence Bermuda (pyscript)
===================================================
Badges K = personnes, C = véhicules.

Comportements (équivalents au blueprint) :
  - Allumage la nuit à l'arrivée (mode : any | vehicle | person | together)
  - Extinction quand une PERSONNE qui vient d'arriver atteint un proxy intérieur
  - Filet de sécurité : timeout, ou lever du soleil
  - Notif "maison vide" (dernier K parti) et "maison ré-occupée" (1er K rentré)
  - Anti faux-positifs reboot WiFi (compteur de proxies Bermuda + durée d'absence)
  - Respect du contrôle manuel : on n'éteint que ce que NOUS avons allumé

Architecture (pensée pour un futur passage en intégration HACS) :
  - CONFIG    : à adapter à ton installation
  - CERVEAU   : fonctions de décision PURES (aucune API HA) -> 100 % réutilisables
  - PLOMBERIE : déclencheurs pyscript qui lisent l'état, appellent le cerveau, agissent

Installation :
  1. Intégration "pyscript" via HACS.
  2. Dans configuration.yaml :
         pyscript:
           allow_all_imports: true
           hass_is_global: true
  3. Déposer ce fichier dans  config/pyscript/projecteur_bermuda.py
  4. Adapter la section CONFIG, puis recharger pyscript (ou redémarrer HA).
"""

from datetime import datetime, timezone, timedelta

# ─────────────────────────── CONFIG ───────────────────────────
PERSONS = ["device_tracker.fsc_bp106k_bermuda_tracker"]       # badges K
PERSON_AREAS = ["sensor.fsc_bp106k_area"]                     # _area des K
VEHICLES = ["device_tracker.fsc_bp105c_bermuda_tracker"]      # badges C

LIGHT = "light.nord_door_projecteur"
SUN = "sun.sun"
PROXY_COUNT = "sensor.bermuda_global_active_proxy_count"
DRIVEWAY_AREA = "Salle de bain travaux"      # zone "allée" (extérieur)

ALLUMAGE_MODE = "any"        # any | vehicle | person | together
MIN_PROXIES = 2              # en dessous = reboot WiFi -> on ignore
AWAY_MIN = 300               # s : absence mini avant allumage (anti-flicker)
TOGETHER_WINDOW = 60         # s : fenêtre "véhicule + personne" (mode together)
ARRIVAL_WINDOW = 300         # s : "vient d'arriver" (pour autoriser l'extinction)
ENTRY_HOLD = 20              # s : area intérieure stable avant extinction
LIGHT_MIN_ON = 30            # s : lumière allumée depuis >= X avant extinction
DEPART_HOLD = 180            # s : confirmation départ
LIGHT_TIMEOUT = 600          # s : extinction de sécurité

# Notifications
NOTIFY_TARGETS = []          # entités notify, ex ["notify.mobile_app_xxx"] ; [] = aucune
TELEGRAM_CONFIG = ""         # config_entry_id Telegram ; "" = désactivé
TELEGRAM_PARSE_MODE = "markdown"   # markdown | markdownv2 | html

# Messages à personnaliser. ⚠️ Évite "maison vide" en clair (interception / écran verrouillé).
# Placeholders : {nom} = badge concerné, {heure} = heure.
MSG_MAISON_VIDE = "🔒 Statut 0 ({heure})"
MSG_MAISON_REOCCUPEE = "🔓 Statut 1 — {nom} ({heure})"

ABSENT = ("not_home", "unknown", "unavailable", "None")

# ─────────────────────────── ÉTAT INTERNE ───────────────────────────
_managed = False             # la lumière est allumée PAR NOUS
_empty = None                # maison vide ? (None = pas encore calculé)
_away_since = {}             # entity -> datetime du dernier passage "absent"

# ─────────────────────────── CERVEAU (pur) ───────────────────────────
# Ces fonctions ne touchent JAMAIS à l'API HA : on leur passe des valeurs.
# C'est ce qui rend la logique réutilisable telle quelle dans une intégration.

def _secs_since(ts):
    if ts is None:
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds()

def is_night(sun_state):
    return sun_state == "below_horizon"

def proxies_ok(count):
    return count is not None and count >= MIN_PROXIES

def is_real_arrival(entity):
    """Le badge était absent assez longtemps (écarte les flickers de reboot)."""
    s = _secs_since(_away_since.get(entity))
    return s is not None and s > AWAY_MIN

def allumage_mode_ok(entity, present_recent):
    """present_recent : dict entity -> True si 'home' et changé il y a < TOGETHER_WINDOW."""
    is_p = entity in PERSONS
    is_v = entity in VEHICLES
    if ALLUMAGE_MODE == "vehicle":
        return is_v
    if ALLUMAGE_MODE == "person":
        return is_p
    if ALLUMAGE_MODE == "together":
        has_v = any(present_recent.get(e) for e in VEHICLES)
        has_p = any(present_recent.get(e) for e in PERSONS)
        return has_v and has_p
    return True  # "any"

def is_interior_area(area_value):
    """Vrai si l'area est une pièce intérieure (≠ allée, ≠ absent)."""
    return area_value not in (DRIVEWAY_AREA,) + ABSENT

def tracker_for_area(area_entity):
    """Retrouve le device_tracker correspondant à un capteur _area (par le nom)."""
    base = area_entity.replace("sensor.", "").replace("_area", "")
    guess = "device_tracker." + base + "_bermuda_tracker"
    if guess in PERSONS:
        return guess
    for p in PERSONS:
        if base in p:
            return p
    return None

# ─────────────────────────── HELPERS pyscript ───────────────────────────

def _val(entity):
    v = state.get(entity)
    return "None" if v is None else str(v)

def _num(entity):
    try:
        return float(state.get(entity))
    except (TypeError, ValueError):
        return None

def _last_changed(entity):
    try:
        return state.get(entity + ".last_changed")
    except Exception:
        return None

def _now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

def _persons_home():
    return [p for p in PERSONS if _val(p) == "home"]

def _friendly(entity):
    try:
        return (state.getattr(entity) or {}).get("friendly_name") or entity
    except Exception:
        return entity

def _notify(message):
    if NOTIFY_TARGETS:
        service.call("notify", "send_message",
                     entity_id=NOTIFY_TARGETS, message=message)
    if TELEGRAM_CONFIG:
        service.call("telegram_bot", "send_message",
                     config_entry_id=TELEGRAM_CONFIG,
                     parse_mode=TELEGRAM_PARSE_MODE, message=message)

# ─────────────────────────── INITIALISATION ───────────────────────────

@time_trigger("startup")
def _init():
    global _empty, _managed
    _managed = False
    _empty = len(_persons_home()) == 0
    # Pour qu'une 1re arrivée après redémarrage compte comme "vraie" :
    long_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    for e in PERSONS + VEHICLES:
        if _val(e) in ABSENT:
            _away_since[e] = long_ago

# ─────────────────────────── PRÉSENCE : timestamps d'absence ───────────────────────────

@state_trigger(*[e + " in ['not_home','unknown','unavailable']" for e in PERSONS + VEHICLES])
def _record_away(var_name=None, **kwargs):
    _away_since[var_name] = datetime.now(timezone.utc)

# ─────────────────────────── 1. ALLUMAGE ───────────────────────────

@state_trigger(*[e + " == 'home'" for e in PERSONS + VEHICLES])
def _allumage(var_name=None, **kwargs):
    global _managed
    if not is_night(_val(SUN)):
        return
    if _val(LIGHT) != "off":
        return
    if not proxies_ok(_num(PROXY_COUNT)):
        return
    if not is_real_arrival(var_name):
        return
    present_recent = {}
    for e in PERSONS + VEHICLES:
        s = _secs_since(_last_changed(e))
        present_recent[e] = (_val(e) == "home") and (s is not None) and (s < TOGETHER_WINDOW)
    if not allumage_mode_ok(var_name, present_recent):
        return
    _managed = True
    light.turn_on(entity_id=LIGHT)

# ─────────────────────────── 2. EXTINCTION (entrée maison) ───────────────────────────

@state_trigger(*PERSON_AREAS)
def _area_changed(var_name=None, value=None, **kwargs):
    # Debounce : on attend ENTRY_HOLD que l'area reste stable
    task.unique("entry_" + var_name)
    new = str(value)
    task.sleep(ENTRY_HOLD)
    if _val(var_name) != new:
        return
    if not is_interior_area(new):
        return
    if _val(LIGHT) != "on":
        return
    if not _managed:            # respect du contrôle manuel
        return
    on_for = _secs_since(_last_changed(LIGHT))
    if on_for is None or on_for < LIGHT_MIN_ON:
        return
    tracker = tracker_for_area(var_name)
    if tracker is None or _val(tracker) != "home":
        return
    since = _secs_since(_last_changed(tracker))
    if since is None or since >= ARRIVAL_WINDOW:   # pas "vient d'arriver"
        return
    light.turn_off(entity_id=LIGHT)

# ─────────────────────────── 3. FILETS DE SÉCURITÉ ───────────────────────────

@state_trigger(LIGHT + " == 'on'", state_hold=LIGHT_TIMEOUT)
def _timeout(**kwargs):
    if _val(LIGHT) == "on" and _managed:
        light.turn_off(entity_id=LIGHT)

@state_trigger(SUN + " == 'above_horizon'")
def _sunrise(**kwargs):
    if _val(LIGHT) == "on" and _managed:
        light.turn_off(entity_id=LIGHT)

# La lumière s'éteint (par nous ou à la main) -> on n'est plus "gestionnaire"
@state_trigger(LIGHT + " == 'off'")
def _light_off(**kwargs):
    global _managed
    _managed = False

# ─────────────────────────── 4. MAISON VIDE / RÉ-OCCUPÉE ───────────────────────────

@state_trigger(*[e + " == 'not_home'" for e in PERSONS], state_hold=DEPART_HOLD)
def _maison_vide(var_name=None, old_value=None, **kwargs):
    global _empty
    if old_value != "home":        # init reboot unknown->not_home : on ignore
        return
    if not proxies_ok(_num(PROXY_COUNT)):
        return
    if _persons_home():            # encore quelqu'un
        return
    if _empty:                     # déjà notifié
        return
    _empty = True
    _notify(MSG_MAISON_VIDE.format(nom=_friendly(var_name), heure=_now_str()))

@state_trigger(*[e + " == 'home'" for e in PERSONS])
def _maison_reoccupee(var_name=None, **kwargs):
    global _empty
    if _empty is not True:         # n'était pas vide -> rien
        return
    if not is_real_arrival(var_name):
        return
    if not proxies_ok(_num(PROXY_COUNT)):
        return
    if len(_persons_home()) != 1:  # ce K est bien le seul présent
        return
    _empty = False
    _notify(MSG_MAISON_REOCCUPEE.format(nom=_friendly(var_name), heure=_now_str()))
