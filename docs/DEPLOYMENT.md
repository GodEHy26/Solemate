# Publishing SoleMate (domain, hosting, phones)

## 1. Try it on your phone today (no domain)

Phones only allow the camera and motion sensors on **HTTPS**, so plain `http://192.168.x.x:5173`
will not work for scanning. Two easy options while developing:

**Self-signed HTTPS on your Wi-Fi**
```bash
cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev:phone        # https://<your-computer-ip>:5173
```
Open the printed `https://` network address on the phone and accept the certificate warning.

**Public tunnel (works over mobile data, real certificate)**
```bash
cloudflared tunnel --url http://localhost:5173     # or: ngrok http 5173
```
The tunnel prints an `https://...` URL you can open on any phone. Vite proxies `/api` to the
backend, so one tunnel is enough.

On the phone: **iPhone** Safari > Share > *Add to Home Screen*. **Android** Chrome > menu >
*Install app* (an in-app banner also offers it). The app then opens full screen like a native app.

## 2. Buy a domain

A domain is a yearly rental from a registrar. You cannot buy it through this repo; you do it in
your own account with your own payment method.

1. Pick a name and check availability on the registrar's search page. Also search the name in the
   trademark office for your country (for example USPTO, KIPO, EUIPO) and on the web: "SoleMate"
   is a plain phrase that other footwear businesses may already use.
2. Buy from a registrar that sells at cost and does not bury you in upsells. Good choices:
   **Cloudflare Registrar** (wholesale price, no markup, free WHOIS privacy, but you must use
   Cloudflare DNS), **Porkbun**, **Namecheap**. Compare the *renewal* price, not just year one.
3. Turn on WHOIS/domain privacy (free at the three above) and auto-renew, and enable two-factor on
   the registrar account: whoever controls the registrar account controls the domain.
4. A `.com` is the safe default for a shop. Short and easy to say aloud beats clever.

## 3. Host it

You need two things running: the static frontend and the Python API (OpenCV needs a normal
server or container; it will not run on serverless functions).

| Piece | Easy choices | Notes |
|-------|-------------|-------|
| Frontend (`frontend/dist`) | Cloudflare Pages, Netlify, Vercel, Render Static | Build command `npm run build`, output `dist`, env `VITE_API_BASE=https://api.YOURDOMAIN.com` |
| API (`backend/`, Docker) | Render, Fly.io, Railway, a small VPS | Needs about 1 GB RAM for reconstruction (not yet measured on real scans) and a **persistent disk** for scans and the SQLite file, or set `SOLEMATE_DATABASE_URL` to Postgres |

The included `render.yaml` deploys both on Render. Free instances lose their disk on restart, so
use a paid instance with a disk for anything real. It has not been deployed yet, so expect to
adjust it on the first run.

### Connect the domain
1. At your host, add `YOURDOMAIN.com` (and `www`) to the frontend and `api.YOURDOMAIN.com` to the API.
2. The host shows DNS records (usually a `CNAME` for `www`/`api` and an `A`/`ALIAS` for the root).
   Add exactly those at your registrar's DNS page.
3. Wait for DNS (minutes to a few hours). HTTPS certificates are issued automatically.
4. Set `SOLEMATE_CORS_ORIGINS` on the API to `["https://YOURDOMAIN.com","https://www.YOURDOMAIN.com"]`.
5. Open `https://YOURDOMAIN.com` on a phone and run a scan.

Alternative with one hostname: put both behind one reverse proxy (see `frontend/nginx.conf` and
`docker-compose.yml`) and leave `VITE_API_BASE` empty.

## 4. Before taking real customers

- **Payments**: orders are saved but nobody is charged yet. Add Stripe Checkout (see ROADMAP).
- **Privacy policy and consent**: you collect foot photos, 3D models and emails. Say what you
  keep, for how long, and let people delete a scan (`DELETE /api/scans/{id}` exists). Check the
  rules where your customers live (GDPR in the EU, Korea's PIPA, and so on).
- **Accounts and backups**: profiles currently live in the browser; back up the data volume.
- **Real accuracy check**: compare scan measurements to a tape measure on real feet first.
