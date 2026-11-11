import json
import os
import subprocess
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

from browser_support import ROOT, serve
import hashlib

WORK = ROOT / 'tests/fixtures'
for filename, digest in json.loads((WORK / 'logic-hashes.json').read_text()).items():
    assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest, filename + ' logic/data changed'

with serve() as BASE_URL, sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(BASE_URL, wait_until='networkidle')
    expect(page.locator('#reset-button')).to_be_disabled()
    expect(page.locator('#day2-search')).to_be_disabled()
    assert page.locator('#day1-options button').count() == 18
    assert page.locator('#event-options button').count() == 13
    page.locator('#day1-search').fill('存在しないボス')
    expect(page.locator('#day1-empty')).to_be_visible()
    assert page.locator('#day1-options button').count() == 0
    page.locator('#reset-button').click()
    page.locator('#day1-search').fill('よるのきへい')
    expect(page.locator('#day1-options button')).to_have_text('夜の騎兵')
    page.locator('#day1-options button').click()
    expect(page.locator('#candidate-count')).to_have_text('3体')
    assert page.locator('#candidate-details .detail-title').all_text_contents() == ['エデレ', 'フルゴール', 'ナメレス']
    page.locator('#candidate-details .candidate-detail').first.locator('summary').first.click()
    expect(page.locator('#candidate-details .candidate-detail').first.locator('.resistance-table').first).to_be_visible()
    page.locator('#day1-selected button').click()
    expect(page.locator('#day2-search')).to_be_disabled()
    page.locator('#reset-button').click()
    snapshots = []
    names = page.locator('#day1-options button').all_text_contents()
    for name in names:
        page.locator('#day1-options button').get_by_text(name, exact=True).click()
        item = {'day1': name, 'candidates': page.locator('#candidate-details .detail-title').all_text_contents(), 'day2': page.locator('#day2-options button').all_text_contents()}
        page.locator('#day2-options button').first.click()
        item['after_day2'] = page.locator('#candidate-details .detail-title').all_text_contents()
        item['events'] = page.locator('#event-options button').all_text_contents()
        page.locator('#day1-selected button').click()
        expect(page.locator('#day2-selected')).to_be_hidden()
        expect(page.locator('#reset-button')).to_be_disabled()
        snapshots.append(item)
    assert snapshots == json.loads((WORK / 'behavior-baseline.json').read_text()), 'Selection behavior differs from baseline'
    page.locator('#event-options button').get_by_text('歩く霊廟', exact=True).click()
    assert page.locator('#candidate-details .detail-title').all_text_contents() == ['マリス', 'カリゴ']
    page.locator('#reset-button').click()
    expect(page.locator('#candidate-count')).to_have_text('未選択')
    assert not errors, errors
    print('PASS: 18 encounter flows match; search/aliases, day2 reset, event-only selection, resistance tables, global reset; no browser errors')
    for width in (320, 768):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.reload(wait_until='networkidle')
        page.locator('#day1-options button').get_by_text('夜の騎兵', exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), str(width) + 'px horizontal overflow'
        assert page.locator('.quick-summary').evaluate_all('els => els.length > 0 && els.every(el => el.checkVisibility())')
        sizes = page.locator('.option-button').evaluate_all('els => els.map(el => {const r=el.getBoundingClientRect();return [r.width,r.height]})')
        assert all(w >= 100 and 44 <= h <= 72 for w, h in sizes), (width, sizes)
    print('PASS: 320px and 768px reflow, tap targets and visible compact resistances')
    context.close()
    browser.close()

baseline_assets = {name: subprocess.run(['git', 'show', '2e39352:' + name], cwd=ROOT, capture_output=True, check=True).stdout for name in ['index.html', 'styles.css', 'resistance.css', 'manifest.webmanifest', 'service-worker.js']}
with serve(baseline_assets) as base_url, sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    context = browser.new_context(service_workers='allow')
    page = context.new_page()
    page.goto(base_url, wait_until='networkidle')
    page.evaluate('navigator.serviceWorker.ready.then(() => true)')
    page.wait_for_function('() => navigator.serviceWorker.controller !== null')
    old_names = page.evaluate('caches.keys()')
    assert 'nightreign-boss-tool-0.9.1' in old_names, old_names
    page.evaluate('window.originalController = navigator.serviceWorker.controller')
    baseline_assets.clear()
    page.evaluate('navigator.serviceWorker.getRegistration().then(reg => reg.update())')
    page.wait_for_function('() => navigator.serviceWorker.controller !== window.originalController')
    page.reload(wait_until='networkidle')
    expect(page.locator('h1')).to_have_text('夜の王チェッカー')
    expect(page.locator('body')).to_have_css('background-color', 'rgb(16, 21, 25)')
    new_names = page.evaluate('caches.keys()')
    assert 'nightreign-boss-tool-0.9.2' in new_names, new_names
    context.set_offline(True)
    page.reload(wait_until='networkidle')
    assert page.locator('#day1-options button').count() == 18
    page.locator('#event-options button').get_by_text('歩く霊廟', exact=True).click()
    assert page.locator('#candidate-details .detail-title').all_text_contents() == ['マリス', 'カリゴ']
    report = {'old_caches': old_names, 'new_caches': new_names, 'offline_candidates': page.locator('#candidate-details .detail-title').all_text_contents(), 'theme': page.locator('body').evaluate('el => getComputedStyle(el).backgroundColor')}
    output = Path(os.environ.get('CODEXENVSET_EVIDENCE_DIR', tempfile.mkdtemp(prefix='nightreign-pwa-')))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'pwa-upgrade.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    context.close()
    browser.close()
    print('PASS: actual old-cache → new-cache upgrade and offline reload, with working event selection')
