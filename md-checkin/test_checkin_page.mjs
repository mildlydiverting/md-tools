// Offline test of the logic block in checkin-log.html.
// Run: node test_checkin_page.mjs
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';

const html = readFileSync(new URL('./checkin-log.html', import.meta.url), 'utf8');
const code = html.split('/* ==== LOGIC')[1].split('/* ==== END LOGIC')[0];
const sandbox = { module: { exports: {} } };
vm.runInNewContext('/*' + code, sandbox);
const L = sandbox.module.exports;
const eq = (a, b, msg) => assert.deepEqual(JSON.parse(JSON.stringify(a)), b, msg);  // sandbox arrays are another realm

// ---- A tiny in-memory Workflowy, speaking the API's URLs.
function fakeWorkflowy() {
  const nodes = new Map(); const days = new Map(); let n = 0;
  const add = (parent, name, extra = {}) => {
    const id = 'n' + (++n);
    nodes.set(id, { id, parent_id: parent, name, priority: n, completed: false, data: extra.data || {} });
    return id;
  };
  const inbox = add(null, 'Inbox');
  const resolve = (key, create) => {
    if (key === 'inbox') return inbox;
    if (/^\d{4}-\d{2}-\d{2}$/.test(key)) {
      if (!days.has(key)) { if (!create) return null; days.set(key, add(null, key)); }
      return days.get(key);
    }
    return nodes.has(key) ? key : null;
  };
  const res = (status, body) => ({ status, ok: status < 400, text: async () => JSON.stringify(body) });
  const origin = id => nodes.get(id).data.mirror?.origin_id || id;
  async function fetch(url, opts) {
    const u = new URL(url); const path = u.pathname.replace('/api/v1', ''); const m = opts.method;
    const body = opts.body ? JSON.parse(opts.body) : {};
    if (m === 'GET' && path === '/nodes') {
      const pid = resolve(u.searchParams.get('parent_id'));
      if (!pid) return res(404, {});
      return res(200, { nodes: [...nodes.values()].filter(x => x.parent_id === pid) });
    }
    let mm;
    if (m === 'GET' && (mm = path.match(/^\/nodes\/([^/]+)$/))) {
      const id = resolve(decodeURIComponent(mm[1])); return id ? res(200, { node: nodes.get(id) }) : res(404, {});
    }
    if (m === 'POST' && path === '/nodes') return res(200, { item_id: add(resolve(body.parent_id, true), body.name) });
    if (m === 'POST' && (mm = path.match(/^\/nodes\/(\w+)\/mirror$/))) {
      assert.ok(nodes.has(body.parent_id), 'mirror parent must be a real id');
      return res(200, { item_id: add(body.parent_id, nodes.get(mm[1]).name, { data: { mirror: { origin_id: mm[1] } } }) });
    }
    if (m === 'DELETE' && (mm = path.match(/^\/nodes\/(\w+)\/mirror$/))) { nodes.delete(mm[1]); return res(200, { status: 'ok' }); }
    if (m === 'POST' && (mm = path.match(/^\/nodes\/(\w+)\/(un)?complete$/))) {
      nodes.get(origin(mm[1])).completed = !mm[2]; return res(200, { status: 'ok' });
    }
    throw new Error('unhandled ' + m + ' ' + path);
  }
  return { fetch, nodes };
}

const T = '2026-11-21', Y = L.addDays(T, -1), Y2 = L.addDays(T, -2);
const wf = fakeWorkflowy();
const api = L.makeApi('k', wf.fetch);

// Day before yesterday: Jo + dentist (both new). Yesterday: Jo carried.
await L.addToToday(api, Y2, [{ text: 'Reply to Jo' }, { text: 'Book dentist' }], []);
let s = await L.collect(api, Y, 14);
const jo = s.earlier.find(t => t.text === 'Reply to Jo');
await L.addToToday(api, Y, [{ id: jo.id }], []);
await L.addToToday(api, Y2, [{ text: 'Spare idea' }], []);      // goes to inbox + Y2
// Today: Jo carried, a new teaching task, and a pure inbox task left alone.
await api.create({ parent_id: 'inbox', name: 'Inbox only' });
s = await L.collect(api, T, 14);
let r = await L.addToToday(api, T, [{ id: jo.id, text: 'Jo' }, { text: 'Teaching 10am' }, { id: jo.id, text: 'Jo' }], []);
eq(r.added, ['Jo', 'Teaching 10am']);
eq(r.skipped, ['Jo'], 'duplicate pick skipped');

s = await L.collect(api, T, 14);
eq(s.todayItems.map(t => t.text), ['Reply to Jo', 'Teaching 10am'], 'order follows the page');
const joT = s.todayItems[0];
assert.equal(joT.daysOn, 2); assert.equal(joT.firstDate, Y2); assert.ok(joT.slipping);
eq(s.earlier.map(t => t.text).sort(), ['Book dentist', 'Spare idea']);
assert.ok(s.inbox.some(t => t.text === 'Inbox only'), 'inbox task offered');
assert.ok(!s.inbox.some(t => t.id === joT.id), "today's tasks not offered again");

// Tick via a mirror id's origin, then untick.
await api.complete(joT.id);
s = await L.collect(api, T, 14);
assert.ok(s.todayItems[0].done && !s.todayItems[0].slipping);
await api.uncomplete(joT.id);
s = await L.collect(api, T, 14);
assert.ok(!s.todayItems[0].done);

// Take off today: mirror goes, task stays, history stays.
await api.unmirror(s.todayItems[1].mirrors[T]);
s = await L.collect(api, T, 14);
eq(s.todayItems.map(t => t.text), ['Reply to Jo']);
assert.ok(s.inbox.some(t => t.text === 'Teaching 10am'), 'original still in inbox');

// Heading reused, not duplicated.
const before = wf.nodes.size; await L.ensureHeading(api, T); assert.equal(wf.nodes.size, before);

// Empty account.
const e = await L.collect(L.makeApi('k', fakeWorkflowy().fetch), T, 14);
assert.equal(e.todayItems.length + e.earlier.length + e.inbox.length, 0);

assert.equal(L.plain('<b>Hi</b> &amp; bye'), 'Hi & bye');
console.log('All page logic tests passed.');
