# 🔍 AuditBot — Auditoría de Accesibilidad Web Automática

API + Bot que recibe una URL y devuelve un reporte de accesibilidad (WCAG 2.1 AA).

## Quick Start
```bash
pip install -r requirements.txt
npm install -g axe-core-cli
uvicorn app:app --reload
```

## Endpoints
- `GET /audit?url=https://example.com` — Auditar URL
- `POST /audit` — Body: `{"url": "https://example.com"}`

## Deploy (Render - gratis con Student Pack)
1. Push a GitHub
2. Conectar en render.com
3. Build: `pip install -r requirements.txt && npm install -g axe-core-cli`
4. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Pricing
- Free: 1 auditoría/mes
- Pro ($29/mes): 10 auditorías
- Agencia ($99/mes): Ilimitadas + branding

## Licencia

MIT — © 2026 Ranuk IT Solutions | ranuk.dev
