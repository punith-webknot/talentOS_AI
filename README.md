# talentOS AI

FastAPI service for recruitment chat agents, resume evaluation, and MCP-backed job operations.

## LLM provider switch

The service supports multiple LLM providers via `LLM_PROVIDER` in `.env`:

| `LLM_PROVIDER` | API key env var   | Default base URL                    |
|----------------|-------------------|-------------------------------------|
| `openai`       | `OPENAI_API_KEY`  | `https://api.openai.com/v1`         |
| `groq`         | `GROQ_API_KEY`    | `https://api.groq.com/openai/v1`    |

- Flip `LLM_PROVIDER=openai|groq` to switch providers — no code changes needed.
- Optional per-provider base URL overrides: `OPENAI_BASE_URL`, `GROQ_BASE_URL`.
- Model names fall back to per-provider defaults when `MODEL_NAME` /
  `EVALUATION_MODEL_NAME` are unset:
  - OpenAI: `gpt-5.4-mini` / `gpt-5.4-nano`
  - Groq: `openai/gpt-oss-120b` / `openai/gpt-oss-20b`

## Run locally

```bash
docker build -t talentos-ai .
docker run --rm --env-file .env -p 8001:8000 talentos-ai
```

