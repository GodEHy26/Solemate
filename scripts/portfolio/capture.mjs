  await shot(page, '11-checkout-with-warning-desktop', '/checkout', { wait: '.scan-warning', fullPage: true });
  await ctx.close();

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
