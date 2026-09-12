const { chromium } = require("playwright");
const path = require("node:path");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const checks = [];
  const output = path.join(__dirname, "..", "test-results", "visual");
  require("node:fs").mkdirSync(output, { recursive: true });

  for (const config of [
    { name: "desktop-short", width: 1365, height: 773 },
    { name: "mobile", width: 390, height: 844 },
  ]) {
    const page = await browser.newPage({ viewport: config });
    await page.goto("http://localhost:3111/universe", { waitUntil: "networkidle" });
    await page.locator("#uni-search").fill("Proxima Cen");
    const choice = page.locator("button").filter({ hasText: "Proxima Cen b" }).first();
    if (!(await choice.count())) throw new Error("Universe search did not expose Proxima Cen b");
    await choice.click();
    await page.waitForTimeout(500);
    const selected = await page.getByTestId("selected-system-panel").boundingBox({ timeout: 5000 });
    const history = await page.getByTestId("discovery-history-controls").boundingBox();
    const overlap = selected && history
      ? Math.max(0, Math.min(selected.y + selected.height, history.y + history.height) - Math.max(selected.y, history.y))
      : null;
    const horizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    checks.push({ viewport: config.name, selected, history, verticalOverlapPx: overlap, horizontalOverflowPx: horizontalOverflow });
    await page.screenshot({ path: path.join(output, `universe-${config.name}.png`) });
    await page.close();
  }

  for (const route of ["/", "/population", "/selection", "/missions", "/information-gain", "/falsification", "/evidence", "/perspective"]) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const response = await page.goto(`http://localhost:3111${route}`, { waitUntil: "networkidle" });
    checks.push({
      route,
      status: response?.status(),
      title: await page.title(),
      h1: await page.locator("h1").first().textContent(),
      horizontalOverflowPx: await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      ),
      errors,
    });
    const name = route === "/" ? "home" : route.slice(1);
    await page.screenshot({ path: path.join(output, `route-${name}.png`) });
    await page.close();
  }

  await browser.close();
  console.log(JSON.stringify(checks, null, 2));
  if (checks.some((check) => check.status && check.status !== 200)) process.exitCode = 1;
  if (checks.some((check) => check.verticalOverlapPx && check.verticalOverlapPx > 0)) process.exitCode = 1;
  if (checks.some((check) => check.horizontalOverflowPx && check.horizontalOverflowPx > 0)) process.exitCode = 1;
  if (checks.some((check) => check.errors && check.errors.length)) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
