from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def explain(self, metrics: dict, evidence: list[dict]) -> list[dict]: ...
