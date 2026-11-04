"""LEGACY / DO NOT USE IN PIPELINE.

Headed-browser attempt to get past Pro-Football-Reference's Cloudflare
challenge (403 "Just a moment..."): real Chrome via Playwright persistent
profile, human solves the challenge, scrape waits for table#games.

Archived 2026-11-04: the challenge loops even in real Chrome driven by
Playwright (browser fingerprinting), and the user rejected the headed
launch. Kept for reference only. The production path no longer calls this;
see elt_ingest.scrape (requests + headless fallback) and the nflverse
alternative explored in data-integration/README.md.

Original usage was: elt-ingest games --headed  (flag removed)
It waited up to 180s per season for a human to clear the challenge, with the
cf_clearance cookie persisted in .pfr-profile/ (PFR_USER_DATA_DIR).
"""

# The implementation lived in elt_ingest.scrape._scrape_games_playwright
# (headless=False branch):
#
#   context = await p.chromium.launch_persistent_context(
#       str(profile), channel="chrome", headless=False, user_agent=_UA,
#       args=["--disable-blink-features=AutomationControlled"],
#       ignore_default_args=["--enable-automation"],
#   )
#   await page.goto(PFR_GAMES_URL.format(year=yr), wait_until="domcontentloaded")
#   await page.wait_for_selector("table#games", timeout=180_000)
