# Deploying the demo on free tiers

Live: web https://policydrift-lime.vercel.app, API https://policydrift-api.vercel.app (`/api/health`).

Both run on Vercel's free Hobby plan as two projects. The API is a Python (FastAPI) function. A
serverless function cannot load the e5-base embedding model, so the hosted demo uses the BM25
retriever in `src/policydrift/demo/lexical.py`; questions in Hindi and Gujarati are translated and
routed to a scheme first. The research experiments always use e5-base.

## API (`policydrift-api`)

```bash
uv run --no-sync python scripts/build_api_bundle.py      # writes deploy/vercel-api/ (about 1 MB)
cd deploy/vercel-api && npx vercel deploy --prod --yes --name policydrift-api
```

Project environment variables (Vercel dashboard, Settings, Environment Variables):

| Name | Value |
|---|---|
| `GROQ_API_KEY` | your Groq key (type Sensitive). Add it yourself; it is never stored in the repository |
| `POLICYDRIFT_CORS` | `https://policydrift-lime.vercel.app,http://localhost:3000` |

The bundle sets `POLICYDRIFT_RETRIEVER=lexical` and keeps the LLM cache in `/tmp`. After changing an
environment variable, redeploy with the command above.

## Web (`policydrift`)

```bash
cd web && npx vercel deploy --prod --yes --name policydrift --build-env NEXT_PUBLIC_API_URL=https://policydrift-api.vercel.app
```

`NEXT_PUBLIC_API_URL` is also stored on the project for later builds.

## Alternative: Hugging Face Space with the dense retriever

The `Dockerfile` at the root builds the API with e5-base for a free Hugging Face Space (Docker SDK,
CPU basic, port 7860; add `GROQ_API_KEY` as a Space secret). It has not been built yet.
