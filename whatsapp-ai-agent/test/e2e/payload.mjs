// Builds a WhatsApp Cloud API webhook payload (same shape Meta sends).
export function textMessage({ from = '923001234567', name = 'Ali', text, id, phoneNumberId = '109876543210' }) {
  return wrap(phoneNumberId, {
    contacts: [{ profile: { name }, wa_id: from }],
    messages: [{ from, id: id || `wamid.${Math.random().toString(36).slice(2)}`, timestamp: String(Math.floor(Date.now() / 1000)), type: 'text', text: { body: text } }],
  });
}
export function imageMessage({ from = '923001234567', name = 'Ali', phoneNumberId = '109876543210' }) {
  return wrap(phoneNumberId, {
    contacts: [{ profile: { name }, wa_id: from }],
    messages: [{ from, id: `wamid.${Math.random().toString(36).slice(2)}`, timestamp: String(Math.floor(Date.now() / 1000)), type: 'image', image: { id: 'img1', mime_type: 'image/jpeg' } }],
  });
}
export function statusUpdate({ phoneNumberId = '109876543210' } = {}) {
  return wrap(phoneNumberId, {
    statuses: [{ id: 'wamid.out1', status: 'delivered', timestamp: String(Math.floor(Date.now() / 1000)), recipient_id: '923001234567' }],
  });
}
function wrap(phoneNumberId, value) {
  return {
    object: 'whatsapp_business_account',
    entry: [{
      id: 'WABA_ID',
      changes: [{ field: 'messages', value: { messaging_product: 'whatsapp', metadata: { display_phone_number: '15550001111', phone_number_id: phoneNumberId }, ...value } }],
    }],
  };
}
