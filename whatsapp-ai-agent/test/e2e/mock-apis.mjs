// Local stand-ins for the Claude API, WhatsApp Cloud API, Google Calendar and
// Google Sheets, so the real n8n workflow can be tested end-to-end offline.
//
// It runs as an HTTP(S) proxy: start n8n with HTTPS_PROXY pointing here and
// NODE_EXTRA_CA_CERTS trusting the test certificate. A small control API on a
// second port lets the test runner read what n8n sent and change behaviour.
//
//   node mock-apis.mjs <proxyPort> <controlPort> <certDir>
import http from 'node:http';
import tls from 'node:tls';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const [proxyPort = 8899, controlPort = 8898, certDir = '.'] = process.argv.slice(2);
const key = readFileSync(join(certDir, 'key.pem'));
const cert = readFileSync(join(certDir, 'cert.pem'));

const HEADERS = ['phone', 'whatsapp_name', 'name', 'service_interest', 'timeline', 'budget', 'email',
  'lead_score', 'lead_summary', 'appointment', 'human_requested_at', 'handoff_reason', 'last_message',
  'first_contact', 'last_contact'];

let state;
const reset = () => {
  state = {
    calls: [], // every request n8n made: { host, method, path, body }
    config: { calendarFails: false, calendarCreateFails: false, busy: [] },
    sheet: [HEADERS.slice()],
    counter: 0,
  };
};
reset();

// ───────────── tiny Google Sheets emulator (A1 ranges) ─────────────
const colToNum = (c) => [...c.toUpperCase()].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0);
function parseRange(range) {
  const decoded = decodeURIComponent(range);
  const [, cells = ''] = decoded.includes('!') ? decoded.split('!') : [decoded, ''];
  if (!cells) return { c1: 1, r1: 1, c2: Infinity, r2: Infinity };
  const [a, b = a] = cells.split(':');
  const p = (x) => {
    const m = x.match(/^([A-Za-z]*)(\d*)$/);
    return { c: m[1] ? colToNum(m[1]) : null, r: m[2] ? Number(m[2]) : null };
  };
  const A = p(a); const B = p(b);
  return { c1: A.c || 1, r1: A.r || 1, c2: B.c || Infinity, r2: B.r || Infinity };
}
function readValues(range) {
  const { c1, r1, c2, r2 } = parseRange(range);
  const rows = [];
  for (let r = r1; r <= Math.min(r2, state.sheet.length); r++) {
    const row = state.sheet[r - 1] || [];
    rows.push(row.slice(c1 - 1, c2 === Infinity ? undefined : c2));
  }
  while (rows.length && rows[rows.length - 1].every((v) => v === '' || v == null)) rows.pop();
  return rows;
}
function writeValues(range, values) {
  const { c1, r1 } = parseRange(range);
  values.forEach((row, i) => {
    const r = r1 - 1 + i;
    while (state.sheet.length <= r) state.sheet.push([]);
    row.forEach((v, j) => { state.sheet[r][c1 - 1 + j] = v; });
  });
}

