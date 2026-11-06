# Final test run: how to resume and finish

State at 2026-11-06: preregistration frozen (tag `prereg-freeze`), final configs in `configs/final/`, gpt-oss-20b dropped (see the deviation log in `docs/preregistration.md`). Ten configs remain: baseline R0-R3, M-a1, M-a2, M-b at R3 and M-c at R1, for `gemini-flash-lite` and `gemini-35-flash-lite`. Each config is run by `policydrift run configs/final/<name>.yaml --final`. The cache holds every answer already received, so a restart costs nothing.

1. Run the driver. It waits until the Gemini daily quota resets (08:05 UTC, 13:35 IST), runs the ten configs (two models in parallel), reruns any config that has missing answers (quota errors), then scores every run, writes `paper/runs.test.yaml` and builds `paper/test/`. It can be stopped and restarted at any time; the cache keeps every answer already received.

```bash
uv run --no-sync python scripts/finish_final.py
```

2. Keep the laptop awake and plugged in (Windows: Settings, System, Power, set sleep to Never). Check `.cache/finish_final.log` for progress; it prints one line per config.

3. When the log says `done`, read `paper/test/results.md`. The primary H1 and H3 tables count answers whose context states the current value; the `_all_answers` tables are the sensitivity analysis. Then commit `paper/test` and `paper/runs.test.yaml`.

Expected time: about 3 hours of uninterrupted running at the Gemini free-tier limit (8 requests a minute per model) after the quota reset. If a daily request cap is lower than the roughly 1,500 calls a model needs, the driver waits 30 minutes between attempts and will take until the next reset. Nothing in `paper/test` may be used to change prompts, mitigations, thresholds or the scorer; changes after this point go in the deviation log.
