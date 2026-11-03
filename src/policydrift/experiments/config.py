"""YAML experiment configuration: one file, one command, explicit seed."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Condition = Literal["R0", "R1", "R2", "R3", "R4", "X"]
Language = Literal["en", "hi", "gu"]
PassageOrder = Literal["current_first", "old_first", "counterbalanced"]
Mitigation = Literal["none", "M-a1", "M-a2", "M-b", "M-c"]


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    split: Literal["dev", "test"] = "dev"  # the test split also needs --final on the command line
    models: list[str]  # keys in configs/models.yaml
    languages: list[Language] = ["en", "hi", "gu"]
    conditions: list[Condition]
    mitigation: Mitigation = "none"
    # "Today" for the mitigations. Fixed in the config so a rerun is reproducible.
    as_of: date = date(2026, 11, 1)
    k: int = Field(default=4, ge=1)  # chunks for R1 and R2
    k_each: int = Field(default=2, ge=1)  # chunks per version for R3, R4 and X
    # "english": every question language is answered over the same English passages, so the
    # language comparison changes only the question. "native": the question's own language where
    # every needed version has a source in it, else English (exploratory).
    doc_language: Literal["english", "native"] = "english"
    passage_order: PassageOrder = "counterbalanced"
    max_tokens: int = Field(default=2048, ge=64)  # reasoning models spend most of it thinking
    # An answer that hits max_tokens with no visible text is retried once with this budget.
    # 0 turns the retry off.
    retry_max_tokens: int = Field(default=8192, ge=0)
    seed: int = 20261101
    item_limit: int = Field(default=0, ge=0)  # 0 = all items; otherwise the first N by item id
    only_confirmatory: bool = False
    judge_model: str = "groq-gpt-oss"

    @model_validator(mode="after")
    def _mitigations_apply_to_retrieval_conditions(self) -> ExperimentConfig:
        allowed = {"R1", "R3"} if self.mitigation != "none" else set(self.conditions)
        if not set(self.conditions) <= allowed:
            raise ValueError(f"{self.mitigation} is only defined for conditions R1 and R3")
        return self


def load_config(path: Path) -> ExperimentConfig:
    with path.open(encoding="utf-8") as f:
        return ExperimentConfig.model_validate(yaml.safe_load(f))
