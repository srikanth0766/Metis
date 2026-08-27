# METIS buildathon deployment

## Before deploying

1. Keep the trained artifacts in `backend/models/`.
2. Copy `.env.example` to `.env` and set non-placeholder values for `SECRET_KEY`, Razorpay Test Mode keys and webhook secret. Do not commit `.env`.
3. Confirm the model runtime locally:

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

`ml_mode` must be `trained`.

## Run the production-shaped stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The frontend is exposed on port 3000; the database and backend are internal-only. A public URL/tunnel must point to frontend port 3000, and Razorpay webhooks must point to `https://YOUR_DOMAIN/api/v1/webhooks/razorpay` only if your reverse proxy forwards that route to the backend. With a Cloudflare Tunnel, map `/` to frontend and `/api` to backend.

## Final demo smoke test

1. Open the overview: it must show `model runtime / live`.
2. Open a recovery case, inspect intervention counterfactuals and policy constraints.
3. Start the AI recovery agent and send a customer reply.
4. Ingest a Test Mode payment with its Razorpay order ID, then complete it and send the signed webhook.
5. Confirm the payment, recovery case, and audit trail update exactly once.

Cloudflare Tunnel, Razorpay dashboard configuration, and external hosting require the account owner to provide credentials and approve the target domain; they cannot be completed from this repository alone.
