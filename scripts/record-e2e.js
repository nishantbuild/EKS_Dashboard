/**
 * Records an end-to-end walkthrough of the EKS Dashboard:
 * login -> namespaces -> pods -> logs -> terminal (exec) -> resource metrics -> deployments -> audit log.
 *
 * Usage: node record-e2e.js
 * Output: scripts/recordings/*.webm
 */
const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = 'http://localhost:5173';
const RECORD_DIR = path.join(__dirname, 'recordings');

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 },
    recordVideo: { dir: RECORD_DIR, size: { width: 1400, height: 900 } },
  });
  const page = await context.newPage();

  const pause = (ms) => new Promise((r) => setTimeout(r, ms));

  // --- Login ---
  await page.goto(BASE_URL);
  await page.waitForSelector('text=EKS Dashboard');
  await pause(1000);
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'admin123');
  await pause(500);
  await page.click('button:has-text("Sign in")');
  await page.waitForSelector('text=eks-dashboard');
  await pause(1500);

  // --- Browse namespaces ---
  for (const ns of ['demo', 'kube-system', 'default']) {
    const nsButton = page.locator(`button:has-text("# ${ns}")`);
    if (await nsButton.count()) {
      await nsButton.first().click();
      await pause(1500);
    }
  }

  // Settle on "demo" for the rest of the walkthrough
  await page.locator('button:has-text("# demo")').first().click();
  await pause(1500);

  // --- View pod logs ---
  const logsButton = page.locator('button:has-text("Logs")').first();
  if (await logsButton.count()) {
    await logsButton.click();
    await pause(2500);
    const closeButton = page.locator('.modal-header button:has-text("Close")');
    if (await closeButton.count()) await closeButton.click();
    await pause(800);
  }

  // --- Open interactive pod terminal ---
  const terminalButton = page.locator('button:has-text("Terminal")').first();
  if (await terminalButton.count()) {
    await terminalButton.click();
    await pause(2500);
    await page.keyboard.type('echo hello-from-recording && hostname');
    await page.keyboard.press('Enter');
    await pause(2000);
    const closeButton = page.locator('.modal-header button:has-text("Close")');
    if (await closeButton.count()) await closeButton.click();
    await pause(800);
  }

  // --- Resource monitor (bottom panel) already visible; give it time on screen ---
  await pause(2500);

  // --- Deployments tab ---
  const deploymentsTab = page.locator('button:has-text("Deployments")');
  if (await deploymentsTab.count()) {
    await deploymentsTab.click();
    await pause(2000);
  }

  // --- Audit log tab (admin only) ---
  const auditTab = page.locator('button:has-text("Audit")');
  if (await auditTab.count()) {
    await auditTab.click();
    await pause(2000);
  }

  // --- Sign out ---
  const signOut = page.locator('button:has-text("Sign out")');
  if (await signOut.count()) {
    await signOut.click();
    await pause(1500);
  }

  await context.close();
  await browser.close();
  console.log('Recording saved under', RECORD_DIR);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
