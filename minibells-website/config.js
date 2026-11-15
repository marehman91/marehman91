/* =====================================================================
   MINIBELLS WEBSITE SETTINGS  —  ویب سائٹ کی سیٹنگز
   ---------------------------------------------------------------------
   Sirf yehi file badalni hai. Har line ke upar likha hai ke kya likhna hai.
   Quotes " " ke andar likhein, aur har line ke aakhir mein comma , rehne dein.
   ===================================================================== */

window.MINIBELLS = {

  // Sab details bharne ke baad isay false kar dein.
  // true rahe ga to website ke upar "نمونہ" (sample) ki patti nazar aaye gi.
  demo: true,

  // ---------- WhatsApp ----------
  // Number 92 se shuru karein, shuru ka 0 aur + na lagayein. Misaal: 03001234567 => "923001234567"
  whatsappNumber: "923000000000",
  // Website pe dikhane ke liye number (jaise customer parhta hai)
  phoneDisplay: "0300-0000000",

  // ---------- Delivery ----------
  deliveryCharge: 250,                 // poore Pakistan ke delivery charges (sirf number)
  deliveryNote: "",                    // agar kuch aur batana ho, jaise: "دور دراز علاقوں کے لیے 300 روپے"
  deliveryDays: "3 سے 5 دن",           // payment ke baad parcel kitne din mein pohanchta hai

  // ---------- Links ----------
  tiktokUrl: "https://www.tiktok.com/@minibells",
  instagramUrl: "",
  facebookUrl: "",

  // ---------- Products (Google Sheet) ----------
  // Google Sheet ka "Publish to web" (CSV) link yahan paste karein. Tareeqa README mein hai.
  // Khaali rahe to neeche "products" wali list use hogi.
  productsSheetUrl: "",

  // ---------- Payment accounts ----------
  // Jo account nahi hai uska poora { ... } hissa mita dein.
  payments: [
    { label: "بینک اکاؤنٹ", provider: "Meezan Bank", title: "Minibells", number: "0000 0000000000", iban: "" },
    { label: "جاز کیش",     provider: "JazzCash",    title: "Minibells", number: "0300 0000000" },
    { label: "ایزی پیسہ",   provider: "Easypaisa",   title: "Minibells", number: "0300 0000000" }
  ],

  // ---------- Brand ki baatein ----------
  tagline: "ایک ماں کا شروع کیا ہوا برانڈ۔ ہر کپڑا خود چن کر اور محبت سے پیک کر کے آپ تک پہنچاتے ہیں۔",
  about: "منی بیلز ایک ماں نے اپنے گھر سے شروع کیا ہے۔ ہم وہی کپڑے بیچتے ہیں جو ہم اپنے بچوں کو پہنانا پسند کریں: نرم، آرام دہ اور خوبصورت۔ ہر آرڈر ہم خود چیک کر کے پیک کرتے ہیں اور روزانہ کی پیکنگ ٹک ٹاک پر دکھاتے ہیں۔",

  // ---------- Size exchange policy (apni policy ke mutabiq badlein) ----------
  exchangePolicy: [
    "سائز پورا نہ آئے تو پارسل ملنے کے 3 دن کے اندر واٹس ایپ پر بتائیں۔",
    "ایکسچینج اسٹاک میں سائز موجود ہونے پر ہوگا۔",
    "کپڑا استعمال یا دھلا ہوا نہ ہو اور ٹیگ لگا ہو۔",
    "ایکسچینج کی ڈیلیوری کا خرچ کسٹمر کے ذمے ہوگا۔"
  ],

  // ---------- Size chart (apne asli naap likhein, inches mein) ----------
  sizeChartNote: "ناپ انچ میں ہیں۔ پھر بھی سمجھ نہ آئے تو بچے کی عمر اور قد واٹس ایپ پر بتائیں، ہم صحیح سائز بتا دیں گے۔",
  sizeChart: [
    { size: "0-6 ماہ",  length: "14", chest: "18" },
    { size: "6-12 ماہ", length: "16", chest: "19" },
    { size: "1-2 سال",  length: "18", chest: "20" },
    { size: "2-3 سال",  length: "20", chest: "21" },
    { size: "3-4 سال",  length: "22", chest: "22" },
    { size: "4-5 سال",  length: "24", chest: "23" },
    { size: "5-6 سال",  length: "26", chest: "24" }
  ],

  // ---------- Customer reviews ----------
  // Customers ke WhatsApp reviews ke screenshots "images" folder mein daal kar unke naam yahan likhein.
  // Misaal: reviews: ["images/review1.jpg", "images/review2.jpg"],
  // Khaali rahe to reviews wala hissa nazar nahi aaye ga.
  reviews: [],

  // ---------- Products (agar Google Sheet use nahi kar rahe) ----------
  // Ye sirf NAMOONA (sample) hai. Google Sheet lagane ke baad ye list istemal nahi hogi.
  // category: "لڑکی" ya "لڑکا" ya "دونوں"
  // images: ["images/mb101.jpg"]  (khaali chhorein to rangeen tasveer khud ban jaye gi)
  products: [
    { code: "MB-101", name: "گلابی فلورل فراک", price: 1850, oldPrice: 2200, sizes: ["1-2 سال", "2-3 سال", "3-4 سال"], soldOut: ["4-5 سال"], category: "لڑکی", tag: "نیا", images: [], description: "نرم کاٹن کپڑا، گرمیوں کے لیے بہترین۔ ہلکے پھولوں کا پرنٹ اور پیچھے بٹن۔" },
    { code: "MB-102", name: "آسمانی کاٹن کرتا شلوار", price: 1650, sizes: ["2-3 سال", "3-4 سال", "5-6 سال"], soldOut: ["1-2 سال"], category: "لڑکا", images: [], description: "سادہ اور آرام دہ کاٹن کا کرتا شلوار۔ عید اور روزمرہ دونوں کے لیے۔" },
    { code: "MB-103", name: "سنہری لیس پارٹی فراک", price: 2450, sizes: ["2-3 سال", "3-4 سال", "4-5 سال"], category: "لڑکی", tag: "پارٹی", images: [], description: "شادی اور سالگرہ کے لیے خوبصورت لیس والا فراک۔ اندر نرم استر۔" },
    { code: "MB-104", name: "فیروزی بے بی رومپر", price: 1250, sizes: ["0-6 ماہ", "6-12 ماہ"], soldOut: ["1-2 سال"], category: "دونوں", images: [], description: "چھوٹے بچوں کے لیے نرم رومپر۔ نیچے بٹن، کپڑے بدلنا آسان۔" },
    { code: "MB-105", name: "لیمن کلر لان فراک", price: 1450, sizes: ["1-2 سال", "2-3 سال", "3-4 سال", "4-5 سال"], category: "لڑکی", images: [], description: "ہلکی پھلکی لان، گرمی میں ٹھنڈک کا احساس۔" },
    { code: "MB-106", name: "گرے ٹریک سوٹ", price: 1750, sizes: ["3-4 سال", "4-5 سال", "5-6 سال"], category: "لڑکا", tag: "نیا", images: [], description: "نرم فلیس کا ٹریک سوٹ، سردیوں کے لیے گرم اور آرام دہ۔" },
    { code: "MB-107", name: "سفید و گلابی نائٹ سوٹ", price: 1350, sizes: ["1-2 سال", "2-3 سال"], soldOut: ["3-4 سال"], category: "دونوں", images: [], description: "رات کو سونے کے لیے نرم کاٹن نائٹ سوٹ۔" },
    { code: "MB-108", name: "نیوی شرٹ اور نیکر سیٹ", price: 1550, sizes: [], soldOut: ["2-3 سال", "3-4 سال"], category: "لڑکا", images: [], description: "کالر والی شرٹ اور نیکر کا سیٹ۔" }
  ]
};
