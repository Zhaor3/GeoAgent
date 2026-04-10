from __future__ import annotations

import json

import anthropic

from geo_agent.config import settings
from geo_agent.models.schemas import VisualClues
from geo_agent.utils.image import detect_media_type, image_to_base64, resize_image
from geo_agent.utils.parse import extract_json_object, get_text_from_response

# --------------------------------------------------------------------------- #
# PASS 1 — Broad sweep: extract every possible clue from the image
# --------------------------------------------------------------------------- #
PASS1_PROMPT = """\
You are the world's #1 geolocation analyst — a GeoGuessr world champion \
combined with a senior OSINT investigator. Your job is to determine exactly \
where in the world this photo was taken. Every single pixel matters.

Study this image with EXTREME attention to detail. Zoom in mentally on every \
part of the image. Extract EVERY geographic clue you can find, no matter how \
small or seemingly insignificant.

PAY SPECIAL ATTENTION TO:

LICENSE PLATES & VEHICLES:
- Read every character on any license plate. Note the plate format (color, \
shape, number of characters, any symbols/flags/coat of arms).
- Identify vehicle makes, models, and which market they are sold in.
- Note any taxi colors, bus designs, or public transport branding.

TEXT, SIGNS & WRITING:
- Transcribe ALL visible text character by character — shop names, street \
signs, billboards, graffiti, stickers, posters, even partial text.
- Identify the EXACT language and script. Distinguish between similar scripts \
(e.g., Serbian Cyrillic vs Russian, Traditional vs Simplified Chinese, \
Brazilian Portuguese vs European Portuguese).
- Note phone number formats (country code, digit grouping).
- Note any URLs, domain extensions (.co.uk, .com.br, .de), or email addresses.

ROAD & INFRASTRUCTURE:
- Road markings: color (white/yellow), style (dashed/solid), lane width.
- Road signs: shape, color scheme, font style (these vary by country).
- Traffic lights: horizontal vs vertical, LED vs bulb, any pedestrian signal \
style.
- Utility poles: material, style of insulators, wire configuration.
- Bollards, guardrails, road barriers: each country has distinct styles.
- Street lights: arm style, lantern shape.
- Pedestrian crossings: style (zebra, pelican, continental).
- Speed bumps, curb styles, drainage grate patterns.
- Sidewalk material and width.

ARCHITECTURE & BUILDINGS:
- Building style: identify the specific architectural tradition.
- Construction materials, wall colors, window frame styles.
- Roof type, chimney style, balcony railings.
- Door styles, gate designs, fence types.
- Building height restrictions or patterns typical of certain regions.
- Any house numbering system visible.

NATURE & GEOGRAPHY:
- Identify specific plant species if possible (not just "palm trees" — what \
kind of palm?).
- Soil/earth color (laterite red, volcanic black, sandy, clay).
- Mountain shapes, rock formations.
- Sky color, cloud types, sun angle and shadow direction.
- Coastal features: beach sand color, wave patterns, tide indicators.

PEOPLE & CULTURE:
- Clothing styles, skin tones, any uniforms.
- Any cultural markers (religious buildings, flags, decorations).
- Shop types and what they sell.

BRAND & CHAIN CLUES:
- Identify ANY brand logos, chain stores, gas station brands, telecom \
providers, bank names — these are often country-specific.
- Note any product packaging visible.

Return a JSON object with these fields:

{
  "text_and_signage": {
    "visible_text": ["transcribe ALL readable text exactly as written"],
    "language_detected": "specific language (e.g. 'Brazilian Portuguese' not just 'Portuguese')",
    "script_type": "latin/cyrillic/arabic/cjk/devanagari/thai/hangul/etc",
    "sign_types": ["type of each sign seen"],
    "phone_numbers_or_codes": ["any phone numbers, area codes, or country codes visible"],
    "urls_or_domains": ["any web addresses or domain extensions visible"]
  },
  "architecture": {
    "style": "specific architectural style and regional variant",
    "building_materials": ["specific materials"],
    "roof_type": "detailed description",
    "era_estimate": "time period with reasoning",
    "window_style": "description of window frames and patterns",
    "building_colors": ["dominant wall/facade colors"],
    "house_numbering": "format if visible"
  },
  "infrastructure": {
    "road_surface": "specific type and condition",
    "road_markings": "exact colors, patterns, lane separator style",
    "road_sign_style": "shape, color scheme, font — which country standard?",
    "driving_side": "left/right with evidence (car positions, road layout)",
    "traffic_lights": "orientation and style description",
    "utility_poles": "material, insulator style, wire config",
    "bollard_style": "description with country guess",
    "street_lights": "arm and lantern style",
    "pedestrian_crossings": "style description",
    "sidewalk_material": "type and pattern",
    "guardrails_barriers": "style description"
  },
  "nature": {
    "vegetation_type": "specific biome or climate zone",
    "specific_plants": ["identify species as precisely as possible"],
    "terrain": "detailed terrain description",
    "soil_color": "specific color and type",
    "water_bodies": "type and characteristics",
    "mountain_features": "shape, snow line, geological type",
    "sky_and_clouds": "cloud types, sky color, visibility"
  },
  "environmental": {
    "sun_position": "angle and direction based on shadows",
    "shadow_analysis": "shadow direction and length — what does this tell us about latitude and time?",
    "hemisphere_hint": "northern/southern with reasoning",
    "season_hint": "season with evidence",
    "weather": "detailed weather description",
    "time_of_day": "estimated time with reasoning",
    "climate_zone_guess": "tropical/subtropical/temperate/continental/arid/etc"
  },
  "vehicles_and_people": {
    "license_plates": [{"text": "exact characters if readable", "format": "color, shape, layout", "country_guess": "which country uses this format"}],
    "vehicle_types": ["specific makes and models if identifiable"],
    "vehicle_brands": ["all brands seen"],
    "vehicle_market": "which regional market are these vehicles typical of?",
    "taxi_or_transit": "description of any taxis or public transport",
    "clothing_style": "detailed description of what people are wearing",
    "apparent_ethnicity_or_region": "demographic observation if relevant to location"
  },
  "distinctive_features": {
    "landmarks": ["any recognizable landmarks or monuments"],
    "brand_names": ["every brand, chain, store name, or logo visible"],
    "telecom_providers": ["any mobile carrier names or logos"],
    "bank_or_financial": ["any bank names or ATM brands"],
    "gas_stations": ["any fuel station brands"],
    "unique_clues": ["anything else that narrows down the location"],
    "flags_or_symbols": ["any national, regional, or organizational flags/symbols"]
  },
  "overall_impression": "Your expert assessment: describe the gestalt of all clues and your gut feeling about where this is. What country does this FEEL like? What region? Be specific."
}

Return ONLY valid JSON, no markdown fences or extra text."""

