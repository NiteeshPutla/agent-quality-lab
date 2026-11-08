test:
	python -m pytest -q
api:
	python -m uvicorn platform_lab.api:app --host 127.0.0.1 --port 8765
worker:
	python -m platform_lab.worker
legacy-demo:
	python -m quality_lab demo
