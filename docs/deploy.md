# Deploying the demo on free tiers

The API runs on a **Hugging Face Space** (Docker SDK, free CPU: 2 vCPU, 16 GB RAM, which fits the
embedding model) and the web app on **Vercel** (Hobby). Answers use Groq's free API. Nothing here
needs a paid plan.

## API: Hugging Face Space

1. Create a Space at https://huggingface.co/new-space: SDK **Docker**, hardware **CPU basic (free)**.
2. In the Space settings add the secret `GROQ_API_KEY`, and the variable
   `POLICYDRIFT_CORS=https://<your-vercel-app>.vercel.app`.
3. Push this repository to the Space. The Space reads `Dockerfile` at the root; its README needs the
   front matter below, so create the Space's README with it when you create the Space:

```yaml
---
title: PolicyDrift API
sdk: docker
app_port: 7860
---
```

```bash
git remote add space https://huggingface.co/spaces/<user>/policydrift-api
git push space main
```

The build downloads the model and embeds the 440 chunks once (a few minutes). Check
`https://<user>-policydrift-api.hf.space/api/health`. Free Spaces sleep after a period of
inactivity and wake on the next request (about a minute).

## Web: Vercel

1. Import the repository in Vercel, set **Root Directory** to `web`.
2. Set `NEXT_PUBLIC_API_URL=https://<user>-policydrift-api.hf.space`.
3. Deploy. To publish a demo without a running backend, set `NEXT_PUBLIC_DEMO_FIXTURES=1` instead.

## Local container check

```bash
docker build -t policydrift-api .
docker run -p 7860:7860 -e GROQ_API_KEY=... policydrift-api
```
