// Dependency-free DOM harness: exercise the existing renderer with synthetic input.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const code = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const translations = fs.readFileSync(path.join(root, 'i18n.js'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'data/latest.json'), 'utf8'));

function element() {
  return {
    textContent: '', innerHTML: '', className: '', style: {}, nextElementSibling: null,
    attributes: {}, listeners: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
    classList: { contains() { return false; } },
    parentNode: { insertBefore(child) { this.inserted = child; } },
  };
}

async function run(payload) {
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], element()]));
  const requests = [];
  const context = vm.createContext({
    console,
    document: { getElementById: id => elements.get(id), createElement: element, documentElement: { lang: 'zh-CN' } },
    fetch: async url => {
      requests.push(url);
      assert.equal(url, 'data/latest.json', 'only the local synthetic fixture may be requested');
      return { ok: true, json: async () => payload };
    },
    setInterval() { throw new Error('automatic polling is disabled in the demo'); },
  });
  vm.runInContext(translations, context, { filename: 'i18n.js', timeout: 2000 });
  await vm.runInContext(code, context, { filename: 'app.js', timeout: 2000 });
  return { elements, requests, context };
}

async function main() {
  assert(!/<(?:script|link|img)[^>]+(?:src|href)=["']https?:/i.test(html), 'no remote page assets');
  assert(/Synthetic demo/i.test(html), 'visible synthetic warning is required');
  const withoutMeeting = await run(structuredClone(fixture));
  assert.deepEqual(withoutMeeting.requests, ['data/latest.json']);
  assert.equal(withoutMeeting.elements.get('hero-score').textContent, fixture.scoring.score.bullish_ratio.toFixed(1) + '%', withoutMeeting.elements.get('hero-sub').textContent);
  const grids = ['macro', 'etf', 'inst', 'stable', 'sentiment', 'deriv', 'onchain', 'supply'];
  for (const name of grids) {
    const content = withoutMeeting.elements.get('grid-' + name).innerHTML;
    assert(content.includes('card-name'), name + ' cards should render without a meeting calendar');
    assert(content.includes('合成示例'), name + ' should label invented data');
    assert(!content.includes('\\"'), name + ' should emit ordinary HTML attributes');
  }
  const details = withoutMeeting.elements.get('hero').parentNode.inserted.innerHTML;
  assert.equal((details.match(/<tr>/g) || []).length, fixture.scoring.indicators.length + 1);
  assert(!details.includes('[object Object]'), 'dictionary-valued indicators need a readable summary');
  assert(details.includes('5 项输入'), 'ETF input count should be visible');

  // Real click handlers change only presentation, reuse the loaded payload, and
  // preserve every numerical score cell and the complete input object.
  const inputBefore = JSON.stringify(withoutMeeting.context.latestPayload);
  const numericCells = markup => [...markup.matchAll(/<tr>(.*?)<\/tr>/gs)].slice(1).map(row => {
    const cells = [...row[1].matchAll(/<td[^>]*>(.*?)<\/td>/gs)].map(match => match[1]);
    return [3, 4, 5, 6].map(index => cells[index]);
  });
  withoutMeeting.elements.get('lang-en').listeners.click();
  assert.equal(withoutMeeting.context.document.documentElement.lang, 'en');
  assert.equal(withoutMeeting.elements.get('lang-en').attributes['aria-pressed'], 'true');
  assert.equal(withoutMeeting.elements.get('notice-link').attributes.href, 'https://github.com/linqingzi/btc-dashboard-open-source/blob/main/README.en.md');
  assert.equal(withoutMeeting.elements.get('hero-title').textContent, 'Bearish (demo)');
  assert.equal(withoutMeeting.elements.get('hero-score').textContent, fixture.scoring.score.bullish_ratio.toFixed(1) + '%');
  const englishDetails = withoutMeeting.elements.get('hero').parentNode.inserted.innerHTML;
  assert.deepEqual(numericCells(details), numericCells(englishDetails));
  assert(!/\p{Script=Han}/u.test(englishDetails), 'every indicator, interpretation, state and tier must be in English');
  for (const name of grids) {
    const content = withoutMeeting.elements.get('grid-' + name).innerHTML;
    assert(content.includes('Synthetic example'), name + ' synthetic attribution must be in English');
    assert(!/\p{Script=Han}/u.test(content), name + ' contains untranslated text');
  }
  assert.equal(JSON.stringify(withoutMeeting.context.latestPayload), inputBefore);
  assert.deepEqual(withoutMeeting.requests, ['data/latest.json'], 'switching language must not fetch again');
  withoutMeeting.elements.get('lang-zh').listeners.click();
  assert.equal(withoutMeeting.context.document.documentElement.lang, 'zh-CN');
  assert.equal(withoutMeeting.elements.get('hero').parentNode.inserted.innerHTML, details);

  // Cover all rule interpretations, including branches absent from the demo.
  const scoringSource = fs.readFileSync(path.join(root, 'scripts/scoring.py'), 'utf8');
  const interpretationStrings = [...scoringSource.matchAll(/"interpretation_(?:bull|bear|neutral)":\s*"([^"]+)"/g)].map(match => match[1]);
  const alertStrings = [...scoringSource.matchAll(/alerts\.append\("([^"]+)"\)/g)].map(match => match[1]);
  assert.equal(interpretationStrings.length, 60);
  assert.equal(alertStrings.length, 5);
  for (const text of [...interpretationStrings, ...alertStrings]) {
    assert(!/\p{Script=Han}/u.test(withoutMeeting.context.DashboardI18n.translate(text, 'en')), 'missing rule translation: ' + text);
  }
  const uiLiterals = [...code.matchAll(/(['"])((?:\\.|(?!\1)[^\\\r\n])*)\1/g)].map(match => match[2]).filter(text => /\p{Script=Han}/u.test(text));
  for (const text of uiLiterals) {
    assert(!/\p{Script=Han}/u.test(withoutMeeting.context.DashboardI18n.translate(text, 'en')), 'missing UI translation: ' + text);
  }
  assert.equal(withoutMeeting.context.DashboardI18n.indicatorKeys.length, fixture.scoring.indicators.length);

  const calendarExample = structuredClone(fixture);
  calendarExample.macro.fomc = {
    next_meeting: { iso_date: '2000-01-03T12:00:00Z', days_until: 2 },
    last_decision: { iso_date: '1999-12-30T12:00:00Z', days_ago: 2 },
    current_rate: { effective_rate: 4.0 },
  };
  calendarExample.macro.implied_rate = 3.5;
  const withMeeting = await run(calendarExample);
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('下次 FOMC'));
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('上次 FOMC'));
  assert(withMeeting.elements.get('grid-supply').innerHTML.includes('card-name'));
  withMeeting.elements.get('lang-en').listeners.click();
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('Next FOMC meeting'));
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('Previous FOMC decision'));
  assert(!/\p{Script=Han}/u.test(withMeeting.elements.get('grid-macro').innerHTML));

  const missingEtf = structuredClone(fixture);
  delete missingEtf.macro.etf;
  const placeholder = await run(missingEtf);
  placeholder.elements.get('lang-en').listeners.click();
  assert(!/\p{Script=Han}/u.test(placeholder.elements.get('grid-etf').innerHTML));

  const rejected = structuredClone(fixture);
  rejected.meta.synthetic = false;
  const refusal = await run(rejected);
  assert.equal(refusal.elements.get('hero-title').textContent, '数据加载失败');
  assert.equal(refusal.elements.get('hero-sub').textContent, '此开源演示仅接受合成数据');
  refusal.elements.get('lang-en').listeners.click();
  assert.equal(refusal.elements.get('hero-title').textContent, 'Data could not be loaded');
  assert.equal(refusal.elements.get('hero-sub').textContent, 'This open-source demo only accepts synthetic data');
  console.log('Frontend checks passed: Chinese/English click handlers, all 8 grids and 20 indicators, 60 interpretations and 5 alerts, unchanged data/scores, calendar/placeholders/errors, and one local request.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
