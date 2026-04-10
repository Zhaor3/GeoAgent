from __future__ import annotations

from abc import ABC, abstractmethod

from geo_agent.models.schemas import Hypothesis, ToolResult, VisualClues


class VerificationTool(ABC):
    name: str

    @abstractmethod
    async def verify(
        self,
        hypothesis: Hypothesis,
        clues: VisualClues,
    ) -> ToolResult: ...
