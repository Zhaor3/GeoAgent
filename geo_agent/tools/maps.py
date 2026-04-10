from __future__ import annotations

import httpx

from geo_agent.config import settings
from geo_agent.models.schemas import Hypothesis, ToolResult, VisualClues
from geo_agent.tools.base import VerificationTool


class GoogleMapsPlacesTool(VerificationTool):
    name = "Google Places"

    async def verify(self, hypothesis: Hypothesis, clues: VisualClues) -> ToolResult:
        if not settings.GOOGLE_MAPS_API_KEY:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="Google Maps API key not configured",
            )

        search_terms = []
        df = clues.distinctive_features
        search_terms.extend(df.get("brand_names", []))
        search_terms.extend(df.get("landmarks", []))
        ts = clues.text_and_signage
        for text in ts.get("visible_text", [])[:3]:
            if len(text) > 2:
                search_terms.append(text)

        if not search_terms:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="No searchable terms extracted from image",
            )

        total_delta = 0.0
        evidence_parts = []

        async with httpx.AsyncClient(timeout=15) as client:
            for term in search_terms[:3]:
                try:
                    resp = await client.get(
                        "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                        params={
                            "location": f"{hypothesis.latitude},{hypothesis.longitude}",
                            "radius": 5000,
                            "keyword": term,
                            "key": settings.GOOGLE_MAPS_API_KEY,
                        },
                    )
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        total_delta += 10
                        evidence_parts.append(f"Found '{term}' near coords ({len(results)} results)")
                    else:
                        total_delta -= 5
                        evidence_parts.append(f"No '{term}' found near coords")
                except Exception as e:
                    evidence_parts.append(f"Places search error for '{term}': {e}")

        total_delta = max(-30.0, min(30.0, total_delta))
        supports = total_delta > 0

        return ToolResult(
            tool_name=self.name,
            hypothesis_rank=hypothesis.rank,
            supports=supports,
            confidence_delta=total_delta,
            evidence_summary="; ".join(evidence_parts) if evidence_parts else "No evidence gathered",
        )


class GoogleGeocodingTool(VerificationTool):
    name = "Reverse Geocode"

    async def verify(self, hypothesis: Hypothesis, clues: VisualClues) -> ToolResult:
        if not settings.GOOGLE_MAPS_API_KEY:
            return ToolResult(
                tool_name=self.name,
                hypothesis_rank=hypothesis.rank,
                supports=False,
                confidence_delta=0,
                evidence_summary="Google Maps API key not configured",
            )

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={
                        "latlng": f"{hypothesis.latitude},{hypothesis.longitude}",
                        "key": settings.GOOGLE_MAPS_API_KEY,
                    },
                )
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    return ToolResult(
                        tool_name=self.name,
                        hypothesis_rank=hypothesis.rank,
                        supports=False,
                        confidence_delta=-5,
                        evidence_summary="No geocoding results for coordinates",
                    )

                address = results[0].get("formatted_address", "")
                components = results[0].get("address_components", [])
                country_match = False
                for comp in components:
                    if "country" in comp.get("types", []):
                        if comp["long_name"].lower() == hypothesis.country.lower():
                            country_match = True

                if country_match:
                    return ToolResult(
                        tool_name=self.name,
                        hypothesis_rank=hypothesis.rank,
                        supports=True,
                        confidence_delta=5,
                        evidence_summary=f"Reverse geocode confirms country — {address}",
                        raw_data={"address": address},
                    )
                else:
                    return ToolResult(
                        tool_name=self.name,
                        hypothesis_rank=hypothesis.rank,
                        supports=False,
                        confidence_delta=-10,
                        evidence_summary=f"Reverse geocode mismatch — got {address}",
                        raw_data={"address": address},
                    )
            except Exception as e:
                return ToolResult(
                    tool_name=self.name,
                    hypothesis_rank=hypothesis.rank,
                    supports=False,
                    confidence_delta=0,
                    evidence_summary=f"Geocoding error: {e}",
                )
