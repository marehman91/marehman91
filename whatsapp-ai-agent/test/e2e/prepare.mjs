// Creates a test copy of the workflow (with fake credentials + filled-in
// settings) and a matching credentials file for `n8n import:*`.
//   node prepare.mjs <outDir>
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = process.argv[2] || join(here, '.tmp');
mkdirSync(outDir, { recursive: true });

const wf = JSON.parse(readFileSync(join(here, '..', '..', 'n8n-workflow.json'), 'utf8'));
wf.id = 'waAgentTest00001';
wf.active = false;

const creds = {
  claude: { id: 'credClaude000001', name: 'Claude API key', type: 'httpHeaderAuth', data: { name: 'x-api-key', value: 'sk-ant-test' } },
  whatsapp: { id: 'credWhatsApp0001', name: 'WhatsApp access token', type: 'httpHeaderAuth', data: { name: 'Authorization', value: 'Bearer EAA-test-token' } },
  gcal: {
    id: 'credGoogleCal001', name: 'Google Calendar account', type: 'googleCalendarOAuth2Api',
    data: { clientId: 'cid', clientSecret: 'csecret', oauthTokenData: { access_token: 'ya29.mock', refresh_token: 'r', token_type: 'Bearer', expires_in: 3599, scope: 'https://www.googleapis.com/auth/calendar' } },
  },
  gsheets: {
    id: 'credGoogleSht001', name: 'Google Sheets account', type: 'googleSheetsOAuth2Api',
    data: { clientId: 'cid', clientSecret: 'csecret', oauthTokenData: { access_token: 'ya29.mock', refresh_token: 'r', token_type: 'Bearer', expires_in: 3599, scope: 'https://www.googleapis.com/auth/spreadsheets' } },
  },
};
const ref = (c) => ({ id: c.id, name: c.name });

for (const node of wf.nodes) {
  if (node.name === 'Ask Claude') node.credentials = { httpHeaderAuth: ref(creds.claude) };
  else if (node.name.startsWith('WhatsApp:')) node.credentials = { httpHeaderAuth: ref(creds.whatsapp) };
  else if (node.type === 'n8n-nodes-base.googleCalendar') node.credentials = { googleCalendarOAuth2Api: ref(creds.gcal) };
  else if (node.type === 'n8n-nodes-base.googleSheets') node.credentials = { googleSheetsOAuth2Api: ref(creds.gsheets) };
}

const overrides = {
  owner_whatsapp_number: '+92 300 9999999',
  google_calendar_id: 'clinic@example.com',
  google_sheet_url: 'https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abcd/edit#gid=0',
  whatsapp_verify_token: 'test-verify-token',
};
const settings = wf.nodes.find((n) => n.name === 'Business Settings');
for (const a of settings.parameters.assignments.assignments) {
  if (a.name in overrides) a.value = overrides[a.name];
}

writeFileSync(join(outDir, 'workflow.json'), JSON.stringify(wf, null, 2));
writeFileSync(join(outDir, 'credentials.json'), JSON.stringify(Object.values(creds), null, 2));
console.log(`Prepared test workflow + credentials in ${outDir}`);
