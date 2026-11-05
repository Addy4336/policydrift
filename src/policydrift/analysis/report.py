"""Tables and figures for the paper: label distributions, H1, H2, H3 and per-fact breakdowns."""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from policydrift.analysis.data import Row
from policydrift.analysis.stats import (
    cluster_bootstrap_ci,
    holm,
    mcnemar_one_sided,
)

LABELS = ("current", "outdated", "refusal", "other")
TAU = 0.02  # preregistration §5
MITIGATIONS = ("M-a1", "M-a2", "M-b")  # confirmatory at R3 (§7)
NAN = float("nan")


def pct(x: float) -> str:
    return "n/a" if x != x else f"{100 * x:.1f}%"


def md_table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def _select(
    rows: Iterable[Row], *, mitigation: str, condition: str, model: str | None = None
) -> list[Row]:
    return [
        r
        for r in rows
        if r.mitigation == mitigation
        and r.condition == condition
        and (model is None or r.model == model)
        and r.answered
    ]


def outdated(rows: Sequence[Row]) -> list[float]:
    return [1.0 if r.label == "outdated" else 0.0 for r in rows]


def _rate(rows: Sequence[Row], label: str) -> float:
    return sum(r.label == label for r in rows) / len(rows) if rows else NAN


def label_distribution(rows: Sequence[Row]) -> str:
    groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    for r in rows:
        groups[(r.mitigation, r.condition, r.model)].append(r)
    body = []
    for (mit, cond, model), g in sorted(groups.items()):
        c = Counter(r.label for r in g)
        n = sum(c[label] for label in LABELS)
        body.append(
            [
                mit,
                cond,
                model,
                n,
                *[c[label] for label in LABELS],
                c["missing"] + c["unresolved"],
                pct(c["outdated"] / n if n else NAN),
            ]
        )
    return md_table(["mitigation", "cond", "model", "n", *LABELS, "missing", "outdated rate"], body)


def h1_table(rows: Sequence[Row]) -> str:
    """Pooled outdated rate per condition, fact-cluster bootstrap CI, and the tau rule."""
    out = []
    for cond in ("R2", "R3"):
        g = _select(rows, mitigation="none", condition=cond)
        if not g:
            continue
        rate, lo, hi = cluster_bootstrap_ci(outdated(g), [r.fact_id for r in g])
        out.append(
            [cond, len(g), pct(rate), f"[{pct(lo)}, {pct(hi)}]", "yes" if lo > TAU else "no"]
        )
    text = md_table(
        [
            "condition",
            "n",
            "outdated rate",
            "95% CI (bootstrap over facts)",
            f"CI lower > {TAU:.0%}",
        ],
        out,
    )
    per_model = []
    for cond in ("R0", "R1", "R2", "R3", "R4"):
        for model in sorted({r.model for r in rows}):
            g = _select(rows, mitigation="none", condition=cond, model=model)
            if g:
                per_model.append([cond, model, len(g), pct(sum(outdated(g)) / len(g))])
    return (
        text
        + "\nPer model:\n\n"
        + md_table(["condition", "model", "n", "outdated rate"], per_model)
    )


def _pairs(a: Sequence[Row], b: Sequence[Row]) -> list[tuple[Row, Row]]:
    index = {r.key: r for r in b}
    return [(r, index[r.key]) for r in a if r.key in index]


