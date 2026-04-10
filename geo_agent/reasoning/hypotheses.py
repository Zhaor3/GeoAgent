from __future__ import annotations

import json

import anthropic

from geo_agent.config import settings
from geo_agent.models.schemas import Hypothesis, VisualClues
from geo_agent.utils.parse import extract_json_array, get_text_from_response

HYPOTHESIS_PROMPT = """\
You are the world's best geolocation analyst. Based on the following \
extracted visual clues from an image, determine where this photo was taken.

Think step by step:

STEP 1 — NARROW THE CONTINENT:
Which continent is this most likely on? Use language/script, driving side, \
vegetation, architecture, and vehicle types to narrow down.

STEP 2 — NARROW THE COUNTRY:
Which country? Cross-reference ALL clues:
- License plate format → specific country
- Language + script → specific country or region
- Road sign standard → specific country (colors, shapes, fonts vary)
- Brand names → many chains are country-specific
- Utility pole style, bollard design → country-specific
- Vehicle makes → certain brands dominate in certain markets
- Phone number format → country code
- Domain extensions → country

STEP 3 — NARROW THE REGION/CITY:
- Specific business names, street names, area codes
- Mountain/coastline shape matching
- Architectural sub-style (varies within countries)
- Climate indicators (north vs south of a country)
- Urban vs rural indicators

STEP 4 — PINPOINT COORDINATES:
Use your knowledge of the specific area to estimate GPS coordinates. \
Don't just guess the city center — try to match the specific neighborhood \
or street type visible in the image.

Clues from image analysis:
{clues_json}

Generate exactly 3 ranked hypotheses. Make them MEANINGFULLY DIFFERENT — \
not 3 cities in the same country unless the evidence overwhelmingly points \
to one country. Consider alternatives.

For each hypothesis, be HONEST about confidence. Don't inflate scores. \
Use this scale:
- 90-100%: You can practically read the address
- 70-89%: Strong evidence for this specific location
- 50-69%: Good evidence for country, uncertain about city
- 30-49%: Educated guess based on limited clues
- 0-29%: Mostly speculation

Return a JSON array of 3 hypothesis objects:
[
  {{
    "rank": 1,
    "country": "full country name",
    "region": "state/province/region",
    "city": "city or town name",
    "latitude": 0.0,
    "longitude": 0.0,
    "confidence_pct": 75,
    "reasoning": "detailed chain of reasoning linking specific clues to this location",
    "confirming_evidence": ["specific evidence that supports this"],
    "refuting_evidence": ["anything that argues against this"]
  }}
]

Return ONLY valid JSON, no markdown fences or extra text."""


async def generate_hypotheses(clues: VisualClues) -> list[Hypothesis]:
    clues_json = clues.model_dump_json(indent=2)
    prompt = HYPOTHESIS_PROMPT.format(clues_json=clues_json)

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    for attempt in range(2):
        kwargs = dict(
            model=settings.MODEL_HEAVY,
            max_tokens=settings.THINKING_BUDGET + 4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if attempt == 0:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": settings.THINKING_BUDGET,
            }
        else:
            kwargs["max_tokens"] = 4096

        response = await client.messages.create(**kwargs)
        raw_text = get_text_from_response(response)
        try:
            data = extract_json_array(raw_text)
            return [Hypothesis(**h) for h in data]
        except Exception:
            if attempt == 0:
                continue
            raise