// ───────────── fake Claude ─────────────
function claudeReply(body) {
  const last = body.messages[body.messages.length - 1];
  const blocks = Array.isArray(last.content) ? last.content : [{ type: 'text', text: last.content }];
  const context = blocks[0].text;
  const text = blocks[blocks.length - 1].text.toLowerCase();
  const firstSlot = (() => {
    const m = context.match(/^(\d{4}-\d{2}-\d{2}) \([^)]*\): (\d{2}:\d{2})/m);
    return m ? `${m[1]}T${m[2]}` : '';
  })();
  const known = JSON.parse(context.match(/Known customer details: (.*)$/m)[1]);
  const lead = { ...known };
  let out = { reply: 'We are open Monday to Saturday. How can I help?', action: 'none', slot_id: '', handoff_reason: '' };

  if (text.includes('fail api')) return { status: 400, json: { type: 'error', error: { type: 'invalid_request_error', message: 'mock bad request' } } };
  if (text.includes('refuse')) {
    return { status: 200, json: { id: 'msg_r', type: 'message', role: 'assistant', model: body.model, content: [], stop_reason: 'refusal', stop_details: { type: 'refusal', category: null }, usage: { input_tokens: 10, output_tokens: 0 } } };
  }
  if (text.includes('cleaning')) {
    Object.assign(lead, { service_interest: 'Cleaning', score: 'warm', summary: 'Asked about cleaning' });
    out.reply = `Cleaning costs Rs. 5,000. The next free time is ${firstSlot}. Would you like it? May I have your name?`;
  }
  if (text.includes('my name is ali')) {
    Object.assign(lead, { name: 'Ali Khan', timeline: 'this week', score: 'hot', summary: 'Wants cleaning this week' });
    out.reply = 'Thanks Ali! Shall I book it?';
  }
  if (text.includes('yes book')) {
    out = { reply: `Done! You're booked for ${firstSlot}.`, action: 'book_appointment', slot_id: firstSlot, handoff_reason: '' };
  }
  if (text.includes('book a bad slot')) {
    out = { reply: 'Booked for 1 Jan 2020!', action: 'book_appointment', slot_id: '2020-01-01T09:00', handoff_reason: '' };
  }
  if (text.includes('human')) {
    out = { reply: 'Sure — a team member will contact you shortly.', action: 'handoff_to_human', slot_id: '', handoff_reason: 'Customer asked for a person' };
  }
  return {
    status: 200,
    json: {
      id: `msg_${++state.counter}`,
      type: 'message',
      role: 'assistant',
      model: body.model,
      content: [
        { type: 'thinking', thinking: '', signature: 'sig' },
        { type: 'text', text: JSON.stringify({ ...out, lead }) },
      ],
      stop_reason: 'end_turn',
      usage: { input_tokens: 1200, output_tokens: 80, cache_read_input_tokens: 900 },
    },
  };
}

