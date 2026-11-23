// ─────────────────────────────────────────────────────────────────────────────
// STEP 3 · Read Claude's answer and double-check it before acting on it
// ─────────────────────────────────────────────────────────────────────────────
// • If Claude could not be reached (or declined), the customer gets your
//   "fallback_reply" and the conversation is flagged for a human.
// • If Claude wants to book a time that isn't actually free, we don't book it.
// You normally don't need to change anything here.

const s = $('Business Settings').first().json;
const msg = $('Extract message').item.json;
const ctx = $('Build Claude request').item.json;
const res = $json; // raw response from the Claude API

let result = null;
let problem = '';

if (res.error) {
  const e = res.error;
  problem = 'Claude API error: ' + (typeof e === 'string' ? e : (e.message || JSON.stringify(e))).slice(0, 300);
} else if (res.stop_reason === 'refusal') {
  problem = 'Claude declined to answer this message';
} else if (res.stop_reason === 'max_tokens') {
  problem = 'Claude reply was cut off (max_tokens)';
} else {
  const text = (res.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
  try {
    result = JSON.parse(text);
    if (typeof result.reply !== 'string' || !result.reply.trim()) throw new Error('empty reply');
  } catch (err) {
    result = null;
    problem = 'Could not read Claude reply: ' + err.message;
  }
}

if (!result) {
  result = {
    reply: s.fallback_reply,
    lead: ctx.known_lead,
    action: 'handoff_to_human',
    slot_id: '',
    handoff_reason: problem,
  };
}

// Merge lead details: keep what we knew unless Claude learned something new.
const lead = Object.assign({}, ctx.known_lead);
for (const [key, value] of Object.entries(result.lead || {})) {
  if (typeof value === 'string' && value.trim()) lead[key] = value.trim();
}

// Safety check for bookings: the slot must be one we offered as free.
let event = null;
if (result.action === 'book_appointment') {
  const slot = String(result.slot_id || '').trim();
  if (!ctx.valid_slots.includes(slot)) {
    result.action = 'none';
    const alternatives = ctx.valid_slots.slice(0, 3).map((v) =>
      DateTime.fromFormat(v, "yyyy-MM-dd'T'HH:mm", { zone: s.timezone }).setLocale('en-US').toFormat("ccc d LLL, h:mm a"));
    result.reply = s.slot_unavailable_reply + (alternatives.length ? `\n• ${alternatives.join('\n• ')}` : '');
    problem = `Claude tried to book an unavailable slot: "${slot}"`;
  } else {
    const start = DateTime.fromFormat(slot, "yyyy-MM-dd'T'HH:mm", { zone: s.timezone }).setLocale('en-US');
    const end = start.plus({ minutes: Number(s.appointment_length_minutes) || 30 });
    const name = lead.name || msg.profile_name || 'WhatsApp customer';
    const service = lead.service_interest || 'Appointment';
    event = {
      start: start.toISO(),
      end: end.toISO(),
      label: start.toFormat("cccc d LLLL 'at' h:mm a"),
      service,
      summary: `${service} – ${name}`,
      description: [
        `Booked by the WhatsApp AI assistant.`,
        `Customer: ${name}`,
        `WhatsApp: +${msg.wa_id}  (chat: https://wa.me/${msg.wa_id})`,
        lead.email ? `Email: ${lead.email}` : '',
        lead.summary ? `Notes: ${lead.summary}` : '',
      ].filter(Boolean).join('\n'),
    };
  }
}

return {
  json: {
    wa_id: msg.wa_id,
    profile_name: msg.profile_name,
    phone_number_id: msg.phone_number_id,
    customer_text: msg.text,
    reply: String(result.reply).trim(),
    action: result.action,
    handoff_reason: result.action === 'handoff_to_human' ? (result.handoff_reason || problem || 'Needs a human') : '',
    lead,
    event,
    problem,
    model_used: res.model || '',
  },
};
