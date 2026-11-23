// ─────────────────────────────────────────────────────────────────────────────
// STEP 1 · Read the WhatsApp webhook and pull out the customer's message
// ─────────────────────────────────────────────────────────────────────────────
// WhatsApp sends many kinds of events to this webhook. We only care about
// messages that customers send to us. "Delivered" / "read" receipts are ignored.
// If one webhook carries several messages from the same person, we merge them
// into one message so the AI answers once.
// You normally don't need to change anything here.

const settings = $('Business Settings').first().json;
const expectedPhoneId = String(settings.whatsapp_phone_number_id || '').trim();
const body = $('WhatsApp webhook (POST)').first().json.body || {};

// Remember message IDs we've already handled, so a duplicate delivery from
// WhatsApp doesn't get two answers.
const store = $getWorkflowStaticData('global');
store.seenMessageIds = store.seenMessageIds || {};
const now = Date.now();
const THREE_DAYS = 3 * 24 * 60 * 60 * 1000;
for (const [id, seenAt] of Object.entries(store.seenMessageIds)) {
  if (now - seenAt > THREE_DAYS) delete store.seenMessageIds[id];
}

const byCustomer = {};

if (body.object === 'whatsapp_business_account') {
  for (const entry of body.entry || []) {
    for (const change of entry.changes || []) {
      if (change.field !== 'messages') continue;
      const value = change.value || {};
      const phoneId = String((value.metadata && value.metadata.phone_number_id) || '');

      // If you filled in your Phone Number ID, ignore traffic for other numbers.
      if (expectedPhoneId && phoneId && phoneId !== expectedPhoneId) continue;

      const names = {};
      for (const c of value.contacts || []) names[c.wa_id] = (c.profile && c.profile.name) || '';

      for (const m of value.messages || []) {
        if (!m.id || !m.from || store.seenMessageIds[m.id]) continue;
        store.seenMessageIds[m.id] = now;

        let text = '';
        if (m.type === 'text') text = (m.text && m.text.body) || '';
        else if (m.type === 'interactive') {
          const i = m.interactive || {};
          text = (i.button_reply && i.button_reply.title) || (i.list_reply && i.list_reply.title) || '';
        } else if (m.type === 'button') text = (m.button && m.button.text) || '';

        const c = byCustomer[m.from] || (byCustomer[m.from] = {
          wa_id: m.from,
          profile_name: names[m.from] || '',
          phone_number_id: phoneId || expectedPhoneId,
          texts: [],
          types: [],
          ids: [],
        });
        if (text.trim()) c.texts.push(text.trim());
        c.types.push(m.type);
        c.ids.push(m.id);
      }
    }
  }
}

// Returning no items stops the workflow here (e.g. for read receipts).
return Object.values(byCustomer).map((c) => ({
  json: {
    wa_id: c.wa_id,
    profile_name: c.profile_name,
    phone_number_id: c.phone_number_id,
    text: c.texts.join('\n'),
    has_text: c.texts.length > 0,
    message_types: c.types.join(','),
    last_message_id: c.ids[c.ids.length - 1],
  },
  pairedItem: { item: 0 },
}));