// ───────────── request router ─────────────
const KEEP_HEADERS = ['x-api-key', 'anthropic-version', 'anthropic-beta', 'authorization', 'content-type'];
function route(host, method, url, body, reqHeaders = {}) {
  const u = new URL(url, `https://${host}`);
  const path = u.pathname;
  const headers = Object.fromEntries(KEEP_HEADERS.filter((h) => reqHeaders[h]).map((h) => [h, reqHeaders[h]]));
  state.calls.push({ host, method, path, query: Object.fromEntries(u.searchParams), headers, body });

  if (host === 'api.anthropic.com' && path === '/v1/messages') return claudeReply(body);

  if (host === 'graph.facebook.com' && /\/messages$/.test(path)) {
    if (body.status === 'read') return { status: 200, json: { success: true } };
    return { status: 200, json: { messaging_product: 'whatsapp', contacts: [{ input: body.to, wa_id: body.to }], messages: [{ id: `wamid.out${++state.counter}` }] } };
  }

  if (host === 'www.googleapis.com' && path === '/calendar/v3/freeBusy') {
    const id = body.items[0].id;
    if (state.config.calendarFails) return { status: 200, json: { calendars: { [id]: { errors: [{ domain: 'global', reason: 'notFound' }], busy: [] } } } };
    return { status: 200, json: { kind: 'calendar#freeBusy', timeMin: body.timeMin, timeMax: body.timeMax, calendars: { [id]: { busy: state.config.busy } } } };
  }
  if (host === 'www.googleapis.com' && /^\/calendar\/v3\/calendars\/[^/]+\/events$/.test(path) && method === 'POST') {
    if (state.config.calendarCreateFails) return { status: 500, json: { error: { code: 500, message: 'mock calendar outage' } } };
    return { status: 200, json: { kind: 'calendar#event', id: `evt_${++state.counter}`, status: 'confirmed', summary: body.summary, start: body.start, end: body.end, htmlLink: 'https://calendar.google.com/x' } };
  }

  if (host === 'sheets.googleapis.com') {
    const m = path.match(/^\/v4\/spreadsheets\/([^/:]+)(.*)$/);
    const rest = m ? m[2] : '';
    if (method === 'GET' && rest === '') {
      return { status: 200, json: { spreadsheetId: m[1], sheets: [{ properties: { sheetId: 0, title: 'Leads', index: 0, gridProperties: { rowCount: 1000, columnCount: 26 } } }] } };
    }
    let mm;
    if (method === 'GET' && (mm = rest.match(/^\/values\/(.+)$/))) {
      return { status: 200, json: { range: decodeURIComponent(mm[1]), majorDimension: 'ROWS', values: readValues(mm[1]) } };
    }
    if (method === 'POST' && rest === '/values:batchUpdate') {
      for (const d of body.data || []) writeValues(d.range, d.values);
      return { status: 200, json: { spreadsheetId: m[1], totalUpdatedRows: (body.data || []).length } };
    }
    if (method === 'POST' && (mm = rest.match(/^\/values\/(.+):append$/))) {
      const startRow = state.sheet.length + 1;
      writeValues(`Leads!A${startRow}`, body.values);
      return { status: 200, json: { spreadsheetId: m[1], updates: { updatedRange: `Leads!A${startRow}`, updatedRows: body.values.length } } };
    }
    if (method === 'PUT' && (mm = rest.match(/^\/values\/(.+)$/))) {
      writeValues(mm[1], body.values);
      return { status: 200, json: { spreadsheetId: m[1], updatedRange: decodeURIComponent(mm[1]) } };
    }
    if (method === 'POST' && rest === ':batchUpdate') return { status: 200, json: { spreadsheetId: m[1], replies: [] } };
  }

  console.error(`[mock] unhandled ${method} https://${host}${url}`);
  return { status: 404, json: { error: { message: `mock: no route for ${method} ${host}${path}` } } };
}

function handle(host) {
  return (req, res) => {
    let raw = '';
    req.on('data', (c) => { raw += c; });
    req.on('end', () => {
      let body = {};
      try { body = raw ? JSON.parse(raw) : {}; } catch { body = { raw }; }
      const { status, json } = route(host || req.headers.host, req.method, req.url, body, req.headers);
      res.writeHead(status, { 'content-type': 'application/json' });
      res.end(JSON.stringify(json));
    });
  };
}

// ───────────── the proxy (terminates TLS for CONNECT tunnels) ─────────────
const proxy = http.createServer((req, res) => {
  // Plain-HTTP proxy request (absolute URL)
  const u = new URL(req.url);
  req.url = u.pathname + u.search;
  handle(u.host)(req, res);
});
proxy.on('connect', (req, clientSocket, head) => {
  const host = req.url.split(':')[0];
  clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
  const tlsSocket = new tls.TLSSocket(clientSocket, { isServer: true, key, cert });
  if (head && head.length) clientSocket.unshift(head);
  const inner = http.createServer(handle(host));
  inner.emit('connection', tlsSocket);
});
proxy.listen(Number(proxyPort), '127.0.0.1', () => console.log(`[mock] proxy on ${proxyPort}`));

// ───────────── control API for the test runner ─────────────
http.createServer((req, res) => {
  let raw = '';
  req.on('data', (c) => { raw += c; });
  req.on('end', () => {
    if (req.url === '/state') { res.end(JSON.stringify(state)); return; }
    if (req.url === '/reset') { reset(); res.end('{}'); return; }
    if (req.url === '/clear-calls') { state.calls = []; res.end('{}'); return; }
    if (req.url === '/config') { Object.assign(state.config, JSON.parse(raw || '{}')); res.end('{}'); return; }
    res.statusCode = 404; res.end('{}');
  });
}).listen(Number(controlPort), '127.0.0.1', () => console.log(`[mock] control on ${controlPort}`));