def h2_table(rows: Sequence[Row]) -> str:
    """hi and gu against en on R2 + R3 baseline answers: exact McNemar (prespecified fallback)."""
    base = [
        r for r in rows if r.mitigation == "none" and r.condition in {"R2", "R3"} and r.answered
    ]
    by_lang: dict[str, dict[tuple[str, str, str], Row]] = {"en": {}, "hi": {}, "gu": {}}
    for r in base:
        by_lang[r.language][(r.model, r.item_id, r.condition)] = r
    body: list[list[object]] = []
    ps: list[float] = []
    for lang in ("hi", "gu"):
        worse = better = 0
        diffs: list[float] = []
        clusters: list[str] = []
        for k, e in by_lang["en"].items():
            o = by_lang[lang].get(k)
            if o is None:
                continue
            ev, ov = e.label == "outdated", o.label == "outdated"
            worse += ov and not ev
            better += ev and not ov
            diffs.append(float(ov) - float(ev))
            clusters.append(e.fact_id)
        p = mcnemar_one_sided(worse, better)  # H2: the other language is worse
        ps.append(p)
        d, lo, hi = cluster_bootstrap_ci(diffs, clusters)
        body.append(
            [f"{lang} vs en", len(diffs), f"{worse} / {better}", pct(d), f"[{pct(lo)}, {pct(hi)}]"]
        )
    for row, p, q in zip(body, ps, holm(ps), strict=True):
        row += [f"{p:.4f}", f"{q:.4f}"]
    rates = []
    for lang in ("en", "hi", "gu"):
        g = [r for r in base if r.language == lang]
        rates.append([lang, len(g), pct(sum(outdated(g)) / len(g)) if g else "n/a"])
    note = (
        "\nMixed-effects logistic regression (preregistration §6) is not fitted here; the "
        "prespecified fallback (exact McNemar on paired item x model x condition outcomes, "
        "Holm) is reported.\n"
    )
    return (
        md_table(["language", "n", "outdated rate"], rates)
        + "\n"
        + md_table(
            [
                "contrast",
                "pairs",
                "other worse / en worse",
                "rate diff",
                "95% CI (facts)",
                "p (one-sided)",
                "p Holm",
            ],
            body,
        )
        + note
    )


def _latency(rows: Sequence[Row]) -> str:
    xs = sorted(r.latency_s for r in rows if r.cached is False and r.latency_s is not None)
    if not xs:
        return "n/a"
    p90 = xs[min(len(xs) - 1, int(0.9 * len(xs)))]
    return f"{statistics.median(xs):.1f} / {p90:.1f}"


def h3_table(rows: Sequence[Row], condition: str = "R3") -> str:
    """Each mitigation against the baseline at ``condition``, on matched answers."""
    base_all = _select(rows, mitigation="none", condition=condition)
    stats: list[dict[str, object]] = []
    ps: list[float] = []
    for mit in MITIGATIONS:
        m_all = _select(rows, mitigation=mit, condition=condition)
        pairs = _pairs(m_all, base_all)
        if not pairs:
            continue
        ms, bs = [m for m, _ in pairs], [b for _, b in pairs]
        fixed = sum(b.label == "outdated" and m.label != "outdated" for m, b in pairs)
        broke = sum(m.label == "outdated" and b.label != "outdated" for m, b in pairs)
        diffs = [float(m.label == "outdated") - float(b.label == "outdated") for m, b in pairs]
        d, lo, hi = cluster_bootstrap_ci(diffs, [m.fact_id for m in ms])
        ps.append(mcnemar_one_sided(fixed, broke))
        tokens = statistics.mean(m.tokens for m in ms)
        base_tokens = statistics.mean(b.tokens for b in bs) or 1.0
        stats.append(
            {
                "row": [
                    mit,
                    len(pairs),
                    pct(sum(outdated(bs)) / len(bs)),
                    pct(sum(outdated(ms)) / len(ms)),
                    f"{fixed} / {broke}",
                    f"{pct(d)} [{pct(lo)}, {pct(hi)}]",
                ],
                "tail": [
                    f"{pct(_rate(ms, 'refusal'))} (base {pct(_rate(bs, 'refusal'))})",
                    f"{pct(_rate(ms, 'current'))} (base {pct(_rate(bs, 'current'))})",
                    f"{statistics.mean(m.calls for m in ms):.2f}",
                    f"{tokens:.0f} ({tokens / base_tokens:.1f}x)",
                    _latency(m_all),
                ],
            }
        )
    adjusted = holm(ps)
    table = [
        [*s["row"], f"{p:.4f}", f"{q:.4f}", *s["tail"]]  # type: ignore[misc]
        for s, p, q in zip(stats, ps, adjusted, strict=True)
    ]
    return md_table(
        [
            "mitigation",
            "n",
            "baseline",
            "with",
            "fixed / broke",
            "change [95% CI, facts]",
            "p (one-sided)",
            "p Holm",
            "refusals",
            "current",
            "calls",
            "tokens/answer",
            "latency median / p90 s (uncached)",
        ],
        table,
    )


