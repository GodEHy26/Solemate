# Preorders, Stripe and legal pages

Everything on SoleMate is sold as a **preorder**: the site says so in a banner on every page, on
each product, in the cart, on Stripe's payment page, and on the confirmation. The customer ticks a
box accepting the Preorder Terms and Privacy Policy before they can pay, and the server refuses an
order without it and records the time and version accepted.

## How a payment flows

```
checkout form ──▶ POST /api/orders              server re-prices every item, stores order = awaiting_payment
              ──▶ POST /api/orders/{id}/checkout   creates a Stripe Checkout session, returns its URL
              ──▶ customer pays on Stripe's hosted page (we never see card numbers)
Stripe ──▶ POST /api/stripe/webhook             signature checked; amount and currency must equal our price
        └▶ browser returns to /orders/{id}?paid=1  which calls POST /api/orders/{id}/confirm
                                                   (asks Stripe directly, so a slow webhook does not matter)
order = preordered
```

Safety rules in the code: the price is always calculated on the server; a payment whose amount or
currency differs from the order goes to `needs_review` instead of being accepted; paid events are
idempotent; unpaid orders are deleted after `SOLEMATE_UNPAID_ORDER_HOURS`.

## Set up Stripe (test mode first)

1. Create a Stripe account at stripe.com and finish business verification. The account holder
   must be of legal age in their country, and Stripe will ask for your business or personal details.
2. In the dashboard stay in **Test mode** and copy the secret key (`sk_test_...`).
3. Put it in `backend/.env` as `SOLEMATE_STRIPE_SECRET_KEY`. Never commit keys; `.env` is git-ignored.
4. Forward webhooks to your computer with the Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/stripe/webhook
   ```
   It prints a `whsec_...` signing secret. Put it in `SOLEMATE_STRIPE_WEBHOOK_SECRET`.
5. Run the app, preorder something, and pay with the test card `4242 4242 4242 4242`, any future
   expiry, any CVC. The order page should flip to "Preorder confirmed".
6. Go live: switch the dashboard to Live mode, create a webhook endpoint
   `https://api.YOURDOMAIN.com/api/stripe/webhook` with the events `checkout.session.completed`,
   `checkout.session.async_payment_succeeded` and `checkout.session.async_payment_failed`, then
   set the live `sk_live_...` key and the new `whsec_...` on your host. Do one real small payment
   and refund it yourself to check the whole path.

Refunds are done in the Stripe dashboard (Payments > the payment > Refund). Then set the order's
status in your records; there is no admin screen yet.

## Decisions only you can make

The defaults below were written to be fair to customers. Check each against your plans and the law
where you sell, then edit the text in `frontend/src/pages/TermsPage.tsx` or the environment variable.

| Decision | Current default |
|----------|-----------------|
| When customers are charged | In full, at checkout. No deposit or pay-later flow exists |
| Shipping and taxes | Not charged at checkout; `SOLEMATE_SHIPPING_POLICY` says you will contact them. Stripe Tax and shipping rates are not wired in |
| Ship date | "To be announced" (`SOLEMATE_PREORDER_SHIP_ESTIMATE`). Put a real window in once you know it, because consumer-protection rules in many places require you to ship within the time you state |
| Cancel before production | Full refund |
| Cancel after production starts | Not possible, except late delivery (more than 60 days past the estimate), defect, or not matching the scan |
| Substitutions | Customer can accept or cancel for a full refund |

## Privacy policy: what is promised and where it is enforced

| Promise on `/privacy` | Enforced by |
|---|---|
| Photos deleted as soon as the 3D model is built | `discard_raw_inputs` in `services/scanning/pipeline.py` |
| Unfinished or failed scans deleted after 24 h | `services/retention.py`, run at startup and hourly |
| Unpaid orders deleted after 48 h | same |
| Customer can delete their scan | `DELETE /api/profiles/{id}` and the button on the profile page; blocked while an open preorder uses it |
| No analytics or ad trackers | none are installed; if you add any, update the policy first |
| Access by long random link, no accounts | true today; see ROADMAP for accounts |

The policy and terms are **templates written to match this code, not legal advice**. Before taking
real money: check the operator name and email (defaults in `backend/app/config.py`), decide whether
you need a published address (`SOLEMATE_COMPANY_ADDRESS`, required for online sellers in the EU, UK
and Korea, among others) and set `SOLEMATE_GOVERNING_LAW`, have them reviewed for the countries you
sell to, and keep this file in sync when you change how data is handled. The pages show a warning
until the name and email are set.

## Tests

`backend/tests/test_orders_and_payments.py` covers consent, server pricing, the exact parameters
sent to Stripe (checked through the real Stripe SDK against a local fake), signed webhooks
(valid, forged, expired, replayed, wrong amount, wrong currency), the confirm fallback, and
checkout without keys. `test_retention_and_deletion.py` covers purging, scan deletion and the
database migration. Nothing has been run against the live Stripe service yet; do the test-mode
steps above first.
