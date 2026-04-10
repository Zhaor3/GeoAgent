from __future__ import annotations

import json

import anthropic

from geo_agent.config import settings
from geo_agent.models.schemas import Hypothesis, VisualClues
from geo_agent.utils.image import detect_media_type, image_to_base64, resize_image
from geo_agent.utils.parse import extract_json_array, get_text_from_response

VERIFY_PROMPT = """\
You are a world-class geolocation expert performing a VERIFICATION check.

An AI system analyzed a photo and produced these location hypotheses:

{hypotheses_json}

Based on these extracted visual clues:

{clues_summary}

Now LOOK AT THE ORIGINAL IMAGE AGAIN with these hypotheses in mind.

Your job is to act as a critical reviewer:

1. For EACH hypothesis, look at the image and ask:
   - Does the architecture actually match this location?
   - Would you see these exact road markings/signs in this country?
   - Do the license plates match the claimed country?
   - Does the vegetation match the climate of this location?
   - Are the brand names / chains actually present in this country?
   - Does ANYTHING in the image contradict this hypothesis?

2. Look for OVERLOOKED DETAILS that might change everything:
   - Any text you can now read knowing the likely language?
   - Any small sign or logo that confirms or denies a hypothesis?
   - Street furniture details that are wrong for the claimed location?

3. Assign REVISED confidence scores and optionally adjust the location.
   If you think a hypothesis is in the right country but wrong city, fix it.
   If you think the ranking is wrong, re-rank.

Return a JSON array of the 3 hypotheses with revised data:
[
  {{
    "rank": 1,
    "country": "country (adjusted if needed)",
    "region": "region (adjusted if needed)",
    "city": "city (adjusted if needed)",
    "latitude": 0.0,
    "longitude": 0.0,
    "confidence_pct": 75,
    "reasoning": "updated reasoning incorporating verification findings",
    "confirming_evidence": ["evidence from re-examination"],
    "refuting_evidence": ["contradictions found"]
  }}
]

Be BRUTALLY HONEST. If a hypothesis is wrong, say so and fix it. \
If you spot a clue everyone missed, use it.

Return ONLY valid JSON, no markdown fences or extra text."""


async def verify_hypotheses_with_image(
    image_bytes: bytes,
    hypotheses: list[Hypothesis],
    clues: VisualClues,
) -> list[Hypothesis]:
    resized = resize_image(image_bytes)
    b64 = image_to_base64(resized)
    media_type = detect_media_type(resized)

    hyp_json = json.dumps([h.model_dump() for h in hypotheses], indent=2)
    clues_summary = clues.overall_impression

    prompt_text = VERIFY_PROMPT.format(
        hypotheses_json=hyp_json,
        clues_summary=clues_summary,
    )

    image_block = {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": b64},
    }

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    for attempt in range(2):
        kwargs = dict(
            model=settings.MODEL_HEAVY,
            max_tokens=settings.THINKING_BUDGET + 4096,
            messages=[
                {
                    "role": "user",
                    "content": [image_block, {"type": "text", "text": prompt_text}],
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

        response = await client.messages.create(**kwargs)
        raw_text = get_text_from_response(response)
        try:
            data = extract_json_array(raw_text)
            verified = [Hypothesis(**h) for h in data]
            verified.sort(key=lambda h: h.confidence_pct, reverse=True)
            for i, h in enumerate(verified):
                h.rank = i + 1
            return verified
        except Exception:
            if attempt == 0:
                continue
            raise
