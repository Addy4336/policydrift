# Final test run: how to resume and finish

State at 2026-11-06: preregistration frozen (tag `prereg-freeze`), final configs in `configs/final/`, gpt-oss-20b dropped (see the deviation log in `docs/preregistration.md`). Ten configs remain: baseline R0-R3, M-a1, M-a2, M-b at R3 and M-c at R1, for `gemini-flash-lite` and `gemini-35-flash-lite`. Each config is run by `policydrift run configs/final/<name>.yaml --final`. The cache holds every answer already received, so a restart costs nothing.

1. Start (or restart after a sleep or reboot) both model chains, one per model so each rate limit is respected:

```bash
bash .cache/final_run_gemini.sh
```

2. In another terminal, run the finisher. It waits for the runs, scores each one (matcher, then the Groq judge), writes `paper/runs.test.yaml` and builds `paper/test/` (tables, figures, `results.md`):

```bash
uv run --no-sync python scripts/finish_final.py
```

3. Read `paper/test/results.md`. The primary H1 and H3 tables count answers whose context states the current value; the `_all_answers` tables are the sensitivity analysis. Then commit `paper/test` and `paper/runs.test.yaml`.

Expected time: about 3 hours of uninterrupted running at the Gemini free-tier limit (8 requests a minute per model). Nothing in `paper/test` may be used to change prompts, mitigations, thresholds or the scorer; changes after this point go in the deviation log.
