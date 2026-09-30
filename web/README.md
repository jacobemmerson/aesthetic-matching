# web
- `npm run dev` — Vite on :5173, proxies /api to :8000 (start the API with `docker compose up -d` at repo root)
- `npm test` — vitest unit tests for `src/lib`
- `npm run shots [scenario…]` — Playwright screenshots into `scripts/shots/` with a mocked analyze response
- `npm run build` — production build into `dist/` (served by the API container)
