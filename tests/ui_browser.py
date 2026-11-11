import json
import os
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_support import ROOT, SCENARIOS, fixture, inventory, serve, fixture_description

CHANGE = os.environ.get('CODEXENVSET_CHANGE_ID', 'ui-design-quality')
CHECK = os.environ.get('CODEXENVSET_CHECK_ID', 'ui-browser')
OUTPUT = Path(os.environ.get('CODEXENVSET_EVIDENCE_DIR', tempfile.mkdtemp(prefix='nightreign-ui-')))
DESIGN = json.loads((ROOT / '.harness/changes' / CHANGE / 'design.json').read_text())['ui']
CONTROL_TARGETS = {
    'choose': '.option-button', 'clear': '.selected-chip button', 'search': '.search-input',
    'reset': '#reset-button', 'stage': '.stage-heading', 'boss': '.resistance-detail > summary',
    'form': '.form-detail > summary', 'help': '.help-details > summary',
}


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def dimensions(locator, zoom=1, pseudo=None):
    return locator.evaluate('''(el, options) => {
      const style = getComputedStyle(el, options.pseudo), rect = el.getBoundingClientRect();
      return {width: options.pseudo ? parseFloat(style.width) : rect.width / options.zoom,
              height: options.pseudo ? parseFloat(style.height) : rect.height / options.zoom};
    }''', {'zoom': zoom, 'pseudo': pseudo})


def focus_visible(page, control):
    page.keyboard.press('Tab')
    control.focus()
    return control.evaluate('''el => {
      const s = getComputedStyle(el);
      return el.matches(':focus-visible') && parseFloat(s.outlineWidth) >= 2 && s.outlineStyle !== 'none';
    }''')


def control_probe(page, base_url, spec, name):
    fixture(page, base_url, spec)
    if name == 'form':
        page.locator('[data-king-id="nameless"]').evaluate('el => el.open = true')
    control = page.locator(CONTROL_TARGETS[name]).first
    control.scroll_into_view_if_needed()
    normal = dimensions(control)
    visual = dimensions(control, pseudo='::before') if name == 'choose' else normal
    focused = focus_visible(page, control)
    before = control.evaluate('el => el.parentElement.open') if name in ('stage', 'boss', 'form', 'help') else None
    result = False
    if name == 'choose':
        expected_name = control.inner_text()
        control.click(position={'x': 24, 'y': 8})
        result = page.locator('#day1-selected .selected-name').inner_text() == expected_name
    elif name == 'clear':
        control.click(position={'x': 4, 'y': 4})
        result = page.locator('#day1-selected').is_hidden() and page.locator('#day2-search').is_disabled()
    elif name == 'search':
        control.click(position={'x': 10, 'y': 10})
        page.keyboard.type('not-a-boss')
        result = page.locator('#day1-empty').is_visible() and page.locator('#day1-options button').count() == 0
    elif name == 'reset':
        control.click(position={'x': 4, 'y': 4})
        result = control.is_disabled() and page.locator('#candidate-count').inner_text() == '未選択' and page.locator('#candidate-details').inner_text() == ''
    else:
        control.click(position={'x': 24, 'y': 8})
        result = control.evaluate('el => el.parentElement.open') != before
        if name == 'help':
            result = result and page.get_by_text('2日目のボスは、1日目を選ぶと選択できます。', exact=True).is_visible()
    return {'visual': visual, 'hit': normal, 'activated': result, 'focus_visible': focused}


def overflow_free(page):
    return page.evaluate('''() => document.documentElement.scrollWidth <= innerWidth + 1
      && document.querySelector('.workspace').getBoundingClientRect().right <= innerWidth + 1''')


