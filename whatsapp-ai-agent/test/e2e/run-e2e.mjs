// End-to-end tests: drives the real n8n workflow through the local mock APIs.
// Expects n8n on :5678 (workflow published) and mock-apis.mjs on :8899/:8898.
// Usually started via ./run.sh
import { textMessage, imageMessage, statusUpdate } from './payload.mjs';

const N8N = process.env.N8N_URL || 'http://localhost:5678';
const CONTROL = 'http://127.0.0.1:8898';
const OWNER = '923009999999';
const run = Date.now().toString().slice(-6);
const phone = (n) => `9230${n}${run}`; // fresh numbers each run so memory starts empty

let passed = 0;
let failed = 0;
const check = (name, cond, detail = '') => {
  if (cond) { passed++; console.log(`  ✅ ${name}`); } else { failed++; console.log(`  ❌ ${name}${detail ? `\n       ${detail}` : ''}`); }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const state = async () => (await fetch(`${CONTROL}/state`)).json();
const config = (c) => fetch(`${CONTROL}/config`, { method: 'POST', body: JSON.stringify(c) });
const post = (payload) => fetch(`${N8N}/webhook/whatsapp`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });

const isReply = (c, to) => c.host === 'graph.facebook.com' && c.body.type === 'text' && c.body.to === to;
const claudeCalls = (s, to) => s.calls.filter((c) => c.host === 'api.anthropic.com' && JSON.stringify(c.body).includes(`+${to}`));
const sheetRow = (s, to) => {
  const [head, ...rows] = s.sheet;
  const row = rows.find((r) => r[0] === `+${to}`);
  return row ? Object.fromEntries(head.map((h, i) => [h, row[i] ?? ''])) : null;
};
async function waitFor(pred, ms = 25000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const s = await state();
    if (pred(s)) return s;
    await sleep(300);
  }
  return state();
}
// A message is "done" when its lead row has been written (the last step before the owner alert).
async function sendAndWait(payload, to, text) {
  const before = (await state()).calls.filter((c) => isReply(c, to)).length;
  const res = await post(payload);
  const s = await waitFor((st) => st.calls.filter((c) => isReply(c, to)).length > before
    && (!text || (sheetRow(st, to) || {}).last_message === text));
  await sleep(1500); // let the owner alert (if any) go out
  return { res, s: await state(), before };
}
const replies = (s, to) => s.calls.filter((c) => isReply(c, to)).map((c) => c.body.text.body);
const ownerAlerts = (s) => s.calls.filter((c) => isReply(c, OWNER)).map((c) => c.body.text.body);

// Tomorrow in Asia/Karachi (UTC+5, no daylight saving)
const pk = new Date(Date.now() + 5 * 3600e3);
const tomorrow = new Date(pk.getTime() + 24 * 3600e3);
const tomorrowStr = tomorrow.toISOString().slice(0, 10);
const tomorrowIsWeekday = tomorrow.getUTCDay() >= 1 && tomorrow.getUTCDay() <= 5;

// n8n reports healthy slightly before published workflows' webhooks are live.
for (let i = 0; i < 60; i++) {
  const r = await fetch(`${N8N}/webhook/whatsapp?hub.verify_token=x`).catch(() => null);
  if (r && r.status !== 404) break;
  await sleep(1000);
}

await fetch(`${CONTROL}/reset`);
await config({ busy: [{ start: `${tomorrowStr}T05:00:00Z`, end: `${tomorrowStr}T06:00:00Z` }] }); // 10:00–11:00 PKT

console.log('\n1) Meta webhook verification');
{
  const ok = await fetch(`${N8N}/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=test-verify-token&hub.challenge=1158201444`);
  check('correct token → 200 + challenge', ok.status === 200 && (await ok.text()) === '1158201444');
  const bad = await fetch(`${N8N}/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=1`);
  check('wrong token → 403', bad.status === 403);
}

console.log('\n2) Delivery receipts are ignored');
{
  const res = await post(statusUpdate());
  await sleep(3000);
  const s = await state();
  check('webhook answers 200 immediately', res.status === 200);
  check('no Claude call, no reply', !s.calls.some((c) => c.host === 'api.anthropic.com' || (c.host === 'graph.facebook.com' && c.body.type === 'text')));
}

