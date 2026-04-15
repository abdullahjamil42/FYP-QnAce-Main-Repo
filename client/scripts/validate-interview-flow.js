const { chromium } = require('playwright');

const baseURL = process.env.QACE_BASE_URL || 'http://127.0.0.1:3000';
const autoEndMode = process.env.AUTO_END_VALIDATION === '1';
const durationMinutes = Number.parseInt(process.env.DURATION_MINUTES || '20', 10);
const autoEndWaitSeconds = Number.parseInt(process.env.AUTO_END_WAIT_SECONDS || '95', 10);

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--use-fake-device-for-media-stream',
      '--use-fake-ui-for-media-stream',
      '--allow-file-access',
    ],
  });

  const context = await browser.newContext({
    baseURL,
    permissions: ['microphone', 'camera'],
  });

  const page = await context.newPage();

  const result = {
    autoEndMode,
    requestedDurationMinutes: durationMinutes,
    autoEndWaitSeconds,
    stressSetupInLocalStorage: null,
    webrtcOfferPayload: null,
    stressLevelSentInOffer: null,
    durationMinutesSentInOffer: null,
    connectionStateText: null,
    connectedSeen: false,
    stateHistory: [],
    systemTimeline: [],
    endAndSaveEnabledAfterConnect: null,
    redirectedToSummaryAfterEnd: null,
    summaryUrl: null,
    errorBannerText: null,
    errors: [],
  };

  let capturedOfferBody = null;
  page.on('request', (req) => {
    if (req.url().includes('/webrtc/offer') && req.method() === 'POST') {
      capturedOfferBody = req.postData();
    }
  });

  try {
    await page.goto('/session/lobby', { waitUntil: 'networkidle' });

    // Persist deterministic setup values before entering the live room.
    await page.evaluate((mins) => {
      localStorage.setItem(
        'qace_setup_v1',
        JSON.stringify({
          mode: 'technical',
          difficulty: 'standard',
          durationMinutes: mins,
          stressLevel: 'high',
          cvSessionId: '',
        })
      );
    }, durationMinutes);

    const setupRaw = await page.evaluate(() => localStorage.getItem('qace_setup_v1'));
    result.stressSetupInLocalStorage = setupRaw;

    await page.getByRole('link', { name: /enter live room/i }).click();
    await page.waitForURL('**/session/live', { timeout: 15000 });

    await page.getByRole('button', { name: /join interview/i }).click();

    // Wait for offer to be observed.
    const deadline = Date.now() + 15000;
    while (!capturedOfferBody && Date.now() < deadline) {
      await page.waitForTimeout(200);
    }

    if (capturedOfferBody) {
      result.webrtcOfferPayload = capturedOfferBody;
      try {
        const parsed = JSON.parse(capturedOfferBody);
        result.stressLevelSentInOffer = parsed.stress_level ?? null;
        result.durationMinutesSentInOffer = parsed.duration_minutes ?? null;
      } catch {
        result.errors.push('Could not parse /webrtc/offer request body as JSON.');
      }
    } else {
      result.errors.push('No /webrtc/offer request captured after Join Interview.');
    }

    const stateBadge = page.locator('header .flex.items-center.gap-2.text-xs span').nth(1);

    // Wait for state transitions; in auto-end mode keep watching for summary redirect.
    const stateTexts = ['idle', 'connecting', 'connected', 'error'];
    const timeoutMs = autoEndMode ? autoEndWaitSeconds * 1000 : 35000;
    const t0 = Date.now();
    while (Date.now() - t0 < timeoutMs) {
      if (/\/session\/summary/i.test(page.url())) {
        result.redirectedToSummaryAfterEnd = true;
        result.summaryUrl = page.url();
        break;
      }

      let matched = null;
      if (await stateBadge.count()) {
        const badgeText = (await stateBadge.innerText()).trim().toLowerCase();
        matched = stateTexts.includes(badgeText) ? badgeText : null;
      }
      if (matched) {
        result.stateHistory.push({ tMs: Date.now() - t0, state: matched });
        result.connectionStateText = matched;
        if (matched === 'connected') {
          result.connectedSeen = true;
        }
      }
      if (!autoEndMode && (matched === 'connected' || matched === 'error')) {
        break;
      }
      await page.waitForTimeout(1000);
    }

    const timelineItems = await page
      .locator('section:has-text("System Timeline") .max-h-28 p')
      .allInnerTexts()
      .catch(() => []);
    result.systemTimeline = timelineItems.map((s) => s.trim()).filter(Boolean);

    if (result.redirectedToSummaryAfterEnd !== true) {
      result.redirectedToSummaryAfterEnd = false;
    }

    const errorBanner = page.locator('text=/Error:/i').first();
    if ((await errorBanner.count()) > 0) {
      result.errorBannerText = (await errorBanner.innerText()).trim();
    }

    const endAndSaveBtn = page.getByRole('button', { name: /end and save/i });
    result.endAndSaveEnabledAfterConnect = await endAndSaveBtn.isEnabled().catch(() => false);

    if (!autoEndMode && result.endAndSaveEnabledAfterConnect) {
      await endAndSaveBtn.click();
      await page.waitForURL('**/session/summary**', { timeout: 20000 });
      result.redirectedToSummaryAfterEnd = true;
      result.summaryUrl = page.url();
    } else if (!autoEndMode) {
      result.redirectedToSummaryAfterEnd = false;
    }
  } catch (err) {
    result.errors.push(String(err && err.message ? err.message : err));
  } finally {
    console.log(JSON.stringify(result, null, 2));
    await context.close();
    await browser.close();
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
