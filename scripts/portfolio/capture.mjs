// Capture every SoleMate screen for the portfolio, on your own computer.
//
//   1. npm run dev                                       (API :8000 + web :5173)
//   2. backend/.venv/bin/python scripts/portfolio/seed_demo.py
//   3. node scripts/portfolio/capture.mjs                (writes portfolio-shots/*.png)
//
// Options: WEB=http://localhost:5173  REAL_PROFILE=<id of a scan of your own foot>  HEADED=1
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, devices } from 'playwright';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = process.env.OUT ?? join(ROOT, 'portfolio-shots');
const WEB = (process.env.WEB ?? 'http://localhost:5173').replace(/\/$/, '');
const P = JSON.parse(readFileSync(join(OUT, 'profiles.json'), 'utf8'));
mkdirSync(OUT, { recursive: true });

const DESKTOP = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 };
const PHONE = { ...devices['iPhone 13'] };

async function session(browser, opts, feet = {}) {
  const ctx = await browser.newContext(opts);
  await ctx.addInitScript((f) => {
    localStorage.setItem('solemate-feet', JSON.stringify({ state: { profiles: f }, version: 0 }));
    localStorage.setItem('solemate-install-dismissed', '1');
  }, feet);
  return ctx;
}

async function shot(page, name, url, { wait, fullPage = false, settle = 1200, before } = {}) {
  await page.goto(WEB + url, { waitUntil: 'networkidle' });
  if (wait) await page.waitForSelector(wait, { timeout: 20000 });
  if (before) await before(page);
  await page.waitForTimeout(settle); // let the 3D viewer render a few frames
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage });
  console.log('saved', `${name}.png`);
}

const browser = await chromium.launch({ headless: !process.env.HEADED, executablePath: process.env.CHROME_PATH || undefined });
const real = process.env.REAL_PROFILE;
const left = real ?? P.clean.left;
try {
  // ---- desktop
  let ctx = await session(browser, DESKTOP, { left: P.clean.left, right: P.clean.right });
  let page = await ctx.newPage();
  await shot(page, '01-home-desktop', '/', { wait: 'text=How it works' });
  await shot(page, '04-foot-profile-desktop', `/profiles/${left}`, { wait: 'text=Measurements', fullPage: true, settle: 3000 });
  await shot(page, '05-foot-3d-viewer-desktop', `/profiles/${left}`, { wait: '.viewer canvas', settle: 3500,
    before: async (p) => p.locator('.viewer').first().scrollIntoViewIfNeeded() });
  await shot(page, '08-catalog-desktop', '/shoes', { wait: '.shoe-card' });
  await shot(page, '09-configurator-desktop', '/shoes/solemate-court', { wait: 'text=Your preorder', settle: 2500 });
  await shot(page, '06-scan-warning-desktop', `/profiles/${P.warning}`, { wait: '.scan-warning', fullPage: true, settle: 2500 });
  await ctx.close();

  // checkout with one warned scan: shows the size range and the "less accurate" tick box
  ctx = await session(browser, DESKTOP, { left: P.clean.left, right: P.warning });
  page = await ctx.newPage();
  await page.goto(WEB + '/shoes/solemate-daily', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.getByRole('button', { name: 'Add preorder to cart' }).click();
  await page.waitForURL('**/checkout');
  await shot(page, '11-checkout-with-warning-desktop', '/checkout', { wait: '.scan-warning', fullPage: true });
  await ctx.close();

  // ---- phone
  ctx = await session(browser, PHONE, { left: P.clean.left, right: P.clean.right });
  page = await ctx.newPage();
  await shot(page, '02-home-phone', '/', { wait: 'text=How it works' });
  await shot(page, '03-scan-start-phone', '/scan', { wait: 'text=Start scan' });
  await shot(page, '10-configurator-phone', '/shoes/solemate-stride', { wait: '.price-bar', settle: 2500 });
  await shot(page, '07-scan-blocked-phone', `/profiles/${P.blocked}`, { wait: 'text=No size from this scan' });
  await shot(page, '12-fit-guarantee-phone', '/fit-guarantee', { wait: 'text=Fit Guarantee' });
  await ctx.close();
} finally {
  await browser.close();
}
console.log(`\nDone. Screenshots are in ${OUT}`);