def measure_scene(page, base_url, spec, scene):
    fixture(page, base_url, spec)
    if os.environ.get('NIGHTREIGN_UI_PROBE') == 'negative':
        page.locator('.app-header h1').evaluate("el => el.style.fontSize = '42px'")
        page.locator('body').evaluate("el => { const p = document.createElement('p'); p.textContent = 'UNREQUESTED COPY'; el.append(p); }")
    option = page.locator('.option-button').first
    reset = page.locator('#reset-button')
    page_color = page.locator('body').evaluate('el => getComputedStyle(el).backgroundColor')
    rgb = [int(value) for value in re.findall(r'\d+', page_color)[:3]]
    count = page.locator('#candidate-count').inner_text()
    names = page.locator('#candidate-details .detail-title').all_text_contents()
    expected_names = ['エデレ', 'ナメレス'] if spec.get('day2') else ['エデレ', 'フルゴール', 'ナメレス'] if spec['selected'] else []
    expected_count = str(len(expected_names)) + '体' if expected_names else '未選択'
    state = count == expected_count and names == expected_names and page.locator('#day2-search').is_disabled() == (not spec['selected'])
    values = {
        'layout': {'order': page.locator('.results-panel > *').evaluate_all('els => els.map(el => el.id || el.className)'), 'selected': names, 'viewport': page.viewport_size, 'zoom': spec['zoom']},
        'heading-font': page.locator('.app-header h1').evaluate('el => parseFloat(getComputedStyle(el).fontSize)'),
        'option-line': option.evaluate('el => parseFloat(getComputedStyle(el).lineHeight)'),
        'option-row': dimensions(option, spec['zoom'])['height'],
        'reset-target': dimensions(reset, spec['zoom'])['height'],
        'workspace-gap': page.locator('.workspace').evaluate('el => parseFloat(getComputedStyle(el).gap)'),
        'page-token': '#' + ''.join(f'{channel:02x}' for channel in rgb),
        'heading-token': page.locator('.app-header h1').evaluate('el => parseFloat(getComputedStyle(el).fontSize)'),
        'copy': inventory(page), 'state-consistency': state,
        'a11y-width': overflow_free(page),
        'a11y-label': page.locator('.search-input').evaluate_all('els => els.every(el => Boolean(el.getAttribute("aria-label")))') and page.locator('button').evaluate_all('els => els.every(el => Boolean(el.getAttribute("aria-label") || el.textContent.trim()))'),
        'a11y-reading_order': page.evaluate('''() => Boolean(document.querySelector('.selection-panel').compareDocumentPosition(document.querySelector('#nightlord-section')) & Node.DOCUMENT_POSITION_FOLLOWING)
          && Boolean(document.querySelector('#nightlord-section').compareDocumentPosition(document.querySelector('#day1-section')) & Node.DOCUMENT_POSITION_FOLLOWING)'''),
    }
    selected_summary_visible = not spec['selected'] or page.locator('.candidate-detail:not([open]) + .quick-summary').evaluate_all('els => els.every(el => el.checkVisibility())')
    if spec.get('expanded'):
        selected_summary_visible &= page.locator('.candidate-detail[open] .resistance-table').evaluate_all('els => els.length > 0 && els.every(el => el.checkVisibility())')
    assert selected_summary_visible, scene + ': compact resistance hidden'
    page.screenshot(path=str(OUTPUT / (scene + '.png')), full_page=True)
    write(OUTPUT / (scene + '.aria.json'), {'snapshot': page.locator('body').aria_snapshot()})
    fixture(page, base_url, {**spec, 'selected': False, 'day2': None, 'event': None, 'expanded': False, 'help': False, 'search': False})
    option = page.locator('.option-button').first
    values['a11y-focus'] = focus_visible(page, option)
    option.focus()
    page.keyboard.press('Space')
    once = page.locator('#day1-options button[aria-pressed="true"]').inner_text()
    page.locator('#day1-selected button').focus()
    page.keyboard.press('Space')
    values['a11y-keyboard'] = once == '亜人の女王＆亜人の剣聖' and page.locator('#day1-selected').is_hidden()
    fixture(page, base_url, spec)
    sizes = page.locator('.option-button').evaluate_all('els => els.map(el => {const r=el.getBoundingClientRect();return [r.width,r.height]})')
    values['a11y-operable_targets'] = all(w / spec['zoom'] >= 100 and h / spec['zoom'] >= 44 for w, h in sizes)
    zoom_spec = {**spec, 'width': 640, 'height': 1000, 'zoom': 2}
    fixture(page, base_url, zoom_spec)
    values['a11y-zoom'] = overflow_free(page) and page.locator('.option-button').first.is_visible()
    page.screenshot(path=str(OUTPUT / (scene + '.zoom.png')), full_page=True)
    if scene in ('desktop-selected', 'mobile-selected'):
        for name in CONTROL_TARGETS:
            probe = control_probe(page, base_url, spec, name)
            values['a11y-focus'] &= probe['focus_visible']
            for region in ('visual', 'hit'):
                for axis in ('width', 'height'):
                    values[name + '-' + region + '-' + axis] = probe[region][axis]
            values[name + '-activate'] = probe['activated']
    return values


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    reports, errors = [], []
    with serve() as url, sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for scene, spec in SCENARIOS.items():
            page = browser.new_page(service_workers='block', color_scheme='light')
            page.set_default_timeout(6000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            values = measure_scene(page, url, spec, scene)
            write(OUTPUT / (scene + '.metrics.json'), values)
            results = []
            for case in DESIGN['cases']:
                if case['scenario'] != scene:
                    continue
                key = case['id'].removeprefix(scene + '-')
                assert key in values, 'Unmeasured case: ' + case['id']
                results.append({'id': case['id'], 'observation': '実Chromiumのcomputed style、DOM、bounding box、または実入力結果。' + case['question'], 'value_ref': {'path': scene + '.metrics.json', 'pointer': '/' + key}})
            reports.append({'id': scene, 'status': 'passed', 'observations': '固定fixtureから実測した値。意味の妥当性は独立レビューで判定する。', 'environment': {'viewport': {'width': spec['width'], 'height': spec['height']}, 'browser': 'Chromium ' + browser.version, 'theme': 'browser prefers-color-scheme: light; application stylesheet per revision', 'fixture': fixture_description(spec)}, 'files': [{'path': scene + '.png', 'kind': 'screenshot'}, {'path': scene + '.zoom.png', 'kind': 'screenshot'}, {'path': scene + '.metrics.json', 'kind': 'metrics'}, {'path': scene + '.aria.json', 'kind': 'aria'}], 'case_results': results})
            page.close()
        browser.close()
    assert not errors, errors
    write(OUTPUT / (CHECK + '.ui.json'), {'schema_version': 3, 'scenarios': reports})
    print(f'Observed {sum(len(s["case_results"]) for s in reports)} cases in {len(reports)} real Chromium scenarios; {OUTPUT}')


if __name__ == '__main__':
    main()
