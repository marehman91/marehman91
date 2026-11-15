# Minibells Website: Setup Guide

Ye bachon ke kapron ki Urdu website hai. Customer kapra aur size chunta hai, apna naam aur pata likhta hai, aur button dabate hi **WhatsApp pe poora order likha hua** aa jata hai. Payment advance mein hoti hai, aur account details website khud dikha deti hai.

Is ki koi monthly fees nahi hai: hosting free hai, aur products Google Sheet se chalte hain.

---

## Folder mein kya hai

| File | Kaam |
|---|---|
| `index.html` | Website khud. **Isay mat chherein.** |
| `config.js` | WhatsApp number, delivery charges, accounts. **Sirf yehi file badalni hai.** |
| `products-template.csv` | Products ki Google Sheet ka namoona |
| `images/` | Logo, aur aap ki tasveerein (agar Sheet ki jagah yahan rakhni hon) |

---

## Step 1: `config.js` bharein (10 minute)

Laptop pe `config.js` ko **Notepad** mein kholein (right click → Open with → Notepad). Har line ke upar likha hai ke kya likhna hai.

| Setting | Kya likhein | Misaal |
|---|---|---|
| `whatsappNumber` | Business WhatsApp number, 92 se shuru, bina 0 aur + ke | `"923001234567"` |
| `phoneDisplay` | Wohi number jaise log parhte hain | `"0300-1234567"` |
| `deliveryCharge` | Delivery charges (sirf number) | `250` |
| `deliveryDays` | Payment ke baad kitne din mein parcel pohanchta hai | `"3 سے 5 دن"` |
| `tiktokUrl` | TikTok profile ka link | `"https://www.tiktok.com/@minibells"` |
| `payments` | Bank / JazzCash / Easypaisa ki details | `title` wohi likhein jo account pe naam hai |
| `exchangePolicy` | Apni exchange policy (din, kharcha kaun dega) | |
| `sizeChart` | **Apne asli naap** (inches) | |
| `demo` | Sab bhar kar `false` kar dein | `demo: false,` |

Dhyan rakhein:
- Quotes `" "` aur line ke aakhir ka comma `,` mat mitayein.
- Jo account nahi hai (jaise Easypaisa), us ka poora `{ ... },` hissa mita dein.
- Save karne ke baad `index.html` ko double click kar ke browser mein check kar lein.

---

## Step 2: Products ki Google Sheet (phone se chalegi)

Ye kaam aap ki wife phone ki **Google Sheets** app se rozana kar sakti hain.

