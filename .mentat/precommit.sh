npm --prefix frontend run format
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test:unit
cd backend && black .
pytest