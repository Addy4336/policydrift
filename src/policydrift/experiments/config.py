"""YAML experiment configuration: one file, one command, explicit seed."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Condition = Literal["R0", "R1", "R2", "R3", "R4", "X"]
Language = Literal["en", "hi", "gu"]
PassageOrder = Literal["current_first", "old_first", "counterbalanced"]


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    split: Literal["dev", "test"] = "dev"  # the test split also needs --final on the command line
    models: list[str]  # keys in configs/models.yaml
    languages: list[Language] = ["en", "hi", "gu"]
    conditions: list[Condition]
    mitigation: Literal["none"] = "none"  # Phase 4 adds M-a1, M-a2, M-b, M-c
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


def load_config(path: Path) -> ExperimentConfig:
    with path.open(encoding="utf-8") as f:
        return ExperimentConfig.model_validate(yaml.safe_load(f))
