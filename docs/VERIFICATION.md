# Verification record

Verified locally on 2026-11-08 using Python 3.9.6:

- 23 tests passed, including seven legacy tests and sixteen service tests (parameterized cases included).
- Real localhost HTTP smoke: readiness, dashboard HTML, authenticated submission, separate worker process, completed run with eight persisted results.
- Docker Compose configuration validated.
- Requested excluded company name: zero matches in project source and documentation.

Not verified: paid live API calls, container build/start (Docker daemon unavailable), browser visual/interaction QA, cloud deployment, performance at production load, or calibrated semantic evaluation. HTTP mocks cover both provider wire formats and selected failure paths. Local HTTP checks used temporary credentials/database and stopped test processes afterward.
