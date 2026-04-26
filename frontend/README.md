# Hermes Frontend

This is the lightweight Vite + React frontend for Hermes.

## Local Setup

From the `frontend/` directory:

```bash
npm install
npm run dev
```

The frontend runs in mock mode if no backend URL is configured.

## Environment Variables

Set `VITE_API_BASE_URL` to point at the backend API:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is missing, the UI uses mock fallback mode.

## Vercel Deployment

1. Import the repository into Vercel.
2. Set the project root to `frontend`.
3. Add `VITE_API_BASE_URL` and point it at the deployed Render backend URL.
4. Keep the default build command: `npm run build`.
5. Keep the default output directory: `dist`.

Example:

```bash
VITE_API_BASE_URL=https://your-hermes-backend.onrender.com
```

Run `npm run build` locally before deploying to confirm the frontend is ready.
