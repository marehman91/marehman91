// Builds ../n8n-workflow.json from the code files in ./code.
// You only need this if you change the JavaScript in ./code and want to
// regenerate the importable workflow:   node src/build-workflow.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const code = (file) => readFileSync(join(here, 'code', file), 'utf8');

// Stable IDs so the generated file doesn't change on every build.
const uuid = (seed) => {
  const h = createHash('sha1').update(seed).digest('hex');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`;
};

const S = (field) => `$('Business Settings').first().json.${field}`;
const GRAPH_URL = `=https://graph.facebook.com/{{ ${S('graph_api_version')} }}/{{ $('Extract message').item.json.phone_number_id }}/messages`;

// ───────────────────────── Business Settings (edit-me node) ─────────────────────────
const settings = [
  ['business_name', 'Bright Smile Dental Clinic'],
  ['assistant_name', 'Sara'],
  ['business_description', 'A friendly family dental clinic. We offer check-ups, cleaning, whitening, fillings and braces consultations for adults and children. Address: 12 Main Boulevard, Your City. Phone: +92 300 0000000.'],
  ['services', [
    '• Check-up & consultation — Rs. 2,000 (30 min)',
    '• Scaling & polishing (cleaning) — Rs. 5,000 (30 min)',
    '• Teeth whitening — from Rs. 25,000 (60 min, needs a check-up first)',
    '• Fillings — from Rs. 4,000 (price depends on the tooth)',
    '• Braces consultation — Rs. 3,000 (30 min)',
  ].join('\n')],
  ['business_hours', 'mon-fri=09:00-13:00,14:00-18:00; sat=10:00-14:00; sun=closed'],
  ['timezone', 'Asia/Karachi'],
  ['appointment_length_minutes', 30, 'number'],
  ['booking_days_ahead', 14, 'number'],
  ['min_notice_hours', 2, 'number'],
  ['faq', [
    'Q: Where are you located? A: 12 Main Boulevard, Your City. Free parking is available behind the building.',
    'Q: Do you accept walk-ins? A: We prefer appointments, but we see dental emergencies the same day.',
    'Q: What payment methods do you accept? A: Cash, debit/credit cards, and bank transfer.',
    'Q: Do you accept insurance? A: Yes, most major health insurance plans. Bring your insurance card to your visit.',
    'Q: Do you treat children? A: Yes, from age 3 upwards.',
    'Q: What is your cancellation policy? A: Please let us know at least 24 hours before your appointment.',
    'Q: Is teeth whitening safe? A: Yes, when done by a dentist. We do a check-up first to make sure it is right for you.',
    'Q: What should I do in a dental emergency outside opening hours? A: Call our emergency line +92 300 0000001.',
  ].join('\n')],
  ['lead_questions', [
    '1. Which service they are interested in',
    '2. When they would like to come in (timeline)',
    '3. Whether this is their first visit',
    '4. Their name',
  ].join('\n')],
  ['lead_scoring_rules', [
    'hot = wants to book soon (within ~2 weeks) or has already booked',
    'warm = interested in a specific service but undecided or later than 2 weeks',
    'cold = only asking general questions or prices, no clear intent',
    'unknown = not enough information yet',
  ].join('\n')],
  ['extra_rules', [
    '• Never diagnose or give medical advice — suggest a check-up instead.',
    '• Do not offer discounts.',
    '• If the customer mentions severe pain, swelling or bleeding, tell them to call the emergency line right away.',
  ].join('\n')],
  ['owner_whatsapp_number', 'PASTE_YOUR_OWN_NUMBER_eg_923001234567'],
  ['google_calendar_id', 'PASTE_YOUR_GMAIL_ADDRESS@gmail.com'],
  ['google_sheet_url', 'PASTE_YOUR_GOOGLE_SHEET_URL'],
  ['whatsapp_verify_token', 'CHANGE-ME-to-any-secret-words-42'],
  ['whatsapp_phone_number_id', ''],
  ['graph_api_version', 'v26.0'],
  ['claude_model', 'claude-opus-5-5'],
  ['claude_effort', 'low'],
  ['fallback_reply', "Sorry, I'm having a little trouble right now. A member of our team will get back to you shortly 🙏"],
  ['unsupported_message_reply', 'Thanks for your message! I can only read text at the moment — could you please type your question? 😊'],
  ['slot_unavailable_reply', "Sorry, that time isn't available any more. Here are the next free times:"],
  ['booking_failed_reply', "Sorry, I couldn't confirm that booking in our calendar just now. A member of our team will contact you shortly to confirm your appointment 🙏"],
];

// ───────────────────────── helpers to build nodes ─────────────────────────
const nodes = [];
const connections = {};
const node = (name, type, typeVersion, position, parameters, extra = {}) => {
  nodes.push({ parameters, id: uuid(name), name, type, typeVersion, position, ...extra });
  return name;
};
const connect = (from, to, outputIndex = 0) => {
  connections[from] = connections[from] || { main: [] };
  while (connections[from].main.length <= outputIndex) connections[from].main.push([]);
  connections[from].main[outputIndex].push({ node: to, type: 'main', index: 0 });
};
const sticky = (name, position, width, height, color, content) =>
  node(name, 'n8n-nodes-base.stickyNote', 1, position, { content, height, width, color });

const ifNode = (name, position, conditions, combinator = 'and') => node(name, 'n8n-nodes-base.if', 2.2, position, {
  conditions: {
    options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
    conditions: conditions.map((c, i) => ({ id: uuid(`${name}-${i}`), ...c })),
    combinator,
  },
  looseTypeValidation: true,
  options: {},
});
const isTrue = (leftValue) => ({ leftValue, rightValue: '', operator: { type: 'boolean', operation: 'true', singleValue: true } });
const equals = (leftValue, rightValue) => ({ leftValue, rightValue, operator: { type: 'string', operation: 'equals' } });
const notEmpty = (leftValue) => ({ leftValue, rightValue: '', operator: { type: 'string', operation: 'notEmpty', singleValue: true } });
const notStartsWith = (leftValue, rightValue) => ({ leftValue, rightValue, operator: { type: 'string', operation: 'notStartsWith' } });

const whatsappPost = (name, position, bodyExpr, extra = {}) => node(name, 'n8n-nodes-base.httpRequest', 4.2, position, {
  method: 'POST',
  url: GRAPH_URL,
  authentication: 'genericCredentialType',
  genericAuthType: 'httpHeaderAuth',
  sendBody: true,
  specifyBody: 'json',
  jsonBody: `={{ JSON.stringify(${bodyExpr}) }}`,
  options: { timeout: 30000 },
}, { onError: 'continueRegularOutput', ...extra });

const textMessage = (toExpr, bodyExpr) =>
  `{ messaging_product: 'whatsapp', recipient_type: 'individual', to: ${toExpr}, type: 'text', text: { preview_url: false, body: ${bodyExpr} } }`;

// ───────────────────────── sticky notes (instructions on the canvas) ─────────────────────────
sticky('Note: Start here', [-120, -660], 760, 440, 4, `## 📱 WhatsApp AI Agent (powered by Claude)
Answers customers · qualifies leads · books appointments · answers FAQs

**Setup checklist** (full guide in README.md):
1. Open **Business Settings** and fill in your business info, FAQs, hours and the PASTE_… fields.
2. Connect credentials (double-click each node with a ⚠️):
   • **Ask Claude** → Header Auth: name \`x-api-key\`, value = your Claude API key
   • All **WhatsApp** nodes → Header Auth: name \`Authorization\`, value \`Bearer YOUR_TOKEN\`
   • **Google Calendar** nodes → Google Calendar account
   • **Save lead to Google Sheets** → Google Sheets account
3. **Publish/activate** the workflow (top-right).
4. In Meta → WhatsApp → Configuration, set the Callback URL to this workflow's **Production URL** (open a webhook node to copy it) and the Verify token from Business Settings. Subscribe to **messages**.
5. Send "Hi" to your WhatsApp number 🎉`);

sticky('Note: Settings', [160, -120], 300, 120, 6, `### ✏️ EDIT THIS NODE
Your business info, FAQs, hours, prices & settings all live in **Business Settings**.`);

sticky('Note: Verification', [640, -420], 560, 170, 7, `### 🔐 Meta webhook verification
When you click **Verify and save** in Meta, Meta sends a GET request with your verify token. If it matches **whatsapp_verify_token**, we reply with Meta's challenge code.`);

sticky('Note: AI brain', [1400, -120], 1000, 160, 5, `### 🧠 The AI brain
Checks your free calendar slots → builds a prompt with your FAQs, the customer's details and chat history → asks **Claude** → double-checks the answer (e.g. only books times that are really free).`);

sticky('Note: Actions', [2620, -180], 1500, 140, 3, `### ⚡ Actions
Books the appointment in Google Calendar (if requested) → sends the WhatsApp reply → saves/updates the lead in Google Sheets (one row per customer) → messages you on WhatsApp for new bookings and when a human is needed.`);

// ───────────────────────── entry: webhooks + settings ─────────────────────────
const webhookGet = node('WhatsApp webhook (GET)', 'n8n-nodes-base.webhook', 2, [0, 0], {
  path: 'whatsapp',
  responseMode: 'responseNode',
  options: {},
}, { webhookId: uuid('webhook-get') });

const webhookPost = node('WhatsApp webhook (POST)', 'n8n-nodes-base.webhook', 2, [0, 220], {
  httpMethod: 'POST',
  path: 'whatsapp',
  responseMode: 'responseNode',
  options: {},
}, { webhookId: uuid('webhook-post') });

const settingsNode = node('Business Settings', 'n8n-nodes-base.set', 3.4, [240, 100], {
  assignments: {
    assignments: settings.map(([name, value, type = 'string']) => ({ id: uuid(`setting-${name}`), name, value, type })),
  },
  options: {},
});
connect(webhookGet, settingsNode);
connect(webhookPost, settingsNode);

// ───────────────────────── GET: Meta verification ─────────────────────────
const isVerification = ifNode("Is this Meta's verification check?", [480, 100], [
  isTrue(`={{ $('WhatsApp webhook (GET)').isExecuted }}`),
]);
connect(settingsNode, isVerification);

const tokenOk = ifNode('Verify token correct?', [720, -120], [
  equals(`={{ $('WhatsApp webhook (GET)').first().json.query['hub.verify_token'] }}`, `={{ ${S('whatsapp_verify_token')} }}`),
]);
connect(isVerification, tokenOk, 0);

const respondChallenge = node('Reply with challenge', 'n8n-nodes-base.respondToWebhook', 1.1, [960, -200], {
  respondWith: 'text',
  responseBody: `={{ $('WhatsApp webhook (GET)').first().json.query['hub.challenge'] }}`,
  options: { responseCode: 200 },
});
const respondForbidden = node('Reply 403 (wrong token)', 'n8n-nodes-base.respondToWebhook', 1.1, [960, -40], {
  respondWith: 'text',
  responseBody: 'Verify token does not match',
  options: { responseCode: 403 },
});
connect(tokenOk, respondChallenge, 0);
connect(tokenOk, respondForbidden, 1);

// ───────────────────────── POST: incoming messages ─────────────────────────
// Answer WhatsApp with "200 OK" straight away (Meta re-sends if we're slow).
const respondOk = node('Reply 200 OK to WhatsApp', 'n8n-nodes-base.respondToWebhook', 1.1, [720, 220], {
  respondWith: 'text',
  responseBody: 'OK',
  options: { responseCode: 200 },
});
connect(isVerification, respondOk, 1);

const extract = node('Extract message', 'n8n-nodes-base.code', 2, [960, 220], {
  jsCode: code('1-extract-message.js'),
});
connect(respondOk, extract);

const markRead = whatsappPost('WhatsApp: mark read + typing…', [1200, 220],
  `{ messaging_product: 'whatsapp', status: 'read', message_id: $('Extract message').item.json.last_message_id, typing_indicator: { type: 'text' } }`);
connect(extract, markRead);

const hasText = ifNode('Is it a text message?', [1200, 220], [isTrue(`={{ $('Extract message').item.json.has_text }}`)]);
connect(markRead, hasText);

const notText = whatsappPost('WhatsApp: "please type" reply', [1440, 420],
  textMessage(`$('Extract message').item.json.wa_id`, S('unsupported_message_reply')));
connect(hasText, notText, 1);

const checkCalendar = node('Check calendar availability', 'n8n-nodes-base.googleCalendar', 1.3, [1440, 140], {
  resource: 'calendar',
  calendar: { __rl: true, mode: 'id', value: `={{ ${S('google_calendar_id')} }}` },
  timeMin: '={{ $now }}',
  timeMax: `={{ $now.plus({ days: Number(${S('booking_days_ahead')}) || 14 }) }}`,
  options: { outputFormat: 'raw' },
}, { onError: 'continueRegularOutput' });
connect(hasText, checkCalendar, 0);

const build = node('Build Claude request', 'n8n-nodes-base.code', 2, [1680, 140], {
  mode: 'runOnceForEachItem',
  jsCode: code('2-build-claude-request.js'),
});
connect(checkCalendar, build);

const askClaude = node('Ask Claude', 'n8n-nodes-base.httpRequest', 4.2, [1920, 140], {
  method: 'POST',
  url: 'https://api.anthropic.com/v1/messages',
  authentication: 'genericCredentialType',
  genericAuthType: 'httpHeaderAuth',
  sendHeaders: true,
  specifyHeaders: 'json',
  jsonHeaders: '={{ JSON.stringify($json.request_headers) }}',
  sendBody: true,
  specifyBody: 'json',
  jsonBody: '={{ JSON.stringify($json.request_body) }}',
  options: { timeout: 120000 },
}, { retryOnFail: true, maxTries: 3, waitBetweenTries: 3000, onError: 'continueRegularOutput' });
connect(build, askClaude);

const parse = node('Parse Claude reply', 'n8n-nodes-base.code', 2, [2160, 140], {
  mode: 'runOnceForEachItem',
  jsCode: code('3-parse-claude-reply.js'),
});
connect(askClaude, parse);

const wantsBooking = ifNode('Book an appointment?', [2400, 140], [equals('={{ $json.action }}', 'book_appointment')]);
connect(parse, wantsBooking);

const createEvent = node('Create calendar event', 'n8n-nodes-base.googleCalendar', 1.3, [2640, 20], {
  calendar: { __rl: true, mode: 'id', value: `={{ ${S('google_calendar_id')} }}` },
  start: '={{ $json.event.start }}',
  end: '={{ $json.event.end }}',
  additionalFields: {
    summary: '={{ $json.event.summary }}',
    description: '={{ $json.event.description }}',
  },
}, { onError: 'continueRegularOutput' });
connect(wantsBooking, createEvent, 0);

const finalize = node('Finalize reply', 'n8n-nodes-base.code', 2, [2880, 140], {
  mode: 'runOnceForEachItem',
  jsCode: code('4-finalize-reply.js'),
});
connect(createEvent, finalize);
connect(wantsBooking, finalize, 1);

const sendReply = node('WhatsApp: send reply', 'n8n-nodes-base.httpRequest', 4.2, [3120, 140], {
  method: 'POST',
  url: `=https://graph.facebook.com/{{ ${S('graph_api_version')} }}/{{ $json.phone_number_id }}/messages`,
  authentication: 'genericCredentialType',
  genericAuthType: 'httpHeaderAuth',
  sendBody: true,
  specifyBody: 'json',
  jsonBody: `={{ JSON.stringify(${textMessage('$json.wa_id', '$json.reply')}) }}`,
  options: { timeout: 30000 },
}, { retryOnFail: true, maxTries: 2, waitBetweenTries: 2000, onError: 'continueRegularOutput' });
connect(finalize, sendReply);

const F = (field) => `$('Finalize reply').item.json.${field}`;
const leadColumns = [
  ['phone', `={{ '+' + ${F('wa_id')} }}`],
  ['whatsapp_name', `={{ ${F('profile_name')} }}`],
  ['name', `={{ ${F('lead.name')} }}`],
  ['service_interest', `={{ ${F('lead.service_interest')} }}`],
  ['timeline', `={{ ${F('lead.timeline')} }}`],
  ['budget', `={{ ${F('lead.budget')} }}`],
  ['email', `={{ ${F('lead.email')} }}`],
  ['lead_score', `={{ ${F('lead.score')} }}`],
  ['lead_summary', `={{ ${F('lead.summary')} }}`],
  ['appointment', `={{ ${F('appointment_label')} }}`],
  ['human_requested_at', `={{ ${F('human_requested_at')} }}`],
  ['handoff_reason', `={{ ${F('last_handoff_reason')} }}`],
  ['last_message', `={{ ${F('customer_text')} }}`],
  ['first_contact', `={{ ${F('first_contact')} }}`],
  ['last_contact', `={{ ${F('last_contact')} }}`],
];
const leadRow = node('Prepare lead row', 'n8n-nodes-base.set', 3.4, [3360, 140], {
  assignments: {
    assignments: leadColumns.map(([name, value]) => ({ id: uuid(`lead-${name}`), name, value, type: 'string' })),
  },
  options: {},
});
connect(sendReply, leadRow);

const saveLead = node('Save lead to Google Sheets', 'n8n-nodes-base.googleSheets', 4.5, [3600, 140], {
  operation: 'appendOrUpdate',
  documentId: { __rl: true, mode: 'url', value: `={{ ${S('google_sheet_url')} }}` },
  sheetName: { __rl: true, mode: 'name', value: 'Leads' },
  columns: { mappingMode: 'autoMapInputData', value: {}, matchingColumns: ['phone'], schema: [] },
  options: { cellFormat: 'RAW' },
}, { onError: 'continueRegularOutput' });
connect(leadRow, saveLead);

const notifyOwner = ifNode('Notify the owner?', [3840, 140], [
  notEmpty(`={{ ${F('owner_alert')} }}`),
  notEmpty(`={{ ${S('owner_whatsapp_number')} }}`),
  notStartsWith(`={{ ${S('owner_whatsapp_number')} }}`, 'PASTE'),
]);
connect(saveLead, notifyOwner);

const alertOwner = node('WhatsApp: alert owner', 'n8n-nodes-base.httpRequest', 4.2, [4080, 60], {
  method: 'POST',
  url: `=https://graph.facebook.com/{{ ${S('graph_api_version')} }}/{{ ${F('phone_number_id')} }}/messages`,
  authentication: 'genericCredentialType',
  genericAuthType: 'httpHeaderAuth',
  sendBody: true,
  specifyBody: 'json',
  jsonBody: `={{ JSON.stringify(${textMessage(`String(${S('owner_whatsapp_number')}).replace(/\\D/g, '')`, F('owner_alert'))}) }}`,
  options: { timeout: 30000 },
}, { onError: 'continueRegularOutput' });
connect(notifyOwner, alertOwner, 0);

// Everything after "WhatsApp: mark read + typing…" sits one column further right.
const shifted = new Set([hasText, notText, checkCalendar, build, askClaude, parse, wantsBooking, createEvent,
  finalize, sendReply, leadRow, saveLead, notifyOwner, alertOwner, 'Note: AI brain', 'Note: Actions']);
for (const n of nodes) if (shifted.has(n.name)) n.position = [n.position[0] + 240, n.position[1]];

// ───────────────────────── write the workflow file ─────────────────────────
const workflow = {
  name: 'WhatsApp AI Agent (Claude)',
  nodes,
  connections,
  pinData: {},
  settings: { executionOrder: 'v1', saveManualExecutions: true },
  meta: { templateCredsSetupCompleted: false },
  tags: [],
};

const out = join(here, '..', 'n8n-workflow.json');
writeFileSync(out, JSON.stringify(workflow, null, 2) + '\n');
console.log(`Wrote ${out} (${nodes.length} nodes)`);
