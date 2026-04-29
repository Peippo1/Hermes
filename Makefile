.PHONY: test test-backend build-frontend

test:
	pytest

test-backend:
	pytest

build-frontend:
	cd frontend && npm run build