console.log('\n3) Full conversation: FAQ → lead details → booking');
const A = phone(1);
{
  const t1 = 'Hi, how much is a cleaning?';
  const { s } = await sendAndWait(textMessage({ from: A, name: 'Ali', text: t1 }), A, t1);
  const [call] = claudeCalls(s, A);
  const b = call?.body || {};
  check('Claude called once', claudeCalls(s, A).length === 1);
  check('auth + version headers', call?.headers['x-api-key'] === 'sk-ant-test' && call?.headers['anthropic-version'] === '2026-10-21');
  check('refusal fallback enabled (beta header + fallbacks: "default")', call?.headers['anthropic-beta'] === 'server-side-fallback-2026-07-01' && b.fallbacks === 'default');
  check('model claude-opus-5-5, effort low', b.model === 'claude-opus-5-5' && b.output_config?.effort === 'low');
  check('JSON structured output requested', b.output_config?.format?.type === 'json_schema');
  check('no sampling params / thinking config sent', !('temperature' in b) && !('top_p' in b) && !('top_k' in b) && !('thinking' in b));
  check('system prompt cached + contains FAQ', b.system?.[0]?.cache_control?.type === 'ephemeral' && b.system[0].text.includes('Frequently asked questions'));
  const ctx = b.messages?.[0]?.content?.[0]?.text || '';
  check('context has live slots', ctx.includes('AVAILABLE SLOTS') && /\d{4}-\d{2}-\d{2} \(/.test(ctx), ctx.slice(0, 400));
  if (tomorrowIsWeekday) {
    const line = ctx.split('\n').find((l) => l.startsWith(tomorrowStr)) || '';
    check('busy 10:00–11:00 tomorrow is excluded', line.includes('09:30') && !line.includes('10:00') && !line.includes('10:30') && line.includes('11:00'), line);
  }
  check('customer text passed as-is', b.messages?.[0]?.content?.[1]?.text === t1);
  const read = s.calls.find((c) => c.host === 'graph.facebook.com' && c.body.status === 'read' && c.body.to === undefined);
  check('marked as read + typing indicator', read?.body.typing_indicator?.type === 'text' && read?.headers.authorization === 'Bearer EAA-test-token');
  check('reply sent to customer', replies(s, A).some((r) => r.startsWith('Cleaning costs')));
  const row = sheetRow(s, A);
  check('lead saved to sheet (service + warm)', row?.service_interest === 'Cleaning' && row?.lead_score === 'warm', JSON.stringify(row));

  const t2 = 'My name is Ali Khan, this week please';
  const r2 = await sendAndWait(textMessage({ from: A, name: 'Ali', text: t2 }), A, t2);
  const call2 = claudeCalls(r2.s, A)[1]?.body || {};
  check('history sent on 2nd message (user, assistant, user)', call2.messages?.length === 3 && call2.messages[0].content === t1 && call2.messages[1].role === 'assistant');
  check('known lead details carried over', (call2.messages?.[2]?.content?.[0]?.text || '').includes('"service_interest":"Cleaning"'));
  const rows = r2.s.sheet.filter((r) => r[0] === `+${A}`);
  check('same sheet row updated (no duplicate)', rows.length === 1 && sheetRow(r2.s, A).name === 'Ali Khan' && sheetRow(r2.s, A).lead_score === 'hot', JSON.stringify(rows));

  const t3 = 'Yes book it';
  const msgId = `wamid.book${run}`;
  const r3 = await sendAndWait(textMessage({ from: A, name: 'Ali', text: t3, id: msgId }), A, t3);
  const ev = r3.s.calls.find((c) => c.host === 'www.googleapis.com' && c.path.endsWith('/events'));
  const firstSlot = (ctx.match(/^(\d{4}-\d{2}-\d{2}) \([^)]*\): (\d{2}:\d{2})/m) || []).slice(1).join('T');
  check('calendar event created', Boolean(ev), JSON.stringify(r3.s.calls.map((c) => c.path)));
  check('event title + description', ev?.body.summary === 'Cleaning – Ali Khan' && ev?.body.description.includes(`https://wa.me/${A}`), JSON.stringify(ev?.body));
  const startUtc = ev ? new Date(ev.body.start.dateTime).getTime() : 0;
  check('event at the offered slot (PKT) and 30 min long', startUtc === new Date(`${firstSlot}:00+05:00`).getTime()
    && new Date(ev?.body.end.dateTime).getTime() - startUtc === 30 * 60e3, `${ev?.body.start.dateTime} vs ${firstSlot}`);
  check('confirmation sent', replies(r3.s, A).at(-1)?.startsWith('Done!'));
  check('owner told about new booking', ownerAlerts(r3.s).some((a) => a.includes('New booking') && a.includes('Ali Khan')), JSON.stringify(ownerAlerts(r3.s)));
  check('appointment stored in sheet', Boolean(sheetRow(r3.s, A)?.appointment), JSON.stringify(sheetRow(r3.s, A)));

  const claudeBefore = claudeCalls(r3.s, A).length;
  await post(textMessage({ from: A, name: 'Ali', text: t3, id: msgId }));
  await sleep(4000);
  check('duplicate delivery ignored', claudeCalls(await state(), A).length === claudeBefore);

  const t4 = 'Thanks!';
  const r4 = await sendAndWait(textMessage({ from: A, name: 'Ali', text: t4 }), A, t4);
  const ctx4 = claudeCalls(r4.s, A).at(-1)?.body.messages.at(-1).content[0].text || '';
  check('existing appointment shown to Claude next time', /Appointment already booked by this customer: \w+day/.test(ctx4), ctx4.split('\n').find((l) => l.startsWith('Appointment')));
}

