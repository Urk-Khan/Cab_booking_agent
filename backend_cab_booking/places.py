"""
Google Places API (New) integration — location search for pickup/drop-off confirmation.

Wraps the Places API "Text Search (New)" endpoint so the voice pipeline can silently resolve
a caller's spoken pickup/drop-off location (a landmark, business name, or partial address)
into real, current UK places before locking it into a booking.

Two extra checks happen here, entirely in the backend — the caller never hears about either:

1. UK-only filtering: every candidate's country is checked via its address components.
   Non-UK matches are flagged (in_uk=False) rather than silently dropped, so the caller can
   still be told plainly that the location is outside the service area.

2. Precision check ("under 500 meters"): a place is only "precise" enough to confirm without
   further questions if it resolves to a tight area — a street address, a specific business,
   a landmark — not a whole city, neighborhood, or region. This uses the place's viewport
   (the bounding box Google returns for how that place is displayed on a map) and measures
   its diagonal; anything wider than ~500m is treated as too broad. If Google doesn't return
   a viewport for a candidate, we fall back to checking its place `types` against a list of
   broad/administrative types (city, locality, state, etc.).

This module only talks to Google; it has no knowledge of Pipecat, FunctionCallParams, or the
LLM tool-calling layer — that seam lives in tools.py (search_location tool wrapper). Keeping
it separate means it's easy to unit-test or swap providers later.
"""

import math
import os

import aiohttp
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=False)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Only request the fields we actually use — Places API (New) bills by field mask, and a
# narrow mask keeps this call cheap and fast (caller is on hold while we wait on it).
# - types / viewport: used for the precision ("under 500m") check
# - addressComponents: used for the UK-only check
_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.types,places.viewport,places.addressComponents"
)

# Keep this tool-call fast; a stalled search is a stalled phone call.
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=5)

# Max candidates returned to the LLM. A few options is enough to disambiguate ("did you mean
# the one on Main St or the one on 5th Ave?") without overwhelming the conversation.
_MAX_RESULTS = 5

# A candidate is only "precise" if its viewport diagonal is at or under this radius.
_PRECISION_RADIUS_METERS = 500

# Place `types` that indicate a broad area (a whole city, state, region, postal code, etc.)
# rather than a specific point. Used as a fallback when Google doesn't return a viewport.
_BROAD_PLACE_TYPES = {
    "country",
    "administrative_area_level_1",
    "administrative_area_level_2",
    "administrative_area_level_3",
    "administrative_area_level_4",
    "administrative_area_level_5",
    "locality",
    "sublocality",
    "sublocality_level_1",
    "sublocality_level_2",
    "sublocality_level_3",
    "postal_code",
    "postal_town",
    "region",
    "colloquial_area",
    "continent",
}


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lng points, in meters."""
    earth_radius_m = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def _viewport_diagonal_meters(viewport):
    if not viewport:
        return None
    low = viewport.get("low") or {}
    high = viewport.get("high") or {}
    lat1, lon1 = low.get("latitude"), low.get("longitude")
    lat2, lon2 = high.get("latitude"), high.get("longitude")
    if None in (lat1, lon1, lat2, lon2):
        return None
    return _haversine_meters(lat1, lon1, lat2, lon2)


def _is_uk(address_components) -> bool:
    for comp in address_components or []:
        if "country" in (comp.get("types") or []):
            # Google's ISO 3166-1 alpha-2 code for the United Kingdom is "GB", not "UK" —
            # this is the one detail that silently breaks the filter if you get it wrong.
            return comp.get("shortText") == "GB"
    # No country component at all — treat as unresolved/non-UK rather than guessing.
    return False


def _is_precise(place_types, viewport) -> bool:
    diagonal = _viewport_diagonal_meters(viewport)
    if diagonal is not None:
        return diagonal <= _PRECISION_RADIUS_METERS
    # No viewport to measure — fall back to the type-based heuristic.
    return not (set(place_types or []) & _BROAD_PLACE_TYPES)


async def search_location(query: str) -> list[dict]:
    """Search current UK locations by name, landmark, or address using the Places API (New).

    Args:
        query: Free-text location query, e.g. "Heathrow Airport", "Costa Coffee on Oxford
            Street London", "10 Downing Street, London".

    Returns:
        A list of up to 5 candidate places (best match first), each a dict with:
            name: str               - the place's display name
            formatted_address: str  - full formatted address
            latitude: float | None
            longitude: float | None
            place_id: str
            in_uk: bool             - True if this place's country is the UK
            precise: bool           - True if it resolves to a specific point (roughly
                                       under 500m across), not a whole city/region
        Returns an empty list if the API key is missing, the request fails, or there are no
        matches — callers should treat an empty list as "couldn't find it" and handle that
        conversationally rather than raising.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY is not set in .env — search_location cannot run.")
        return []

    if not query or not query.strip():
        return []

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": _FIELD_MASK,
    }
    # regionCode biases results toward the UK but is not a hard filter — _is_uk() below is
    # the hard filter.
    payload = {
        "textQuery": query.strip(),
        "regionCode": "GB",
    }

    try:
        async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
            async with session.post(
                _PLACES_TEXT_SEARCH_URL, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
    except Exception as e:
        logger.error(f"Google Places search failed for query={query!r}: {e}")
        return []

    places = data.get("places", []) or []
    results = []
    for place in places[:_MAX_RESULTS]:
        location = place.get("location") or {}
        types = place.get("types") or []
        viewport = place.get("viewport")
        results.append(
            {
                "name": (place.get("displayName") or {}).get("text", ""),
                "formatted_address": place.get("formattedAddress", ""),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "place_id": place.get("id", ""),
                "in_uk": _is_uk(place.get("addressComponents")),
                "precise": _is_precise(types, viewport),
            }
        )

    if not results:
        logger.info(f"Places search returned no matches for query={query!r}")

    return results