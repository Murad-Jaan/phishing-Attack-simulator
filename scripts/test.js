// Unit tests for the simulator logic. Run: node scripts/test.js [index.html]
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(process.argv[2] || 'index.html', 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
const els = {}, mk = () => ({ innerHTML: '', textContent: '', value: '', className: '', style: {}, scrollIntoView() {} });
const U = require('url').URL; U.createObjectURL = () => 'blob:x'; U.revokeObjectURL = () => {};
const ctx = { console, Math, setTimeout, URL: U, localStorage: { getItem: () => null, setItem() {} }, confirm: () => true,
  Blob: class { constructor(p) { ctx.lastBlob = p.join(''); } }, FileReader: class {},
  document: { getElementById: id => els[id] || (els[id] = mk()), createElement: () => ({ click() {} }) } };
vm.createContext(ctx); vm.runInContext(js, ctx);
const run = c => vm.runInContext(c, ctx);
let n = 0, failed = 0;
const t = (name, fn) => { try { fn(); n++; console.log('ok   ' + name); } catch (e) { failed++; console.log('FAIL ' + name + ' -> ' + e.message); } };

t('every scenario: phishing scores clearly above legitimate', () => {
  const sc = run('SC'), rows = sc.map((s, i) => {
    run(`scan(${JSON.stringify(s.from.toLowerCase())},${JSON.stringify((s.link || '').toLowerCase())},${JSON.stringify((s.sub + ' ' + s.body + ' ' + (s.att || '')).toLowerCase())})`);
    return { p: s.p, score: run('lastP') };
  });
  const minPhish = Math.min(...rows.filter(r => r.p).map(r => r.score)), maxLegit = Math.max(...rows.filter(r => !r.p).map(r => r.score));
  assert(minPhish >= 30, 'lowest phishing score ' + minPhish);
  assert(maxLegit < 30, 'highest legitimate score ' + maxLegit);
});
t('sample phishing email is high risk', () => {
  run('scan("security@paypa1-support.com","http://paypa1-verify.com/login","dear customer, urgent: verify your password within 24 hours or your account will be suspended.")');
  assert(run('lastP') >= 60);
});
t('answer logic ok()', () => { assert.strictEqual(run('ok(0,"phish")'), true); assert.strictEqual(run('ok(0,"report")'), true); assert.strictEqual(run('ok(0,"legit")'), false); assert.strictEqual(run('ok(1,"legit")'), true); });
t('score(): accuracy and click penalty', () => {
  run('S.res={"1|0|0":{a:"phish"},"1|1|0":{a:"legit"}}'); assert.strictEqual(run('score(0)'), 100);
  run('S.res={"1|0|0":{a:"phish",click:true}}'); assert.strictEqual(run('score(0)'), 90);
  run('S.res={}'); assert.strictEqual(run('score(0)'), null);
});
t('esc() neutralises HTML and quotes', () => { const o = run(`esc('<img onerror=1> "x" \\'y\\' &')`); assert(!/[<>"']/.test(o)); });
t('campaign creation, auto-simulation and stats', () => {
  run('S={camps:[],res:{}}'); els.cn = { value: 'T' }; els.cd = { value: 'IT' }; els.cf = { value: 'easy' };
  run('newCamp()'); assert.strictEqual(run('S.camps.length'), 1); assert.strictEqual(run('S.camps[0].emps.length'), 2); assert.strictEqual(run('S.camps[0].scs.length'), 2);
  run('simulate()'); assert.strictEqual(run('stats().sent'), 4); assert.strictEqual(run('stats().good+stats().bad'), 4);
});
t('all views render without errors', () => {
  for (const v of ['it', 'emp', 'dp', 'tips']) { run(`go("${v}")`); assert(els.app.innerHTML.length > 100, v + ' empty'); }
  assert(els.app.innerHTML.includes('Phishing attack visualization'));
});
const eml = h => `${h}\n\n`;
t('real email: forged headers and deceptive link are caught', () => {
  els['e-org'] = { value: '' };
  run('emlText(' + JSON.stringify(eml('From: "PayPal" <service@paypa1-support.com>\nReply-To: <collect@evil-mail.ru>\nReturn-Path: <bounce@other.net>\nAuthentication-Results: mx.google.com; spf=fail; dkim=fail; dmarc=fail\nSubject: Urgent verify your password') + '<a href="http://evil-login.com/x">https://paypal.com/login</a> verify your password within 24 hours') + ')');
  const o = els['e-out'].innerHTML;
  ['High risk', 'SPF check failed', 'DMARC check failed', 'Reply-To domain', 'goes to evil-login.com'].forEach(x => assert(o.includes(x), 'missing: ' + x));
});
t('real email: clean message is low risk', () => {
  els['e-org'] = { value: 'company.com' };
  run('emlText(' + JSON.stringify(eml('From: HR <hr@company.com>\nAuthentication-Results: mx; spf=pass; dkim=pass; dmarc=pass\nSubject: Team lunch') + 'Lunch is on Friday at 1 PM.') + ')');
  assert(els['e-out'].innerHTML.includes('Low risk'));
});
t('CSV export neutralises formula injection', () => {
  run('S={camps:[{id:1,name:"=cmd()",emps:[0],scs:[0]}],res:{"1|0|0":{a:"phish"}}}'); run('exportCsv()');
  assert(ctx.lastBlob.includes(`"'=cmd()"`), ctx.lastBlob);
});
console.log(`\n${n} passed, ${failed} failed`); process.exit(failed ? 1 : 0);
