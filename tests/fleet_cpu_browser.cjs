// Run with Playwright available in NODE_PATH. Optional browser override:
// PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium node tests/fleet_cpu_browser.cjs URL
const {chromium} = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = process.argv[2] || 'https://dertog.tailb4b58.ts.net/';
    const response = page.waitForResponse(r => r.url().endsWith('/_fleet.json'));
    await page.goto(base + '#fleet');
    const live = await (await response).json();
    assert(live.complete);
    for (const host of live.hosts) {
      assert(host.guests.some(g => g.cpu?.state === 'ok' && g.cpu.sample_count >= 5), host.host);
    }
    await page.locator('.cpu-meter').first().waitFor();
    const firstSamples = live.hosts.map(h => Math.max(...h.guests.map(g => g.cpu?.sampled_at || 0)));
    let advancing;
    for (let attempt = 0; attempt < 7; attempt++) {
      const update = await page.waitForResponse(r => r.url().endsWith('/_fleet.json'), {timeout: 12000});
      advancing = await update.json();
      if (advancing.hosts.every((h, i) => Math.max(...h.guests.map(g => g.cpu?.sampled_at || 0)) > firstSamples[i])) break;
    }
    assert(advancing.hosts.every((h, i) => Math.max(...h.guests.map(g => g.cpu?.sampled_at || 0)) > firstSamples[i]),
      'Both hosts must deliver newer native CPU samples through automatic polling');
    console.log('Both hosts advanced their native CPU samples through background polling.');
    assert.equal(await page.locator('th').nth(5).innerText(), 'CPU load · 1m↕');
    assert((await page.locator('th').nth(6).innerText()).startsWith('vCPU'));
    await page.locator('[data-sort="cpu"]').click();
    await page.locator('#fleet-heading').evaluate(el => el.scrollIntoView({block: 'start'}));
    await page.screenshot({path: '/tmp/dertog-cpu-desktop.png'});
    await page.locator('[data-theme-set="paper"]').click();
    await page.locator('#fleet-heading').evaluate(el => el.scrollIntoView({block: 'start'}));
    await page.screenshot({path: '/tmp/dertog-cpu-paper.png'});
    await page.locator('[data-theme-set=""]').click();
    await page.setViewportSize({width: 390, height: 844});
    await page.locator('[data-sort="cpu"]').scrollIntoViewIfNeeded();
    const overflow = await page.evaluate(() => ({width: innerWidth, scroll: document.documentElement.scrollWidth}));
    assert(overflow.scroll <= overflow.width);
    await page.screenshot({path: '/tmp/dertog-cpu-mobile.png'});
    await page.setViewportSize({width: 1440, height: 1050});

    // Deterministic data exercises every level, nulls, natural/numeric sorting,
    // keyboard operation, and preservation of sort state through polling.
    let fixture = structuredClone(advancing);
    const original = live.hosts[0].guests.filter(g => g.type === 'qemu' && g.status === 'running').slice(0, 4);
    const samples = original.map((g, i) => ({...g, name: ['vm-2', 'vm-10', 'vm-1', 'vm-20'][i],
      cpus: [2, 16, 8, 4][i], memory_bytes: [4, 16, 8, 2][i] * 2**30,
      disk_bytes: [80, 300, 120, 64][i] * 2**30, services: ['service ' + (i + 1)],
      cpu: i === 3 ? null : {average: [.2, .6, .85][i], current: [.25, .65, .9][i],
        sampled_at: Date.now() / 1000, sample_count: 6, state: 'ok'}}));
    fixture.hosts[0].guests = samples;
    fixture.hosts[1].guests = [];
    await page.route('**/_fleet.json', route => route.fulfill({json: fixture}));
    const refresh = async () => {
      const response = page.waitForResponse(r => r.url().endsWith('/_fleet.json'));
      await page.locator('#fleet-refresh').click();
      await response;
      await page.waitForFunction(() => !document.getElementById('fleet-refresh').disabled);
    };
    const keys = () => page.locator('#fleet-body tr[data-key]').evaluateAll(rows => rows.map(row => row.dataset.key));
    await refresh();
    assert.equal(await page.locator('.cpu-meter.low').count(), 1);
    assert.equal(await page.locator('.cpu-meter.medium').count(), 1);
    assert.equal(await page.locator('.cpu-meter.high').count(), 1);
    assert((await page.locator(`[data-key="${samples[3].key}"]`).innerText()).includes('No recent sample'));
    assert.deepEqual(await keys(), [samples[2].key, samples[1].key, samples[0].key, samples[3].key]);
    await page.locator('[data-sort="cpu"]').focus();
    await page.keyboard.press('Enter');
    assert.deepEqual(await keys(), [samples[0].key, samples[1].key, samples[2].key, samples[3].key]);
    assert.equal(await page.locator('th').nth(5).getAttribute('aria-sort'), 'ascending');

    for (const column of ['host', 'vmid', 'name', 'status', 'services', 'cpus', 'memory_bytes', 'disk_bytes']) {
      for (let toggle = 0; toggle < 2; toggle++) {
        await page.locator(`[data-sort="${column}"]`).click();
        const direction = await page.locator(`[data-sort="${column}"]`).evaluate(el => el.closest('th').getAttribute('aria-sort'));
        const values = (await keys()).map(key => {
          const guest = samples.find(g => g.key === key);
          return column === 'services' ? guest.services.join(', ') : guest[column];
        });
        for (let i = 1; i < values.length; i++) {
          const difference = typeof values[i] === 'number' ? values[i] - values[i - 1]
            : String(values[i]).localeCompare(String(values[i - 1]), undefined, {numeric: true, sensitivity: 'base'});
          assert(direction === 'ascending' ? difference >= 0 : difference <= 0, column);
        }
      }
    }
    await page.locator('[data-sort="cpu"]').click(); // Busiest first.
    samples[0].cpu.average = .99;
    await page.waitForFunction(key => document.querySelector('#fleet-body tr[data-key]')?.dataset.key === key,
      samples[0].key, {timeout: 8000}); // Automatic 5-second refresh, no click.
    assert.equal(await page.locator('th').nth(5).getAttribute('aria-sort'), 'descending');
    samples[0].cpu.sampled_at = Date.now() / 1000 - 40;
    await refresh();
    assert.equal(await page.locator(`[data-key="${samples[0].key}"] .cpu-meter.stale`).count(), 1);
    assert.equal((await keys())[0], samples[2].key); // Stale value is not ranked as live load.
    fixture.hosts[0].state = 'stale';
    await refresh();
    assert.equal(await page.locator('.cpu-meter.stale').count(), 3);
    assert.equal(await page.locator('.cpu-meter.low, .cpu-meter.medium, .cpu-meter.high').count(), 0);
    assert.deepEqual(errors, []);
    console.log('Passed live CPU history, bar levels, missing/stale samples, all nine sortable columns, keyboard sorting, automatic refresh, themes, and mobile width.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
