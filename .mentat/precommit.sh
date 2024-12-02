# Frontend checks
cd frontend && npm run format && cd ..
cd frontend && npm run lint && cd ..
cd frontend && npm run type-check && cd ..
cd frontend && npm run test:unit && cd ..

# Backend checks
black .
pytest

# General checks
pre-commit run --all-files check-json
pre-commit run --all-files check-yaml
pre-commit run --all-files check-merge-conflict
pre-commit run --all-files trailing-whitespace
pre-commit run --all-files check-added-large-files