# --------------------------------------------------------------------------- #
# PASS 2 — Deep-focus: re-examine the image looking for missed details
# --------------------------------------------------------------------------- #
PASS2_PROMPT = """\
You are a world-class geolocation expert doing a SECOND, deeper analysis of \
this image. A first-pass analysis already found these clues:

{pass1_json}

Now look at the image AGAIN with fresh eyes. Your job is to find what was \
MISSED in the first pass. Focus on:

1. TINY DETAILS: Look at edges, corners, reflections in windows/cars, \
partially obscured text, blurry signs in the background.
2. CONTRADICTIONS: Does anything in the first-pass analysis seem wrong? \
Any clues that contradict each other?
3. CULTURAL MICRO-DETAILS: Electrical outlet shapes on buildings, antenna \
types, mailbox styles, garbage bin designs, manhole cover patterns, \
parking meter styles — these are extremely country-specific.
4. DISTANCE CLUES: What's in the far background? Mountains? City skyline? \
Type of horizon?
5. META-CLUES: What is the STYLE of photography? Tourist photo? Google \
Street View? Dashcam? Security camera? This affects where it might be.

Return a JSON object with ONLY new or corrected information (not a repeat of \
pass 1). Use this format:

{
  "additional_text": ["any new text found"],
  "additional_brands": ["any new brands or signs found"],
  "corrected_clues": {"field": "corrected value — explain why the first pass was wrong"},
  "micro_details": ["list every tiny country-specific detail: outlet types, manhole covers, bin styles, antenna types, etc."],
  "background_analysis": "what is visible in the far background?",
  "photography_style": "what type of camera/photo is this?",
  "missed_clues": ["anything else the first pass missed"],
  "refined_location_guess": "Based on ALL evidence combined, your refined gut feeling about the exact location"
}

Return ONLY valid JSON, no markdown fences or extra text."""