### 2a. Sheet banayein (sirf ek dafa)
1. Laptop pe [sheets.google.com](https://sheets.google.com) kholein → **Blank** sheet.
2. **File → Import → Upload** → `products-template.csv` chunein → **Replace current sheet** → Import.
3. Sheet ka naam rakh dein, jaise "Minibells Products".

### 2b. Columns ka matlab

| Column | Kya likhein |
|---|---|
| کوڈ | Article code, jaise `MB-101` (video mein bhi yehi code dikhayein) |
| نام | Kapre ka naam |
| قیمت | Price (sirf number) |
| پرانی قیمت | Sale ho to purani price, warna khaali |
| موجود سائز | Jo sizes stock mein hain, comma se alag: `1-2 سال, 2-3 سال` |
| ختم سائز | Jo sizes khatam ho gaye (website pe "ختم" likha nazar aaye ga) |
| کیٹیگری | `لڑکی` ya `لڑکا` ya `دونوں` |
| تصویر | Photo ka link (neeche tareeqa hai). Zyada photos hon to comma laga kar |
| تفصیل | Kapre ki 1-2 line tafseel |
| ٹیگ | Chhota label, jaise `نیا` ya `سیل` (khaali bhi chal jaye ga) |
| دکھائیں | `ہاں` ya `نہیں`. Jo design website se hatana ho us mein `نہیں` likh dein |

> ⚠️ **Size ke saath hamesha `سال` ya `ماہ` likhein.** Sirf `2-3` likhne se Google Sheet usay tareekh (date) bana deta hai.

### 2c. Photo ka link kaise lein
1. Phone pe **Google Drive** app → **+** → Upload → photo.
2. Photo ke saath teen dots **⋮** → **Share** → **Manage access** → General access: **Anyone with the link** (Viewer).
3. **Copy link** dabayein aur Sheet ke `تصویر` column mein paste kar dein. Website link ko khud theek kar leti hai.

Tip: Photo seedhi (portrait) aur roshni mein lein. Sab photos ek jaisi background pe hon to website bohat professional lagti hai.

### 2d. Sheet ko website se jorein (sirf ek dafa)
1. Sheet mein **File → Share → Publish to web**.
2. Pehle dropdown mein apni sheet (Sheet1), doosre mein **Comma-separated values (.csv)** → **Publish** → OK.
3. Jo link mile use copy kar ke `config.js` mein paste karein:
   ```js
   productsSheetUrl: "https://docs.google.com/spreadsheets/d/e/....../pub?gid=0&single=true&output=csv",
   ```
4. Ab Sheet mein jo badlenge wo **takreeban 5 minute** mein website pe aa jaye ga. Dobara upload ki zaroorat nahi.

---

## Step 3: Website online karein (free, Netlify)

1. [netlify.com](https://www.netlify.com) pe **Sign up** (Google account se).
2. **Add new project** (ya "Add new site") → **Deploy manually**.
3. Poora `minibells-website` folder us box mein **drag** kar dein. 1 minute mein link mil jaye ga.
4. **Project configuration** (ya "Site configuration") → **Change name** → `minibells` likhein. Agar available hua to link ban jaye ga: `minibells.netlify.app`.
5. Jab bhi `config.js` badlein: **Deploys** tab → folder dobara drag karein. (Products ke liye ye zaroori nahi, wo Sheet se aate hain.)

**Apna domain (optional):** `minibells.pk` ya `.com` kharid kar Netlify mein **Domain management → Add domain** se jor sakte hain. Is se bharosa aur barhta hai.

---

## Step 4: Link customers tak pohanchayein

- **TikTok bio** mein website ka link lagayein.
- **Video caption:** "آرڈر کے لیے بایو میں لنک" ya "Order ke liye bio mein link".
- **WhatsApp Business → Business tools → Profile → Website** mein link.
- **Greeting message** mein link: "تمام کپڑے، سائز اور قیمتیں: minibells.netlify.app"

---

## Online karne ke baad ye zaroor check karein

- [ ] Apne phone se ek test order bhejein: WhatsApp **sahi number** pe khulta hai?
- [ ] **TikTok app ke andar** bio link se website kholein aur order button dabayein (TikTok ka apna browser hota hai).
- [ ] Account number ka "کاپی" button chal raha hai?
- [ ] Ooper "نمونہ ویب سائٹ" wali patti chali gayi? (`demo: false`)

---

## Rozana ka kaam (sirf Google Sheet mein)

| Kya hua | Sheet mein kya karein |
|---|---|
| Koi size bik gaya | Us size ko `موجود سائز` se kaat kar `ختم سائز` mein likh dein |
| Naya kapra aaya | Neeche nayi row bana dein |
| Restock hua | Size wapas `موجود سائز` mein likh dein |
| Design band karna hai | `دکھائیں` mein `نہیں` |
| Sale lagani hai | `پرانی قیمت` mein purani, `قیمت` mein nayi price |

## WhatsApp pe order kaisa aata hai

```
*نیا آرڈر — Minibells* 🎀
آرڈر نمبر: MB-1511-482
━━━━━━━━━━
1۔ گلابی فلورل فراک
   کوڈ: MB-101 | سائز: 3-4 سال | تعداد: 2
   قیمت: 3,700 روپے
━━━━━━━━━━
کپڑے: 3,700 روپے
ڈیلیوری: 250 روپے
*کل رقم: 3,950 روپے*

*ڈیلیوری کی تفصیل*
نام: ...
موبائل: 03001234567
شہر: لاہور
پتہ: ...
```

Wife ka kaam: payment ka screenshot check karein → `Payment Pending` label hata kar `Confirmed` lagayein → parcel bhejein → tracking number bhej dein.

---

## Customer reviews lagana (bharosa barhane ke liye)

1. Customers ke achhe WhatsApp messages ke screenshots lein. Customer ka naam aur number chhupa dein, aur un se ijazat le lein.
2. `images` folder mein `review1.jpg`, `review2.jpg` naam se rakhein.
3. `config.js` mein: `reviews: ["images/review1.jpg", "images/review2.jpg"],`
4. Folder Netlify pe dobara drag karein.
