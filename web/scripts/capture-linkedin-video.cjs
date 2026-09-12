const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..", "..");
const MEDIA = path.join(ROOT, "media");
const RAW = path.join(MEDIA, "raw");
const BASE = process.env.EARTH2_VIDEO_BASE || "http://127.0.0.1:3111";

const scenes = [
  { route: "/", eyebrow: "164,209 records → 6,354 worlds", title: "Finding Earth 2.0", note: "What did humanity actually detect?", ms: 4700, y: 420 },
  { route: "/population", eyebrow: "Observed ≠ intrinsic", title: "The catalogue is only the visible tip", note: "Selection-aware inference reconstructs what the survey could see.", ms: 4800, y: 520 },
  { route: "/selection", eyebrow: "One Earth-like signal per ~50,535 stars", title: "Detection has a shape", note: "Geometry, window, pipeline, vetting and reliability stay explicit.", ms: 4800, y: 560 },
  { route: "/falsification", eyebrow: "A model must be allowed to fail", title: "Venus breaks the shortcut", note: "Similarity is not habitability. HZ position is not surface climate.", ms: 4300, y: 420 },
  { route: "/beyond", eyebrow: "From detection to distance and contact", title: "Could we ever reach it?", note: "Relativity, communication delay and extragalactic limits—calculated, not imagined away.", ms: 5600, y: 1550 },
  { route: "/perspective", eyebrow: "Built and authored by Biswajit Jana", title: "I did not find a second Earth", note: "I built a system that shows how hard it is to earn that conclusion.", ms: 5200, y: 600 },
];

async function overlay(page, scene) {
  await page.evaluate((copy) => {
    document.documentElement.style.scrollBehavior = "smooth";
    const existing = document.getElementById("linkedin-film-copy");
    if (existing) existing.remove();
    const overlay = document.createElement("div");
    overlay.id = "linkedin-film-copy";
    overlay.innerHTML = `<p>${copy.eyebrow}</p><h2>${copy.title}</h2><span>${copy.note}</span>`;
    Object.assign(overlay.style, {
      position: "fixed", left: "34px", right: "34px", bottom: "32px", zIndex: "99999",
      padding: "24px 28px", border: "1px solid rgba(116,220,235,.34)", borderRadius: "10px",
      background: "linear-gradient(110deg,rgba(5,8,14,.96),rgba(10,16,27,.84))",
      boxShadow: "0 22px 70px rgba(0,0,0,.55)", backdropFilter: "blur(16px)", color: "#f3efe6",
      fontFamily: "IBM Plex Sans,system-ui,sans-serif", opacity: "0", transform: "translateY(18px)",
      transition: "opacity .6s ease, transform .6s ease",
    });
    overlay.querySelector("p").style.cssText = "margin:0 0 8px;color:#63d6e8;font:500 12px IBM Plex Mono,monospace;letter-spacing:.15em;text-transform:uppercase";
    overlay.querySelector("h2").style.cssText = "margin:0;font:400 38px Fraunces,serif;line-height:1.05";
    overlay.querySelector("span").style.cssText = "display:block;margin-top:9px;color:#aab2c1;font-size:15px";
    document.body.appendChild(overlay);
    requestAnimationFrame(() => { overlay.style.opacity = "1"; overlay.style.transform = "translateY(0)"; });
  }, scene);
}

async function main() {
  fs.mkdirSync(RAW, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1350, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: RAW, size: { width: 1350, height: 1080 } },
    colorScheme: "dark",
  });
  const page = await context.newPage();
  await page.emulateMedia({ reducedMotion: "no-preference" });
  for (const scene of scenes) {
    await page.goto(`${BASE}${scene.route}`, { waitUntil: "networkidle" });
    await overlay(page, scene);
    await page.waitForTimeout(700);
    await page.evaluate(({ y, duration }) => {
      const main = document.querySelector("main");
      if (main) {
        main.style.transformOrigin = "50% 28%";
        main.style.transition = `transform ${duration}ms cubic-bezier(.2,.7,.2,1)`;
        main.style.transform = "scale(1.035)";
      }
      window.scrollTo({ top: y, behavior: "smooth" });
    }, { y: scene.y, duration: scene.ms - 900 });
    await page.waitForTimeout(scene.ms - 700);
  }
  await page.screenshot({ path: path.join(MEDIA, "finding-earth-2-linkedin-poster.png") });
  const video = page.video();
  await context.close();
  const rawPath = await video.path();
  await browser.close();
  const target = path.join(RAW, "finding-earth-2-capture.webm");
  if (rawPath !== target) fs.copyFileSync(rawPath, target);
  console.log(target);
}

main().catch((error) => { console.error(error); process.exit(1); });
