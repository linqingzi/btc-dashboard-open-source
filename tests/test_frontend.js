// Dependency-free DOM harness: exercise the existing renderer with synthetic input.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const code = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'data/latest.json'), 'utf8'));

function element() {
  return {
    textContent: '', innerHTML: '', className: '', style: {}, nextElementSibling: null,
    classList: { contains() { return false; } },
    parentNode: { insertBefore(child) { this.inserted = child; } },
  };
}

async function run(payload) {
  const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], element()]));
  const requests = [];
  const context = vm.createContext({
    console,
    document: { getElementById: id => elements.get(id), createElement: element },
    fetch: async url => {
      requests.push(url);
      assert.equal(url, 'data/latest.json', 'only the local synthetic fixture may be requested');
      return { ok: true, json: async () => payload };
    },
    setInterval() { throw new Error('automatic polling is disabled in the demo'); },
  });
  await vm.runInContext(code, context, { filename: 'app.js', timeout: 2000 });
  return { elements, requests };
}

async function main() {
  assert(!/<(?:script|link|img)[^>]+(?:src|href)=["']https?:/i.test(html), 'no remote page assets');
  assert(html.includes('SYNTHETIC DEMO'), 'visible synthetic warning is required');
  const withoutMeeting = await run(structuredClone(fixture));
  assert.deepEqual(withoutMeeting.requests, ['data/latest.json']);
  assert.equal(withoutMeeting.elements.get('hero-score').textContent, fixture.scoring.score.bullish_ratio.toFixed(1) + '%');
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

  const calendarExample = structuredClone(fixture);
  calendarExample.macro.fomc = {
    next_meeting: { iso_date: '2000-01-03T12:00:00Z', days_until: 2 },
    last_decision: { iso_date: '1999-12-30T12:00:00Z', days_ago: 2 },
    current_rate: { effective_rate: 4.0 },
  };
  const withMeeting = await run(calendarExample);
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('下次 FOMC'));
  assert(withMeeting.elements.get('grid-macro').innerHTML.includes('上次 FOMC'));
  assert(withMeeting.elements.get('grid-supply').innerHTML.includes('card-name'));

  const rejected = structuredClone(fixture);
  rejected.meta.synthetic = false;
  const refusal = await run(rejected);
  assert.equal(refusal.elements.get('hero-title').textContent, '数据加载失败');
  assert.equal(refusal.elements.get('hero-sub').textContent, '此开源演示仅接受合成数据');
  console.log('Frontend checks passed: all 8 grids, 20 indicators, optional calendar, synthetic-only input, and one local request.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
