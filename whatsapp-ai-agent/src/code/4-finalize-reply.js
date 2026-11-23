// ─────────────────────────────────────────────────────────────────────────────
// STEP 4 · Confirm the booking result and save the conversation to memory
// ─────────────────────────────────────────────────────────────────────────────
// Memory lives inside this workflow ("static data"), so no database is needed.
// It is only saved for real (production) executions — not when you click
// "Execute workflow" / "Listen for test event" in the editor.
// You normally don't need to change anything here.

const s = $('Business Settings').first().json;
const p = $('Parse Claude reply').item.json;
const nowIso = DateTime.now().setZone(s.timezone || 'UTC').toISO();
const HISTORY_MESSAGES = 20;
const MAX_CONTACTS = 1000;
const FORGET_AFTER_DAYS = 90;

let reply = p.reply;
let action = p.action;
let handoffReason = p.handoff_reason;
let problem = p.problem;
let newAppointment = null;

if (p.action === 'book_appointment') {
  // We arrive here from "Create calendar event": $json is the new event (or an error).
  if ($json && $json.id && !$json.error) {
    newAppointment = { start: p.event.start, label: p.event.label, service: p.event.service, event_id: $json.id };
  } else {
    reply = s.booking_failed_reply;
    action = 'handoff_to_human';
    problem = 'Calendar booking failed: ' + (($json && ($json.error && ($json.error.message || $json.error))) || 'unknown error');
    handoffReason = problem;
  }
}

// ── Save to memory ──────────────────────────────────────────────────────────
const store = $getWorkflowStaticData('global');
store.contacts = store.contacts || {};
const c = store.contacts[p.wa_id] || { history: [], lead: {}, appointment: null, first_contact: nowIso };
c.history = (c.history || []).concat(
  { role: 'user', text: p.customer_text },
  { role: 'assistant', text: reply },
).slice(-HISTORY_MESSAGES);
c.lead = p.lead;
c.profile_name = p.profile_name;
c.last_contact = nowIso;
if (newAppointment) c.appointment = newAppointment;
if (action === 'handoff_to_human') {
  c.human_requested_at = nowIso;
  c.handoff_reason = handoffReason;
}
store.contacts[p.wa_id] = c;

// Keep memory small: forget quiet contacts and cap the total.
const cutoff = Date.now() - FORGET_AFTER_DAYS * 24 * 60 * 60 * 1000;
const ids = Object.keys(store.contacts);
for (const id of ids) {
  if (new Date(store.contacts[id].last_contact).getTime() < cutoff) delete store.contacts[id];
}
const remaining = Object.keys(store.contacts);
if (remaining.length > MAX_CONTACTS) {
  remaining
    .sort((a, b) => new Date(store.contacts[a].last_contact) - new Date(store.contacts[b].last_contact))
    .slice(0, remaining.length - MAX_CONTACTS)
    .forEach((id) => delete store.contacts[id]);
}

// WhatsApp text messages can be at most 4096 characters.
if (reply.length > 4000) reply = reply.slice(0, 3990) + '…';

// Message for the business owner (sent by "WhatsApp: alert owner").
const who = `${p.lead.name || p.profile_name || 'Customer'} (+${p.wa_id})`;
let ownerAlert = '';
if (action === 'handoff_to_human') {
  ownerAlert = `🔔 *A customer needs a human*\n${who}\nReason: ${handoffReason}\nTheir message: "${String(p.customer_text).slice(0, 300)}"\nOpen chat: https://wa.me/${p.wa_id}`;
} else if (newAppointment) {
  ownerAlert = `📅 *New booking*\n${who}\n${newAppointment.service} — ${newAppointment.label}\nOpen chat: https://wa.me/${p.wa_id}`;
}

return {
  json: {
    wa_id: p.wa_id,
    phone_number_id: p.phone_number_id,
    profile_name: p.profile_name,
    customer_text: p.customer_text,
    reply,
    action,
    handoff_reason: handoffReason,
    problem,
    lead: p.lead,
    appointment_label: (newAppointment || c.appointment || {}).label || '',
    new_booking: Boolean(newAppointment),
    first_contact: c.first_contact,
    last_contact: nowIso,
    human_requested_at: c.human_requested_at || '',
    last_handoff_reason: c.handoff_reason || '',
    owner_alert: ownerAlert,
  },
};
