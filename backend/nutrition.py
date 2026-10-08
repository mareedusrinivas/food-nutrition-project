"""USDA Food Data Central nutrition lookup with an in-memory TTL cache.

Performance notes:
- Results are cached per food name (case-insensitive) so repeated captures of
  the same food don't hit the external API on every request.
- A single ``requests.Session`` reuses TCP connections (keep-alive), avoiding
  a new TLS handshake for each call.
- Negative results ("no foods found") are also cached briefly to protect
  against hammering the API for unknown items.
- The nutrient list is scanned once and mapped by name instead of running
  six separate linear searches.
"""

import threading
import time

import requests

USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# How long (seconds) a successful / failed lookup stays in the cache.
CACHE_TTL = 15 * 60
NEGATIVE_CACHE_TTL = 60

_EMPTY_RESULT = {
    "calories": "N/A", "carbohydrates": "N/A", "protein": "N/A",
    "fat": "N/A", "fiber": "N/A", "sugar": "N/A",
}

# USDA nutrient display names we care about -> output keys
_NUTRIENT_MAP = {
    "Energy": "calories",
    "Carbohydrate, by difference": "carbohydrates",
    "Protein": "protein",
    "Total lipid (fat)": "fat",
    "Fiber, total dietary": "fiber",
    "Sugars, total including NLEA": "sugar",
}


class NutritionClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self._session = requests.Session()
        self._cache = {}            # food -> (expires_at, result)
        self._lock = threading.Lock()

    def fetch(self, food_item):
        """Return dict with calories/carbs/protein/fat/fiber/sugar for a food."""
        key = (food_item or "").strip().lower()
        now = time.monotonic()

        with self._lock:
            entry = self._cache.get(key)
            if entry and entry[0] > now:
                return entry[1]

        result = self._lookup(food_item)

        with self._lock:
            ttl = CACHE_TTL if result is not _EMPTY_RESULT else NEGATIVE_CACHE_TTL
            self._cache[key] = (now + ttl, result)
        return result

    # ------------------------------------------------------------- internals
    def _lookup(self, food_item):
        try:
            response = self._session.get(
                USDA_API_URL,
                params={"query": food_item, "api_key": self.api_key},
                timeout=(3.05, 10),
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            # Network/API failure: don't poison the cache long; return N/A.
            return dict(_EMPTY_RESULT)

        foods = data.get("foods") or []
        if not foods:
            return _EMPTY_RESULT

        nutrients = foods[0].get("foodNutrients") or []
        # Single pass over the nutrient list, mapping every name we need.
        values = {}
        wanted = len(_NUTRIENT_MAP)
        for nutrient in nutrients:
            name = nutrient.get("nutrientName")
            out_key = _NUTRIENT_MAP.get(name)
            if out_key is not None:
                values[out_key] = nutrient.get("value", "N/A")
                if len(values) == wanted:
                    break

        result = {k: values.get(k, "N/A") for k in _NUTRIENT_MAP.values()}
        return result
