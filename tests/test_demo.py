"""Citation validation and the demo agent (no network: retriever and LLM are stubbed)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from policydrift.citations import cited_ids, validate
from policydrift.demo import DemoService
from policydrift.ingest.build import Chunk
from policydrift.llm import LLMRequest, LLMResponse
from policydrift.retrieval.search import Filters, Hit, chunk_matches


def test_cited_ids_order_and_groups() -> None:
    assert cited_ids("Rs 25,000 [2]. Also [1, 3] and again [2]") == [2, 1, 3]
    assert cited_ids("no markers") == []


def test_odd_marker_styles_are_normalised() -> None:
    from policydrift.citations import normalise_markers

    assert normalise_markers("Rs 15,000【4】 and 【1, 2】 and [3†source]") == (
        "Rs 15,000[4] and [1, 2] and [3]"
    )
    assert validate("Rs 15,000【1】", ["Loan of Rs 15,000."]).numbers_verified


def test_validate_checks_markers_and_numbers() -> None:
    passages = ["The loan is Rs 25,000 for the second tranche.", "Rate is 12.5 per cent."]
    good = validate("The second loan is ₹25,000 [1].", passages)
    assert good.citations_valid and good.numbers_verified
    assert good.numbers[0].cited_in == [1]
    bad = validate("It is Rs 30,000 [3].", passages)
    assert bad.invalid_markers == [3] and not bad.citations_valid
    assert not bad.numbers_verified
    uncited = validate("It is Rs 25,000.", passages)
    assert uncited.uncited and not uncited.numbers[0].verified
    assert not validate("The passages do not contain this.", passages, says_no_answer=True).uncited


def test_validate_reads_indian_digits_and_lakh() -> None:
    passages = ["Loans up to Rs 20 lakh under Tarun Plus."]
    hi = validate("तरुण प्लस के तहत ₹२०,००,००० तक [1]", passages)  # noqa: RUF001
    assert hi.numbers and hi.numbers_verified


def _chunk(cid: str, version: str, start: date, end: date | None, text: str) -> Chunk:
    return Chunk.model_construct(
        chunk_id=cid,
        scheme="pm-svanidhi",
        version=version,
        effective_from=start,
        effective_to=end,
        language="en",
        title=f"PM SVANidhi {version}",
        source_url="https://pib.gov.in/x",
        posted_on=start,
        ministry="MoHUA",
        text=text,
    )


OLD = _chunk("s:v1:0", "v1", date(2020, 6, 1), date(2025, 7, 31), "First loan of Rs 10,000.")
NEW = _chunk("s:v2:0", "v2", date(2025, 8, 1), None, "First loan raised to Rs 15,000.")


class StubRetriever:
    def search(self, query: str, k: int, flt: Filters | None = None) -> list[Hit]:
        chunks = [c for c in (OLD, NEW) if flt is None or chunk_matches(c, flt)]
        return [Hit(c, 1.0, i) for i, c in enumerate(chunks[:k], start=1)]


class StubClient:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(text="The first loan is Rs 15,000 [1].", provider="groq", model="m")


def _service() -> tuple[DemoService, StubClient]:
    svc = DemoService(Path("."))
    client = StubClient()
    svc._retriever = StubRetriever()  # type: ignore[assignment]
    svc._client = client  # type: ignore[assignment]
    return svc, client


def test_ask_uses_in_force_version_and_flags_the_change() -> None:
    svc, client = _service()
    out = svc.ask("What is the first SVANidhi loan?", "en", date(2026, 11, 1))
    assert [c["version"] for c in out["citations"]] == ["v2"]  # old version filtered out (M-c)
    assert "2026-11-01" in (client.requests[0].system or "")  # date-stamped prompt (M-a1)
    assert out["rule_versions"][0]["version"] == "v2"
    assert out["conflicts"] and out["conflicts"][0]["superseded_version"] == "v1"
    assert out["checks"]["citations_valid"] and out["checks"]["numbers"][0]["verified"]
    assert out["warnings"] == []


def test_ask_on_a_past_date_uses_the_old_version() -> None:
    svc, _ = _service()
    out = svc.ask("What is the first SVANidhi loan?", "en", date(2024, 1, 1))
    assert [c["version"] for c in out["citations"]] == ["v1"]
    assert out["conflicts"][0]["note"].startswith("A newer version (v2)")
    # The stub answer says 15,000, which the v1 passage does not contain.
    assert out["warnings"] and not out["checks"]["numbers"][0]["verified"]


def test_api_endpoints(monkeypatch: Any) -> None:
    import api.main as api

    svc, _ = _service()
    monkeypatch.setattr(api, "service", lambda: svc)
    client = TestClient(api.app)
    assert client.get("/api/health").json()["status"] == "ok"
    r = client.post(
        "/api/ask", json={"question": "First loan?", "language": "hi", "as_of": "2026-11-01"}
    )
    assert r.status_code == 200 and r.json()["language"] == "hi"
    assert client.post("/api/ask", json={"question": "x"}).status_code == 422
    schemes = client.get("/api/schemes").json()
    assert any(s["id"] == "pm-svanidhi" for s in schemes)
    assert set(client.get("/api/examples").json()) == {"en", "hi", "gu"}
    assert "dev" in client.get("/api/results").json()


def test_dates_are_not_checked_as_figures() -> None:
    report = validate(
        "Raised to ₹20 lakh in Budget 2024-25, from 24 October 2024 [1].",
        ["The limit is Rs 20 lakh."],
    )
    assert [n.value for n in report.numbers] == ["2,000,000"] and report.numbers_verified


def test_routing_by_scheme_name_in_any_language() -> None:
    from policydrift.demo.routing import named_schemes

    assert named_schemes("પીએમ સ્વનિધિ યોજના હેઠળ પ્રથમ લોન")[0] == "pm-svanidhi"
    assert named_schemes("PM Swarnidhi first loan")[0] == "pm-svanidhi"
    assert named_schemes("मुद्रा योजना में अधिकतम ऋण")[0] == "pm-mudra"
    assert named_schemes("what is the weather") == []
