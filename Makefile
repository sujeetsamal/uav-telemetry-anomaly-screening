.PHONY: install test test-perf api web build-web clean

install:
	pip install -r requirements.txt
	cd web && npm install

test:
	python -m pytest tests -v

test-perf:
	python -m pytest tests/test_performance.py -v

api:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd web && npm run dev

build-web:
	cd web && npm run build

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]"