async def _call_and_parse_object(
    client: anthropic.AsyncAnthropic,
    model: str,
    image_block: dict,
    prompt: str,
) -> dict:
    """Call the API with image + prompt and parse a JSON object from the response.
    Retries once without extended thinking if the first attempt fails to parse."""
    for attempt in range(2):
        kwargs = dict(
            model=model,
            max_tokens=settings.THINKING_BUDGET + 4096,
            messages=[
                {
                    "role": "user",
                    "content": [image_block, {"type": "text", "text": prompt}],
                }
            ],
        )
        if attempt == 0:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": settings.THINKING_BUDGET,
            }
        else:
            kwargs["max_tokens"] = 4096

        resp = await client.messages.create(**kwargs)
        raw = get_text_from_response(resp)
        try:
            return extract_json_object(raw)
        except Exception:
            if attempt == 0:
                continue
            raise


async def extract_visual_clues(image_bytes: bytes) -> VisualClues:
    resized = resize_image(image_bytes)
    b64 = image_to_base64(resized)
    media_type = detect_media_type(resized)

    image_block = {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": b64},
    }

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ---- PASS 1: broad sweep with extended thinking ----
    pass1_data = await _call_and_parse_object(
        client, settings.MODEL_HEAVY, image_block, PASS1_PROMPT,
    )
    clues = VisualClues(**pass1_data)

    # ---- PASS 2: deep-focus re-examination with extended thinking ----
    try:
        pass2_prompt = PASS2_PROMPT.format(pass1_json=json.dumps(pass1_data, indent=2))
        pass2_data = await _call_and_parse_object(
            client, settings.MODEL_HEAVY, image_block, pass2_prompt,
        )
        _merge_pass2(clues, pass2_data)
    except Exception:
        pass  # Pass 2 is best-effort; continue with Pass 1 data

    return clues


def _merge_pass2(clues: VisualClues, pass2: dict) -> None:
    extra_text = pass2.get("additional_text", [])
    if extra_text:
        existing = clues.text_and_signage.get("visible_text", [])
        clues.text_and_signage["visible_text"] = existing + extra_text

    extra_brands = pass2.get("additional_brands", [])
    if extra_brands:
        existing = clues.distinctive_features.get("brand_names", [])
        clues.distinctive_features["brand_names"] = existing + extra_brands

    micro = pass2.get("micro_details", [])
    if micro:
        existing = clues.distinctive_features.get("unique_clues", [])
        clues.distinctive_features["unique_clues"] = existing + micro

    corrections = pass2.get("corrected_clues", {})
    for field, value in corrections.items():
        for section_name in [
            "text_and_signage", "architecture", "infrastructure",
            "nature", "environmental", "vehicles_and_people",
            "distinctive_features",
        ]:
            section = getattr(clues, section_name, {})
            if isinstance(section, dict) and field in section:
                section[field] = value

    bg = pass2.get("background_analysis", "")
    refined = pass2.get("refined_location_guess", "")
    if bg or refined:
        extra = []
        if bg:
            extra.append(f"Background: {bg}")
        if refined:
            extra.append(f"Refined guess: {refined}")
        clues.overall_impression += "\n" + "\n".join(extra)