def r1_descriptive_table(rows: Sequence[Row]) -> str:
    """Descriptive R1 results for every mitigation, including M-c (preregistration §2)."""
    base = _select(rows, mitigation="none", condition="R1")
    out = []
    for mit in ("M-a1", "M-a2", "M-b", "M-c"):
        pairs = _pairs(_select(rows, mitigation=mit, condition="R1"), base)
        if not pairs:
            continue
        ms, bs = [m for m, _ in pairs], [b for _, b in pairs]
        out.append(
            [
                mit,
                len(pairs),
                pct(sum(outdated(bs)) / len(bs)),
                pct(sum(outdated(ms)) / len(ms)),
                pct(_rate(ms, "refusal")),
                f"{statistics.mean(m.tokens for m in ms):.0f}",
            ]
        )
    return md_table(
        ["mitigation (R1, descriptive)", "n", "baseline", "with", "refusals", "tokens/answer"], out
    )


def per_fact_table(rows: Sequence[Row]) -> str:
    body = []
    for f in sorted({r.fact_id for r in rows}):
        cells: list[object] = [f]
        for cond in ("R1", "R3"):
            g = [r for r in _select(rows, mitigation="none", condition=cond) if r.fact_id == f]
            cells.append(f"{sum(outdated(g)):.0f}/{len(g)}" if g else "n/a")
        r1 = [r for r in _select(rows, mitigation="none", condition="R1") if r.fact_id == f]
        known = [r.has_current for r in r1 if r.has_current is not None]
        cells.append(f"{sum(known)}/{len(known)}" if known else "n/a")
        body.append(cells)
    return md_table(
        ["fact", "R1 outdated", "R3 outdated", "R1 current chunk retrieved (k=4)"], body
    )


def write_csv(path: Path, rows: Sequence[Row]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            [
                "run",
                "model",
                "language",
                "condition",
                "mitigation",
                "item_id",
                "fact_id",
                "label",
                "calls",
                "tokens",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.run,
                    r.model,
                    r.language,
                    r.condition,
                    r.mitigation,
                    r.item_id,
                    r.fact_id,
                    r.label,
                    r.calls,
                    r.tokens,
                ]
            )


def figures(rows: Sequence[Row], out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    written: list[Path] = []
    conds = [
        c for c in ("R0", "R1", "R2", "R3", "R4") if _select(rows, mitigation="none", condition=c)
    ]
    width = 0.25
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for j, lang in enumerate(("en", "hi", "gu")):
        vals = []
        for c in conds:
            g = [r for r in _select(rows, mitigation="none", condition=c) if r.language == lang]
            vals.append(100 * sum(outdated(g)) / len(g) if g else 0)
        ax.bar([i + (j - 1) * width for i in range(len(conds))], vals, width, label=lang)
    ax.set_xticks(range(len(conds)), conds)
    ax.set_ylabel("outdated answers (%)")
    ax.set_title("Outdated-answer rate by condition and question language")
    ax.legend(title="language", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = out_dir / "fig_outdated_by_condition.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(6, 3.8))
    for name, mit in (("no mitigation", "none"), *((m, m) for m in MITIGATIONS)):
        g = _select(rows, mitigation=mit, condition="R3")
        if g:
            ax.scatter(
                [statistics.mean(r.tokens for r in g)],
                [100 * sum(outdated(g)) / len(g)],
                label=name,
            )
    ax.set_xlabel("tokens per answer")
    ax.set_ylabel("outdated answers (%) at R3")
    ax.set_title("Mitigation cost against outdated rate")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = out_dir / "fig_mitigation_tradeoff.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    written.append(path)
    return written


def build_paper(rows: Sequence[Row], out_dir: Path, title: str) -> list[Path]:
    tables = out_dir / "tables"
    figs = out_dir / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    parts = {
        "label_distribution": label_distribution(rows),
        "h1": h1_table(rows),
        "h2": h2_table(rows),
        "h3_r3": h3_table(rows, "R3"),
        "mitigations_r1_descriptive": r1_descriptive_table(rows),
        "per_fact": per_fact_table(rows),
    }
    written: list[Path] = []
    for name, text in parts.items():
        path = tables / f"{name}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    write_csv(tables / "answers.csv", rows)
    summary = f"# {title}\n\n" + "\n".join(f"## {n}\n\n{t}" for n, t in parts.items())
    (out_dir / "results.md").write_text(summary, encoding="utf-8", newline="\n")
    written.append(out_dir / "results.md")
    written += figures(rows, figs)
    return written