console.log('\n4) Claude picks a slot that is not free → not booked');
{
  const B = phone(2);
  const { s } = await sendAndWait(textMessage({ from: B, text: 'please book a bad slot' }), B, 'please book a bad slot');
  check('no calendar event', !s.calls.some((c) => c.path.endsWith('/events') && JSON.stringify(c.body).includes(B)));
  check('customer offered real alternatives', replies(s, B).at(-1)?.startsWith("Sorry, that time isn't available") && replies(s, B).at(-1).includes('•'), replies(s, B).at(-1));
}

console.log('\n5) Hand-off to a human');
{
  const C = phone(3);
  const { s } = await sendAndWait(textMessage({ from: C, name: 'Sana', text: 'Can I talk to a human please' }), C, 'Can I talk to a human please');
  check('customer told a person will follow up', replies(s, C).at(-1)?.includes('team member'));
  check('owner alerted', ownerAlerts(s).some((a) => a.includes('needs a human') && a.includes(C)), JSON.stringify(ownerAlerts(s)));
  const row = sheetRow(s, C);
  check('flagged in sheet', Boolean(row?.human_requested_at) && row?.handoff_reason === 'Customer asked for a person', JSON.stringify(row));
}

console.log('\n6) Claude API error → polite fallback');
{
  const D = phone(4);
  const { s } = await sendAndWait(textMessage({ from: D, text: 'fail api' }), D, 'fail api');
  check('retried 3 times', claudeCalls(s, D).length === 3, `got ${claudeCalls(s, D).length}`);
  check('fallback reply sent', replies(s, D).at(-1)?.startsWith("Sorry, I'm having a little trouble"));
  check('owner alerted', ownerAlerts(s).some((a) => a.includes(D)));
}

console.log('\n7) Claude declines (refusal) → polite fallback');
{
  const E = phone(5);
  const { s } = await sendAndWait(textMessage({ from: E, text: 'refuse this' }), E, 'refuse this');
  check('fallback reply sent', replies(s, E).at(-1)?.startsWith("Sorry, I'm having a little trouble"));
}

console.log('\n8) Image / voice note → asks for text');
{
  const F = phone(6);
  await post(imageMessage({ from: F }));
  const s = await waitFor((st) => st.calls.some((c) => isReply(c, F)), 15000);
  check('"please type" reply sent', replies(s, F)[0]?.includes('I can only read text'));
  check('Claude not called', claudeCalls(s, F).length === 0);
}

console.log('\n9) Google Calendar down → no booking promises');
{
  await config({ calendarFails: true });
  const G = phone(7);
  const { s } = await sendAndWait(textMessage({ from: G, text: 'hello' }), G, 'hello');
  const ctx = claudeCalls(s, G)[0]?.body.messages.at(-1).content[0].text || '';
  check('Claude told the calendar is unavailable', ctx.includes('UNAVAILABLE'));
  check('reply still sent', replies(s, G).length === 1);
  await config({ calendarFails: false });
}

console.log('\n10) Booking fails in Google Calendar → customer + owner informed');
{
  const H = phone(8);
  await sendAndWait(textMessage({ from: H, text: 'how much is a cleaning' }), H, 'how much is a cleaning');
  await config({ calendarCreateFails: true });
  const { s } = await sendAndWait(textMessage({ from: H, text: 'yes book it' }), H, 'yes book it');
  check('customer told booking could not be confirmed', replies(s, H).at(-1)?.includes("couldn't confirm that booking"), replies(s, H).at(-1));
  check('owner alerted about failed booking', ownerAlerts(s).some((a) => a.includes(H) && a.includes('Calendar booking failed')), JSON.stringify(ownerAlerts(s).slice(-1)));
  await config({ calendarCreateFails: false });
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
