# Agent Quality Lab · v2

An evaluation engineering project with a real asynchronous service, durable workers, live model adapters, and regression gates. Built to practice backend and applied AI engineering with inspectable code and failure tests.

## Run locally

A local `.env` has already been generated for this checkout. Keep it private; skip initialization unless setting up a fresh copy.

From this directory, use Python 3.9+ (3.12 recommended):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
python scripts/init_local.py  # Only if .env does not already exist
set -a
source .env
set +a
python -m uvicorn platform_lab.api:app --host 127.0.0.1 --port 8765
```

In a second terminal, from the same directory:

```sh
source .venv/bin/activate
set -a
source .env
set +a
python -m platform_lab.worker
```

Open http://127.0.0.1:8765, paste the random token from `.env`, and queue an offline run. Refresh after the worker completes. API documentation: http://127.0.0.1:8765/docs. Stop any earlier simulator server using port 8765 first.

Alternatively, after creating `.env`: `docker compose up --build`. Containers run as an unprivileged user, with a shared persistent volume and API readiness probe. Compose is a single-host development deployment.

## What changed from v1

| Area | Implemented in v2 |
|---|---|
| Service | FastAPI, validated request schemas, bearer tokens mapped to tenants, request IDs |
| Jobs | Durable SQLite queue, atomic claims, renewable leases, stale-worker fencing, bounded recovery |
| Results | Idempotent case writes, resume completed cases, tenant-scoped inspection, cancellation |
| Agent | Authorized lexical retrieval from actual source text, JSON answer contract, explicit abstention |
| Providers | OpenAI Responses and Anthropic Messages adapters, usage capture, deadlines and selective retries |
| Evaluation | Deterministic checks plus optional structured live judge; invalid responses fail runs |
| Experiments | Dataset/prompt/code fingerprints, paired cluster bootstrap, safety gates and minimum sample gate |
| Improvement | One live model-generated prompt candidate, dev-only evaluation, comparison and lineage artifact |
| Calibration | Binary judge-versus-human confusion matrix and false-pass/false-fail rates |
| Delivery | Pinned dependencies, CI, Docker Compose, integration/failure tests and operating notes |

The original `quality_lab` simulator remains available as a separate introductory exercise. All new development belongs in `platform_lab`.

## Live evaluation

Set `LAB_ALLOW_LIVE=1` for both API and worker. Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the worker environment. Use a model identifier available to your account; the project does not assume access to a particular model. Restart the processes after configuration changes.

Select the provider and model in the dashboard, or submit to `POST /v1/runs` with `Authorization: Bearer ...` and a unique `Idempotency-Key` header. Optional `judge_provider` and `judge_model` fields enable semantic evaluation through the API. Judge usage is recorded separately. No keys were needed or used during local verification.

```json
{
  "provider": "openai",
  "model": "YOUR_MODEL_ID",
  "split": "dev",
  "repeats": 3,
  "judge_provider": "anthropic",
  "judge_model": "YOUR_JUDGE_MODEL_ID",
  "prompt": "Answer with source-backed facts and explicitly abstain when evidence is missing."
}
```

To run one bounded prompt improvement experiment, set `LAB_CLIENT_TOKEN` to your local API token and configure the proposer's provider key in this terminal:

```sh
python -m platform_lab.experiments improve --provider openai --model YOUR_MODEL_ID
```

This makes paid live calls: two development evaluation runs plus one proposer call (and bounded retries). It records lineage in `var/`, uses no holdout data, and never deploys a candidate. It limits candidates/calls, not dollar spend; use provider account limits for a financial cap.

Calibrate a judge with independently adjudicated JSONL records containing boolean `human_pass` and `judge_pass` fields:

```sh
python -m platform_lab.experiments calibrate annotations.jsonl
```

## Verify

```sh
python -m pytest -q
```

Tests cover API isolation, conflicting idempotency keys, concurrent claims, lease recovery, cancellation fencing, output validation, provider retries and contracts, and statistical gates. Live integrations use HTTP mocks in tests; credentials and live endpoint behavior still need smoke testing with your account.

## Honest operating boundary

This is a substantial engineering foundation, not evidence of production readiness. SQLite supports this single-host deployment; do not place the database on network storage or claim horizontal multi-host scale. The 16 synthetic scenarios are independent across split entities but not a representative benchmark. Runs with fewer than 20 independent clusters cannot pass the promotion gate; even 20 is a guard, not a power calculation. Offline extraction deliberately exposes injection failures. Quality needs a larger independently labeled dataset and judge calibration.

There is no automatic model routing/fallback policy yet: an evaluation stays on its requested provider so outages cannot silently contaminate a benchmark. A serving gateway with explicit fallback accounting is a next milestone. Pricing, cloud deployment, OIDC, distributed storage, online A/B assignment, full telemetry export, and formal security review remain work to do. See `docs/OPERATIONS.md` and `docs/V2_LEARNING_PATH.md`.

## Provider references

Adapters follow [OpenAI text generation](https://developers.openai.com/api/docs/guides/text) and [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create). API testing uses [FastAPI TestClient](https://fastapi.tiangolo.com/advanced/testing-events/). Verify your chosen model's schema and access before live evaluation.
