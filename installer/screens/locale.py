"""Screen 2 & 3 -- Language / Locale and Timezone.

Language: pick a locale from the standard set.
Timezone: region then city drill-down exactly like tzselect, backed by
the live media's /usr/share/zoneinfo tree when available.
"""

import os

from core import ui
from core.config import tux

LOCALES = [
    ("en_US.UTF-8", "English (United States)"),
    ("id_ID.UTF-8", "Bahasa Indonesia"),
    ("ar_AE.UTF-8", "Arabic (United Arab Emirates)"),
    ("de_DE.UTF-8", "Deutsch (Deutschland)"),
    ("fr_FR.UTF-8", "Francais (France)"),
    ("ja_JP.UTF-8", "Japanese (Japan)"),
    ("zh_CN.UTF-8", "Chinese (Simplified, PRC)"),
    ("es_ES.UTF-8", "Espanol (Espana)"),
    ("tr_TR.UTF-8", "Turkce (Turkiye)"),
    ("ru_RU.UTF-8", "Russian (Russia)"),
]

ZONEINFO = "/usr/share/zoneinfo"

SKIP_REGIONS = {
    "posix", "right", "SystemV", "etc", "Etc", "factory", "localtime",
}


def _available_regions():
    if not os.path.isdir(ZONEINFO):
        return []
    regions = []
    for entry in sorted(os.listdir(ZONEINFO)):
        path = os.path.join(ZONEINFO, entry)
        if os.path.isdir(path) and entry not in SKIP_REGIONS:
            regions.append(entry)
    return regions


def _available_cities(region):
    base = os.path.join(ZONEINFO, region)
    if not os.path.isdir(base):
        return []
    cities = []
    for entry in sorted(os.listdir(base)):
        full = os.path.join(base, entry)
        if os.path.isfile(full) and ".tab" not in entry:
            cities.append(entry.replace("_", " "))
    return cities


FALLBACK_REGIONS = {
    "America": ["New York", "Chicago", "Denver", "Los Angeles", "Mexico City",
                "Toronto", "Sao Paulo", "Buenos Aires", "Bogota", "Caracas"],
    "Europe": ["London", "Berlin", "Paris", "Madrid", "Rome", "Amsterdam",
               "Brussels", "Vienna", "Warsaw", "Istanbul", "Moscow", "Zurich"],
    "Africa": ["Cairo", "Lagos", "Nairobi", "Casablanca", "Johannesburg",
               "Accra", "Addis Ababa"],
    "Asia": ["Tokyo", "Shanghai", "Hong Kong", "Singapore", "Jakarta",
             "Bangkok", "Kolkata", "Tehran", "Riyadh", "Dubai", "Seoul",
             "Taipei", "Manila", "Ho Chi Minh", "Tallinn"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    "Pacific": ["Auckland", "Honolulu", "Fiji", "Guam", "Bougainville"],
    "Atlantic": ["Azores", "Reykjavik", "South Georgia", "St Helena"],
    "Indian": ["Maldives", "Mauritius", "Chagos", "Christmas"],
}


def _pick_locale(cfg):
    items = [(code, name) for code, name in LOCALES]
    preselected = cfg.locale
    radiolist_items = [
        (code, name, "ON" if code == preselected else "OFF")
        for code, name in items
    ]
    tags, cancelled = ui.select(
        "Language",
        f"{tux()}\n\nChoose your system language:",
        radiolist_items,
        kind=ui.RADIOLIST,
        width=74,
    )
    if cancelled:
        return False
    if not tags:
        return False
    cfg.locale = tags[0]
    return True


def _pick_region(cfg):
    regions = _available_regions() or list(FALLBACK_REGIONS)
    items = [(r, r) for r in regions]
    tags, cancelled = ui.select(
        "Region",
        f"{tux()}\n\nSelect your region:",
        items,
        kind=ui.MENU,
        width=60,
    )
    if cancelled:
        return False
    cfg.region = tags[0]
    return True


def _pick_city(cfg):
    cities = _available_cities(cfg.region)
    if not cities:
        cities = FALLBACK_REGIONS.get(cfg.region, [])
    if not cities:
        return True  # region has no drill-down; keep the region zone
    items = [(c, c) for c in cities]
    tags, cancelled = ui.select(
        "City",
        f"{tux()}\n\nSelect your city ({cfg.region}):",
        items,
        kind=ui.MENU,
        width=60,
    )
    if cancelled:
        return False
    cfg.city = tags[0].replace(" ", "_")
    return True


def run(cfg):
    result = _pick_locale(cfg)
    if not result:
        return False
    result = _pick_region(cfg)
    if not result:
        return False
    result = _pick_city(cfg)
    if not result:
        return False
    return True