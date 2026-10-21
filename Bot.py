# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║     Kairozen All-in-One Bot v4.1 — カイロゼン                ║
║     ហាងរឿង (Movies Shop) + SMM Panel · ដាក់លុយ KHQR          ║
║     Global Discount · Panel Admin                         ║
║     Compatible: Python 3.10+ · Termux / Pydroid 3         ║
╚══════════════════════════════════════════════════════════════╝
ដំឡើង:
  pip install pyTelegramBotAPI requests flask qrcode pillow --break-system-packages
"""

import json, logging, time, re, threading, hashlib, io, os, sys, subprocess, datetime
import requests as http_req
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from flask import Flask, request as flask_request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── COLOR CONSTANTS FOR TERMINAL ───
CLR_RESET   = "\033[0m"
CLR_BOLD    = "\033[1m"
CLR_RED     = "\033[91m"
CLR_GREEN   = "\033[92m"
CLR_YELLOW  = "\033[93m"
CLR_BLUE    = "\033[94m"
CLR_MAGENTA = "\033[95m"
CLR_CYAN    = "\033[96m"
CLR_WHITE   = "\033[97m"

BG_RED      = "\033[41m"
BG_GREEN    = "\033[42m"
BG_BLUE     = "\033[44m"

# Custom Colored Formatter for Logging
class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BLUE}%(levelname)s{CLR_RESET}] %(message)s",
        logging.INFO:     f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_GREEN}%(levelname)s{CLR_RESET}] %(message)s",
        logging.WARNING:  f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_YELLOW}%(levelname)s{CLR_RESET}] %(message)s",
        logging.ERROR:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s",
        logging.CRITICAL: f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BOLD}{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# Setup Logging with Colors
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# ─── Auto-install deps ───
def _ensure_deps():
    pkgs = {"PIL": "pillow", "qrcode": "qrcode"}
    for mod, pkg in pkgs.items():
        try: __import__(mod)
        except ImportError:
            logger.info(f"{CLR_YELLOW}Installing missing package: {pkg}...{CLR_RESET}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=False)
_ensure_deps()

import qrcode
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════
#  CONFIG  — ដូរតម្លៃទាំងនេះ
# ═══════════════════════════════════════════════════════════
BOT_TOKEN          = "8635907476:AAEMUF65TTPCPwgVo0IGLKmUKO1RMZb2b1s"
ADMIN_ID           = 8807182741

# Bakong KHQR (ដាក់ Token ពេញលេញពីអ៊ីមែលរបស់អ្នក)
BAKONG_TOKEN       = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXJjb2pMZm1lYzJNY1GQ2NDAyYiJvJiJvj9kuSWJXi03NDQzNDQzNTIzNzFNaHptNGxDbTYiLCJpc3MiOiJCYWtvbmcifQ.eyJhaGNvdW50X2lkIjoibW9uX3NhbW5hbmdAYmtydCIsImRhdGVfaXNzdWVkIjoiMTc2MzgyOTc1MCIsImV4cGlyZXNfYXQiOjE4MjkyMzg5NTB9"
BANK_ACCOUNT       = "mon_samnang@bkrt"
MERCHANT_NAME      = "SmeyLov"
MERCHANT_CITY      = "Phnom Penh"

DEPOSIT_EXPIRE_SEC = 300   # 5 នាទី
POLL_INTERVAL      = 5
STOCK_ALERT_MIN    = 5

# ═══════════════════════════════════════════════════════════
#  FILES
# ═══════════════════════════════════════════════════════════
WALLETS_FILE    = "aio_wallets.json"
USERS_FILE      = "aio_users.json"
LANG_FILE       = "aio_lang.json"
PROMO_FILE      = "aio_promos.json"
SETTINGS_FILE   = "aio_settings.json"
DISCOUNT_FILE   = "aio_discount.json"   # Global Discount File

PRODUCTS_FILE   = "aio_products.json"
ORDERS_FILE     = "aio_orders.json"
STOCK_FILE      = "aio_stock.json"
STORE_DEP_FILE  = "aio_store_deposits.json"
SEEN_TXN_FILE   = "aio_seen_txn.json"

SMM_API_FILE    = "aio_smm_api.json"
SMM_SVC_FILE    = "aio_smm_services.json"
SMM_ORD_FILE    = "aio_smm_orders.json"
SMM_PROFIT_FILE = "aio_smm_profit.json"
SMM_POLL_FILE   = "aio_smm_poll.json"
LIVECHAT_FILE   = "aio_livechat.json"     # Live Chat Mapping File

def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"{CLR_RED}Save {path}: {e}{CLR_RESET}")

# ─── Load all state ───
wallets         = _load(WALLETS_FILE,   {})
users_db        = _load(USERS_FILE,     {})
user_lang       = _load(LANG_FILE,      {})
promos          = _load(PROMO_FILE,     {})
settings        = _load(SETTINGS_FILE,  {})
discount_config = _load(DISCOUNT_FILE,  {"active": False, "pct": 0})

products        = _load(PRODUCTS_FILE,  [])
orders          = _load(ORDERS_FILE,    {})
stock           = _load(STOCK_FILE,     {})
store_deps      = _load(STORE_DEP_FILE, {})
seen_txn        = set(_load(SEEN_TXN_FILE, []))
livechat_sessions = _load(LIVECHAT_FILE, {}) # admin_msg_id -> user_uid

smm_api         = _load(SMM_API_FILE,   {"url": "", "key": ""})
smm_services    = _load(SMM_SVC_FILE,   {})
smm_orders      = _load(SMM_ORD_FILE,   {})
smm_profit      = _load(SMM_PROFIT_FILE,{"pct": 20})
smm_poll        = _load(SMM_POLL_FILE,  {"interval": POLL_INTERVAL})

waiting         = {}   # uid -> step/dict
lang_cooldown   = {}
livechat_users  = set() # uid set of users currently in live chat mode

# ═══════════════════════════════════════════════════════════
#  MOVIES CONFIG (តម្លៃរឿង $1.00 ក្នុងមួយរឿង)
# ═══════════════════════════════════════════════════════════
MOVIES = [
    {
        "id": "movie1",
        "title": "រឿងទី ១៖ អាថ៌កំបាំងព្រៃជ្រៅ",
        "photo": "https://raw.githubusercontent.com/mylove-Khmer/SmeyLov008bot/main/movie1.jpg",
        "desc": "នេះជារឿងដ៏ល្បីល្បាញ និងរំភើប...",
        "price": 1.00,
        "video_link": "https://t.me/c/xxxx/xxxx"
    },
    {
        "id": "movie2",
        "title": "រឿងទី ២៖ ស្នេហ៍ក្រោមពន្លឺខែ",
        "photo": "https://raw.githubusercontent.com/mylove-Khmer/SmeyLov008bot/main/movie2.jpg",
        "desc": "រឿងស្នេហាអន្លង់អន្លោច...",
        "price": 1.00,
        "video_link": "https://t.me/c/xxxx/xxxx"
    },
    {
        "id": "movie3",
        "title": "រឿងទី ៣៖ វីរបុរសរងគ្រោះ",
        "photo": "https://raw.githubusercontent.com/mylove-Khmer/SmeyLov008bot/main/movie3.jpg",
        "desc": "សាច់រឿងអស្ចារ្យ និងឈុតឆាកប្រយុទ្ធដ៏ជក់ចិត្ត...",
        "price": 1.00,
        "video_link": "https://t.me/c/xxxx/xxxx"
    }
]

def movies_kb():
    btns = []
    for m in MOVIES:
        btns.append([InlineKeyboardButton(f"🎬 {m['title']} — ${m['price']:.2f}", callback_data=f"show_movie:{m['id']}")])
    btns.append([InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

# ═══════════════════════════════════════════════════════════
#  BOT + HTTP
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

def _make_session():
    s = http_req.Session()
    r = Retry(total=3, backoff_factor=2, status_forcelist=[500,502,503,504])
    a = HTTPAdapter(max_retries=r)
    s.mount("http://", a); s.mount("https://", a)
    return s
http = _make_session()

# ═══════════════════════════════════════════════════════════
#  LANGUAGE
# ═══════════════════════════════════════════════════════════
STRINGS = {
    "kh": {
        "welcome": (
            "👋 សួស្ដី {name}!\n\n"
            "សូមស្វាគមន៍មកកាន់ <b>Smey Lov</b> 🤖\n\n"
            "👇 សូមជ្រើសរើសភាសាខាងក្រោម៖"
        ),
        "select_lang":   "🌐 ជ្រើសរើសភាសា / Select Language:",
        "lang_set":      "✅ ភាសាត្រូវបានប្ដូរទៅជា ខ្មែរ។",
        "menu":          "🏠 ត្រឡប់ Menu ដើម",
        "banned":        "🚫 គណនីរបស់អ្នកត្រូវបាន ban!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ គ្មាន SMM Service ទេ",
        "choose_platform": "ជ្រើស Platform:",
        "choose_qty":    "ជ្រើស ចំនួន:",
        "send_link":     "ផ្ញើ Link របស់អ្នក:",
        "low_balance":   "❌ លុយមិនគ្រប់!",
        "order_done":    "✅ បញ្ជាទិញបានជោគជ័យ!",
        "deposit_ok":    "✅ ដាក់លុយបានជោគជ័យ!",
        "qr_expired":    "⏰ QR ផុតកំណត់! សូម top up ម្ដងទៀត",
        "qr_error":      "⚠️ QR Generate Error! ទាក់ទង Admin",
        "order_notfound":"❌ Order រកមិនឃើញ!",
        "no_orders":     "❌ គ្មាន Order ទេ!",
        "how_to_use": (
            "💡 <b>របៀបប្រើប្រាស់</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ ចុច <b>💳 ដាក់ប្រាក់</b> → ជ្រើស ចំនួន → ស្កេន QR តាម Bakong"
        ),
        "support_msg": (
            "💬 <b>ជំនួយ & ទំនាក់ទំនង Support</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💬 អ្នកអាចចុចប៊ូតុងខាងក្រោមដើម្បីឆាតផ្ទាល់ជាមួយ Admin៖\n"
            "👤 <b>Admin Telegram:</b> @SmeyLov008"
        ),
        "fallback": "❓ ប្រើ Menu ខាងក្រោម",
    },
    "en": {
        "welcome": (
            "👋 Welcome {name}!\n\n"
            "Welcome to <b>Smey Lov</b> 🤖\n\n"
            "👇 Please select your preferred language below:"
        ),
        "select_lang":   "🌐 Select Language:",
        "lang_set":      "✅ Language changed to English.",
        "menu":          "🏠 Back to Menu",
        "banned":        "🚫 Your account has been banned!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ No SMM Services available",
        "choose_platform": "Choose Platform:",
        "choose_qty":    "Choose Quantity:",
        "send_link":     "Send your Link:",
        "low_balance":   "❌ Insufficient balance!",
        "order_done":    "✅ Order placed successfully!",
        "deposit_ok":    "✅ Deposit successful!",
        "qr_expired":    "⏰ QR expired! Please top up again",
        "qr_error":      "⚠️ QR Generate Error! Contact Admin",
        "order_notfound":"❌ Order not found!",
        "no_orders":     "❌ No orders yet!",
        "how_to_use": (
            "💡 <b>How to Use</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Tap <b>💳 Top Up</b> → Choose Amount → Scan Bakong QR"
        ),
        "support_msg": (
            "💬 <b>Support & Contact</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💬 You can click the button below to chat with admin directly:\n"
            "👤 <b>Admin Telegram:</b> @SmeyLov008"
        ),
        "fallback": "❓ Use the menu below",
    },
}

def get_lang(uid): return user_lang.get(str(uid), "kh")

def t(uid, key, *args):
    lang = get_lang(uid)
    s = STRINGS.get(lang, STRINGS["kh"]).get(key) or STRINGS["kh"].get(key, key)
    
    if "{name}" in s and not args:
        user_name = users_db.get(str(uid), {}).get("name", "User")
        args = (user_name,)

    if args:
        try: 
            return s.format(*args)
        except: 
            return s
    return s

def toggle_lang(uid):
    uid_str = str(uid)
    now = time.time()
    if now - lang_cooldown.get(uid_str, 0) < 3.0: return
    lang_cooldown[uid_str] = now
    cycle = {"kh": "en", "en": "kh"}
    user_lang[uid_str] = cycle.get(get_lang(uid), "kh")
    _save(LANG_FILE, user_lang)

def lang_flag(uid):
    return {"kh": "🇰🇭 ខ្មែរ", "en": "🇬🇧 English"}.get(get_lang(uid), "🇰🇭")

# ═══════════════════════════════════════════════════════════
#  WALLET & DISCOUNT HELPERS
# ═══════════════════════════════════════════════════════════
def bal(uid): return float(wallets.get(str(uid), 0))
def add_bal(uid, amt):
    wallets[str(uid)] = round(bal(uid) + amt, 2)
    _save(WALLETS_FILE, wallets)
def ded_bal(uid, amt):
    wallets[str(uid)] = max(0, round(bal(uid) - amt, 2))
    _save(WALLETS_FILE, wallets)
def set_bal(uid, amt):
    wallets[str(uid)] = round(float(amt), 2)
    _save(WALLETS_FILE, wallets)

def _calc_discounted_price(price):
    if discount_config.get("active", False):
        pct = float(discount_config.get("pct", 0))
        return round(price * (1 - pct / 100), 2)
    return price

# ═══════════════════════════════════════════════════════════
#  PROMO CODE
# ═══════════════════════════════════════════════════════════
def apply_promo(uid, code, amount):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return amount, 0, "❌ Promo Code ខុស!"
    if p.get("uses", 0) > 0 and p.get("used", 0) >= p["uses"]:
        return amount, 0, "❌ Promo Code ផុតសិទ្ធិហើយ!"
    user_used = p.get("user_used", {})
    if str(uid) in user_used:
        return amount, 0, "❌ អ្នកបានប្រើ Promo Code នេះហើយ!"
    if p.get("pct", False):
        discount = round(amount * float(p["discount"]) / 100, 2)
    else:
        discount = min(float(p["discount"]), amount)
    final = max(0, round(amount - discount, 2))
    return final, discount, None

def confirm_promo(code, uid):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return
    p["used"] = p.get("used", 0) + 1
    uu = p.get("user_used", {})
    uu[str(uid)] = 1
    p["user_used"] = uu
    _save(PROMO_FILE, promos)

# ═══════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════
def main_kb(uid=None):
    lang = get_lang(uid) if uid else "kh"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("💳 Top Up",        "👜 Wallet")
        kb.row("🎬 Movies",        "💬 Support")
        kb.row("💡 How to Use",    "🌐 Language")
    else:
        kb.row("💳 ដាក់ប្រាក់",    "👜 កាបូបលុយ")
        kb.row("🎬 មើលរឿង",       "💬 ជំនួយ Support")
        kb.row("💡 របៀបប្រើប្រាស់", "🌐 ភាសា / Language")
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎬 គ្រប់គ្រងរឿង",   "📦 ការបញ្ជាទិញ")
    kb.row("🔥 បញ្ចុះតម្លៃទាំងអស់", "💳 ប្រាក់បញ្ញើ")
    kb.row("━━━ 📊 SMM ━━━")
    kb.row("📊 ការបញ្ជា SMM",  "⚙️ កំណត់ SMM API")
    kb.row("➕ បន្ថែម SMM",    "🗑️ លុប SMM")
    kb.row("💹 ប្រាក់ចំណេញ SMM")
    kb.row("━━━ 💰 ហិរញ្ញវត្ថុ ━━━")
    kb.row("💰 កាបូបលុយ",      "💰 ឆែកលុយ API")
    kb.row("💸 បន្ថែមប្រាក់",   "💔 កាត់ប្រាក់")
    kb.row("━━━ 👥 អ្នកប្រើ ━━━")
    kb.row("👥 អ្នកប្រើប្រាស់",  "📊 ស្ថិតិ")
    kb.row("🎟️ លេខកូដPromo",   "📢 ផ្សព្វផ្សាយ")
    kb.row("⏱ ល្បឿន Poll",     "🔄 ធ្វើឱ្យទាន់សម័យ")
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✕ Cancel")
    return kb

def lang_select_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="setlang:kh"),
         InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en")]
    ])

def deposit_amt_kb(uid=None, promo_code=None):
    lang = get_lang(uid) if uid else "kh"
    amts = [1, 2, 5, 10, 20, 50]
    btns = []
    row = []
    for a in amts:
        row.append(InlineKeyboardButton(f"${a}", callback_data=f"dep:{a}"))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(
        "✏️ ផ្ទាល់ខ្លួន" if lang=="kh" else "✏ Custom",
        callback_data="dep:custom")])
    return InlineKeyboardMarkup(btns)

def smm_cat_kb():
    PLATFORM_ICONS = {
        "tiktok": "🎵", "telegram": "📱", "facebook": "📘",
        "instagram": "📸", "youtube": "▶️", "twitter": "🐦",
        "x": "🐦", "threads": "🧵"
    }
    cats = _smm_get_categories()
    btns = []
    for cat in cats:
        icon = "📱"
        for key, ico in PLATFORM_ICONS.items():
            if key in cat.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {cat}", callback_data=f"smmcat:{cat}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def smm_svc_kb(cat):
    SVC_ICONS = {
        "follower":"👤","like":"❤️","view":"👁","comment":"💬",
        "share":"🔗","save":"🔖","member":"👥","subscriber":"🔔",
        "watch":"👀","reaction":"😍",
    }
    svcs = _smm_get_svcs_in_cat(cat)
    btns = []
    for slug, s in svcs:
        label = s.get("label", slug)
        icon = "⚡"
        for key, ico in SVC_ICONS.items():
            if key in label.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {label}", callback_data=f"smmsvc:{slug}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:smmcats")])
    return InlineKeyboardMarkup(btns)

def smm_qty_kb(slug, s):
    sr   = _smm_sell_rate(s["cost_rate"], slug)
    mn   = s.get("min", 100)
    mx   = s.get("max", 100000)
    label= s.get("label", slug)
    first= label.split()[0] if label else slug
    preset = s.get("preset_qtys")
    if preset and isinstance(preset, list):
        qtys = [q for q in preset if mn <= q <= mx]
    else:
        suggestions = [100, 500, 1000, 5000, 10000, 50000]
        qtys = []
        for q in [mn] + suggestions:
            if mn <= q <= mx and q not in qtys: qtys.append(q)
            if len(qtys) >= 6: break
    btns = []
    for q in qtys:
        price = sr * q / 1000
        btns.append([InlineKeyboardButton(
            f"{q:,} {first} — ${price:.2f}", callback_data=f"smmqty:{slug}:{q}")])
    
    btns.append([InlineKeyboardButton("✏️ បញ្ចូលចំនួនផ្ទាល់ខ្លួន (Custom Qty)", callback_data=f"smmcustom:{slug}")])
    
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:smmcats")])
    return InlineKeyboardMarkup(btns)

# ═══════════════════════════════════════════════════════════
#  SMM HELPERS
# ═══════════════════════════════════════════════════════════
def _smm_get_categories():
    cats = []
    for s in smm_services.values():
        c = s.get("category", "Other")
        if c not in cats: cats.append(c)
    return cats

def _smm_get_svcs_in_cat(cat):
    return [(slug, s) for slug, s in smm_services.items() if s.get("category") == cat]

def _smm_profit_pct(): return float(smm_profit.get("pct", 20))

def _smm_sell_rate(cost, slug=None):
    s = smm_services.get(slug, {})
    if s.get("custom_price"): 
        base_price = float(s["custom_price"])
    else:
        base_price = round(float(cost) * (1 + _smm_profit_pct() / 100), 4)
    return _calc_discounted_price(base_price)

def _smm_api_post(params, timeout=25):
    url = smm_api.get("url", "")
    if not url: return None
    try:
        r = http.post(url, data=params, timeout=timeout)
        return r.json()
    except Exception as e:
        logger.error(f"{CLR_RED}SMM API: {e}{CLR_RESET}"); return None

def _smm_fetch_service(api_id):
    key = smm_api.get("key", "")
    url = smm_api.get("url", "")
    if not key or not url: return None
    try:
        r = http.post(url, data={"key": key, "action": "services"}, timeout=20)
        for s in r.json():
            if str(s.get("service")) == str(api_id):
                return {
                    "cost_rate": s.get("rate", s.get("min", "0")),
                    "min": int(s.get("min", 100)),
                    "max": int(s.get("max", 100000)),
                    "raw_name": s.get("name", ""),
                }
    except Exception as e: logger.error(f"{CLR_RED}Fetch service: {e}{CLR_RESET}")
    return None

def _smm_clean_name(raw):
    raw = re.sub(r'\s*\[.*?\]\s*', ' ', raw)
    raw = re.sub(r'\s*\(.*?\)\s*', ' ', raw)
    return re.sub(r'\s+', ' ', raw).strip()[:60]

def _smm_service_list_text():
    if not smm_services: return "❌ គ្មាន Service ទេ"
    lines = ["<b>📋 SMM Services</b>\n━━━━━━━━━━━━━━━━━━"]
    for cat in _smm_get_categories():
        lines.append(f"\n📂 <b>{cat}</b>")
        for slug, s in _smm_get_svcs_in_cat(cat):
            sr = _smm_sell_rate(s["cost_rate"], slug)
            lines.append(f"  • {s.get('label',slug)} — ${sr:.2f}/1K")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
#  BAKONG KHQR & COUNTDOWN TIMER
# ═══════════════════════════════════════════════════════════
def _generate_khqr(uid, amount, note=""):
    try:
        from bakong_khqr import KHQR
        k = KHQR(BAKONG_TOKEN)
        qr_str = k.create_qr(
            bank_account  = BANK_ACCOUNT,
            merchant_name = MERCHANT_NAME,
            merchant_city = MERCHANT_CITY,
            amount        = round(float(amount), 2),
            currency      = "USD",
            bill_number   = (note or f"uid{uid}")[:25],
            static        = False,
        )
        return qr_str or ""
    except Exception as e:
        logger.error(f"{CLR_RED}[_generate_khqr] ❌ {e}{CLR_RESET}")
    return ""

def _check_bakong(md5, amount, start_ts):
    try:
        from bakong_khqr import KHQR as _BK
        k = _BK(BAKONG_TOKEN)
        status = k.check_payment(str(md5))
        return status == "PAID"
    except Exception as e:
        logger.error(f"{CLR_RED}[_check_bakong] {e}{CLR_RESET}")
    return False

def _watch_deposit(uid, uid_str, dep_id, amount, start_ts, sent_msg_id=None):
    deadline = time.time() + DEPOSIT_EXPIRE_SEC
    last_update_min = -1
    
    while time.time() < deadline:
        dep = store_deps.get(dep_id)
        if not dep or dep.get("status") != "confirmed":
            md5 = dep.get("md5", "") if dep else ""
            if md5 and _check_bakong(md5, amount, start_ts):
                bonus = float(dep.get("bonus", 0))
                total_credit = round(amount + bonus, 2)
                add_bal(uid, total_credit)
                store_deps[dep_id]["status"] = "confirmed"
                _save(STORE_DEP_FILE, store_deps)
                new_b = bal(uid)
                msg = (f"✅ <b>ដាក់លុយបានជោគជ័យ!</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"💰 បញ្ញើ: <b>${amount:.2f}</b>")
                if bonus > 0:
                    msg += f"\n🎟️ Promo Bonus: <b>+${bonus:.2f}</b>"
                msg += (f"\n💳 Balance: <b>${new_b:.2f}</b>")
                try:
                    bot.send_message(uid, msg, parse_mode="HTML", reply_markup=main_kb(uid))
                except: pass
                try:
                    bot.send_message(ADMIN_ID,
                        f"💰 <b>ដាក់លុយ ✅ (Auto)</b>\n👤 <code>{uid_str}</code>\n"
                        f"💰 ${amount:.2f}",
                        parse_mode="HTML")
                except: pass
                if sent_msg_id:
                    try:
                        bot.edit_message_caption(
                            chat_id=uid, message_id=sent_msg_id,
                            caption=f"💳 <b>ដាក់ប្រាក់ (បានទូទាត់រួចរាល់ ✅)</b>\n━━━━━━━━━━━━━━━━━━\n💰 ចំនួន: <b>${amount:.2f}</b>",
                            parse_mode="HTML"
                        )
                    except: pass
                return

        rem_sec = int(deadline - time.time())
        current_min = rem_sec // 60
        if current_min != last_update_min and sent_msg_id and rem_sec > 0:
            last_update_min = current_min
            mins_left = rem_sec // 60
            secs_left = rem_sec % 60
            timer_str = f"{mins_left:02d}:{secs_left:02d}"
            try:
                updated_cap = (
                    f"💳 <b>ដាក់ប្រាក់</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💰 ចំនួន: <b>${amount:.2f}</b>\n"
                    f"⏱ រាប់ថយក្រោយ: <b>{timer_str} នាទី</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 <b>Bakong KHQR សម្រាប់ទូទាត់</b>"
                )
                bot.edit_message_caption(chat_id=uid, message_id=sent_msg_id, caption=updated_cap, parse_mode="HTML")
            except: pass

        time.sleep(5)

    dep = store_deps.get(dep_id)
    if dep and dep.get("status") == "pending":
        dep["status"] = "expired"; _save(STORE_DEP_FILE, store_deps)
        try: bot.send_message(uid, "⏰ <b>QR ផុតកំណត់!</b> សូម top up ម្ដងទៀត", parse_mode="HTML")
        except: pass
        if sent_msg_id:
            try:
                bot.edit_message_caption(
                    chat_id=uid, message_id=sent_msg_id,
                    caption=f"💳 <b>ដាក់ប្រាក់ (ផុតកំណត់ ⏰)</b>\n━━━━━━━━━━━━━━━━━━\n💰 ចំនួន: <b>${amount:.2f}</b>",
                    parse_mode="HTML"
                )
            except: pass

def _send_deposit_qr(uid, amount, promo_code=None, label="💳 ដាក់ប្រាក់", bonus=0.0, promo_code_name=None):
    uid_str = str(uid)
    final_amount = amount

    qr_str = _generate_khqr(uid, final_amount, f"uid={uid} ${final_amount}")
    if not qr_str:
        bot.send_message(uid, "⚠️ មានបញ្ហា Generate QR! ទាក់ទង Admin", parse_mode="HTML")
        return

    try:
        from bakong_khqr import KHQR as _BK
        k = _BK(BAKONG_TOKEN)
        md5_hash = k.generate_md5(qr_str)
    except Exception as e:
        import hashlib
        md5_hash = hashlib.md5(qr_str.encode()).hexdigest()

    dep_id   = f"dep_{uid}_{int(time.time())}"
    start_ts = int(time.time())
    total_credit = round(final_amount + bonus, 2)

    store_deps[dep_id] = {
        "uid": uid_str, "amount": final_amount, "status": "pending",
        "bonus": bonus, "promo": "",
        "md5": md5_hash, "qr_str": qr_str,
    }
    _save(STORE_DEP_FILE, store_deps)

    cap = (f"{label}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"💰 ចំនួន: <b>${final_amount:.2f}</b>\n"
           f"⏱ រាប់ថយក្រោយ: <b>05:00 នាទី</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📱 <b>Bakong KHQR សម្រាប់ទូទាត់</b>")

    try:
        admin_txt = (
            f"📥 <b>ការស្នើដាក់លុយថ្មី!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 User ID: <code>{uid_str}</code>\n"
            f"💰 ទឹកប្រាក់ស្នើ: <b>${final_amount:.2f}</b>\n"
            f"💵 សរុបត្រូវបញ្ចូល: <b>${total_credit:.2f}</b>"
        )

        admin_deposit_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ដាក់ប្រាក់ឱ្យគេ", callback_data=f"manual_dep:approve:{dep_id}"),
                InlineKeyboardButton("❌ កុំដាក់ប្រាក់ឱ្យគេ", callback_data=f"manual_dep:reject:{dep_id}")
            ]
        ])
        bot.send_message(ADMIN_ID, admin_txt, parse_mode="HTML", reply_markup=admin_deposit_kb)
    except Exception as e:
        logger.error(f"{CLR_RED}[deposit] Admin notification error: {e}{CLR_RESET}")

    img_buf = None
    try:
        import base64
        r = http.post(
            "https://api.bakongrelay.com/v1/generate_khqr_image",
            json    = {"qr": qr_str},
            headers = {"Authorization": f"Bearer {BAKONG_TOKEN}", "Content-Type": "application/json"},
            timeout = 10,
        )
        if r.ok and r.json().get("responseCode") == 0:
            img_b64 = r.json().get("data", {}).get("image", "")
            if img_b64:
                if "," in img_b64: img_b64 = img_b64.split(",", 1)[1]
                img_buf = io.BytesIO(base64.b64decode(img_b64))
                img_buf.seek(0); img_buf.name = "khqr.png"
    except Exception:
        pass

    if img_buf is None:
        try:
            import qrcode as _qrc
            qr = _qrc.QRCode(box_size=6, border=2)
            qr.add_data(qr_str); qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img_buf = io.BytesIO(); img.save(img_buf, format="PNG"); img_buf.seek(0)
        except Exception:
            pass

    sent_msg_id = None
    if img_buf:
        try:
            img_buf.seek(0)
            sent_msg = bot.send_photo(uid, img_buf, caption=cap, parse_mode="HTML")
            sent_msg_id = sent_msg.message_id
        except:
            sent_msg = bot.send_message(uid, f"{cap}\n\n<code>{qr_str}</code>", parse_mode="HTML")
            sent_msg_id = sent_msg.message_id
    else:
        sent_msg = bot.send_message(uid, f"{cap}\n\n<code>{qr_str}</code>", parse_mode="HTML")
        sent_msg_id = sent_msg.message_id

    threading.Thread(target=_watch_deposit,
                     args=(uid, uid_str, dep_id, final_amount, start_ts, sent_msg_id), daemon=True).start()

# ═══════════════════════════════════════════════════════════
#  ORDER HELPERS
# ═══════════════════════════════════════════════════════════
def _make_order_id():
    return f"KZ{int(time.time())%100000:05d}"

def _place_smm_order(uid, slug, qty):
    uid_str = str(uid)
    s = smm_services.get(slug)
    if not s: return None, "❌ Service រកមិនឃើញ"
    sr    = _smm_sell_rate(s["cost_rate"], slug)
    price = sr * qty / 1000
    if bal(uid) < price: return None, f"❌ Balance មិនគ្រប់! (Balance: ${bal(uid):.2f})"
    ded_bal(uid, price)
    key = smm_api.get("key",""); url = smm_api.get("url","")
    res = _smm_api_post({"key": key, "action": "add",
                         "service": s["api_id"], "link": "pending", "quantity": qty})
    api_order_id = str(res.get("order","")) if res else ""
    oid = _make_order_id()
    smm_orders[oid] = {
        "uid": uid_str, "slug": slug, "label": s.get("label",slug),
        "qty": qty, "price": price, "api_order_id": api_order_id,
        "status": "pending", "ts": int(time.time()),
    }
    _save(SMM_ORD_FILE, smm_orders)
    return oid, None

# ═══════════════════════════════════════════════════════════
#  TRACK USER
# ═══════════════════════════════════════════════════════════
def _track_user(message):
    uid = message.chat.id
    uid_str = str(uid)
    u = message.from_user
    users_db[uid_str] = {
        "name":     u.first_name or "",
        "username": u.username or "",
        "last":     int(time.time()),
        "banned":   users_db.get(uid_str, {}).get("banned", False),
    }
    _save(USERS_FILE, users_db)
    wallets.setdefault(uid_str, 0.0)

def is_banned(uid):
    return bool(users_db.get(str(uid), {}).get("banned", False))

# ═══════════════════════════════════════════════════════════
#  START & WELCOME WITH GITHUB PHOTO (Support Start Parameters)
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    waiting.pop(uid, None)
    livechat_users.discard(uid)
    _track_user(message)
    
    if is_banned(uid):
        bot.send_message(uid, t(uid, "banned"))
        return
        
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) > 1:
        param = command_parts[1].strip()
        if param == "buy":
            bot.send_message(
                uid,
                "🎬 <b>សូមជ្រើសរើសចំណងជើងរឿងដែលអ្នកចង់ទស្សនា៖</b>",
                parse_mode="HTML",
                reply_markup=movies_kb()
            )
            return

    if uid == ADMIN_ID:
        bot.send_message(
            uid,
            f"🤖 <b>Panel Admin — Kairozen All-in-One</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{ADMIN_ID}</code>\n"
            f"💹 ចំណេញ SMM: <b>{_smm_profit_pct():.0f}%</b>\n"
            f"🔥 Global Discount: <b>{'ON (' + str(discount_config.get('pct')) + '%)' if discount_config.get('active') else 'OFF'}</b>\n"
            f"⏱ Poll: <b>{smm_poll.get('interval',5)}s</b>\n"
            f"━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML", reply_markup=admin_kb()
        )
        return

    user_name = message.from_user.first_name or "User"
    caption = t(uid, "welcome", user_name)
    photo_url = "https://raw.githubusercontent.com/ngna8947-sys/SmeyLov/main/photo_url.jpg"

    try:
        bot.send_photo(
            chat_id=uid,
            photo=photo_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=lang_select_kb()
        )
    except Exception:
        bot.send_message(uid, caption, parse_mode="HTML", reply_markup=lang_select_kb())

# ═══════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("setlang:"))
def cb_setlang(call):
    uid  = call.message.chat.id
    lang = call.data.split(":")[1]
    user_lang[str(uid)] = lang
    _save(LANG_FILE, user_lang)
    bot.answer_callback_query(call.id, t(uid, "lang_set"))
    
    try:
        bot.delete_message(uid, call.message.message_id)
    except:
        pass
        
    b = bal(uid)
    user_name = call.from_user.first_name or "User"
    caption = t(uid, "welcome", user_name) + f"\n\n💰 Balance: <b>${b:.2f}</b>"
    photo_url = "https://raw.githubusercontent.com/ngna8947-sys/SmeyLov/main/photo_url.jpg"
    
    try:
        bot.send_photo(
            chat_id=uid,
            photo=photo_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
    except Exception:
        bot.send_message(uid, caption, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("show_movie:"))
def cb_show_movie(call):
    uid = call.message.chat.id
    movie_id = call.data.split(":")[1]
    bot.answer_callback_query(call.id)
    
    selected_movie = next((m for m in MOVIES if m["id"] == movie_id), None)
    if not selected_movie:
        return
    
    caption = (
        f"🎬 <b>{selected_movie['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{selected_movie['desc']}\n\n"
        f"💵 តម្លៃ: <b>${selected_movie['price']:.2f}</b>"
    )
    
    try:
        bot.delete_message(uid, call.message.message_id)
    except:
        pass
        
    bot.send_photo(
        chat_id=uid,
        photo=selected_movie["photo"],
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 ទិញឥឡូវនេះ ($1.00)", callback_data=f"buy_movie:{selected_movie['id']}")],
            [InlineKeyboardButton("◀️ ត្រឡប់ទៅរឿងផ្សេង", callback_data="back:movies")]
        ])
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_movie:"))
def cb_buy_movie(call):
    uid = call.message.chat.id
    movie_id = call.data.split(":")[1]
    selected_movie = next((m for m in MOVIES if m["id"] == movie_id), None)
    
    if not selected_movie:
        bot.answer_callback_query(call.id, "❌ រកមិនឃើញរឿងនេះទេ!", show_alert=True)
        return

    price = selected_movie["price"]
    user_balance = bal(uid)

    if user_balance < price:
        bot.answer_callback_query(call.id, "❌ ទឹកប្រាក់ក្នុងកាបូបរបស់អ្នកមិនគ្រប់គ្រាន់ទេ!", show_alert=True)
        
        low_bal_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 ដាក់ប្រាក់បន្ថែម", callback_data="dep:1"),
             InlineKeyboardButton("👜 មើលកាបូបលុយ", callback_data="show_wallet")]
        ])
        bot.send_message(
            uid,
            f"❌ <b>ទឹកប្រាក់មិនគ្រប់គ្រាន់!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 តម្លៃរឿង: <b>${price:.2f}</b>\n"
            f"💳 ប្រាក់របស់អ្នក: <b>${user_balance:.2f}</b>\n\n"
            f"👇 សូមធ្វើការដាក់ប្រាក់បន្ថែមដើម្បីទស្សនារឿងនេះ៖",
            parse_mode="HTML",
            reply_markup=low_bal_kb
        )
        return

    ded_bal(uid, price)
    bot.answer_callback_query(call.id, "✅ ទិញរឿងបានជោគជ័យ!")

    success_msg = (
        f"✅ <b>ទិញរឿងបានជោគជ័យ!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>{selected_movie['title']}</b>\n"
        f"💰 បានកាត់ប្រាក់: <b>${price:.2f}</b>\n"
        f"💳 សល់ប្រាក់ក្នុងកាបូប: <b>${bal(uid):.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>តំណភ្ជាប់ទស្សនារឿងរបស់អ្នក៖</b>\n"
        f"👉 <a href='{selected_movie['video_link']}'>ចុចទីនេះដើម្បីមើលវីដេអូរឿង</a>"
    )

    try:
        bot.send_message(uid, success_msg, parse_mode="HTML", reply_markup=main_kb(uid))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "show_wallet")
def cb_show_wallet(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    b = bal(uid)
    bot.send_message(
        uid,
        f"👜 <b>កាបូបលុយរបស់អ្នក</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 សាច់ប្រាក់បច្ចុប្បន្ន: <b>${b:.2f}</b>",
        parse_mode="HTML",
        reply_markup=main_kb(uid)
    )

@bot.callback_query_handler(func=lambda c: c.data == "back:movies")
def cb_back_movies(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(uid, call.message.message_id)
    except:
        pass
    bot.send_message(
        uid,
        "🎬 <b>សូមជ្រើសរើសចំណងជើងរឿងដែលអ្នកចង់ទស្សនា៖</b>",
        parse_mode="HTML",
        reply_markup=movies_kb()
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("poll:"))
def cb_poll(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    sec = int(call.data.split(":")[1])
    smm_poll["interval"] = sec; _save(SMM_POLL_FILE, smm_poll)
    bot.answer_callback_query(call.id, f"✅ Poll = {sec}s")
    try: bot.edit_message_text(f"✅ Poll Speed = <b>{sec} វិ</b>",
                               chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("dep:"))
def cb_dep(call):
    uid     = call.message.chat.id
    uid_str = str(uid)
    lang    = get_lang(uid)
    val     = call.data[4:]
    bot.answer_callback_query(call.id)

    if val == "custom":
        waiting[uid] = {"step": "dep_custom"}
        bot.send_message(uid,
            "✏ <b>ផ្ញើចំនួន $ ដែលចង់ deposit:</b>" if lang=="kh" else
            "✏️ <b>Send amount $ to deposit:</b>",
            parse_mode="HTML", reply_markup=cancel_kb())
        return

    amount = float(val)
    waiting.pop(uid, None)
    _process_deposit(uid, uid_str, amount, None)

def _process_deposit(uid, uid_str, amount, promo_code):
    lang  = get_lang(uid)
    _send_deposit_qr(uid, amount,
                     label=f"💳 <b>{'ដាក់ប្រាក់' if lang=='kh' else 'Top Up'}</b>",
                     bonus=0.0, promo_code_name=None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("manual_dep:"))
def cb_manual_dep(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID:
        bot.answer_callback_query(call.id)
        return

    parts = call.data.split(":")
    action = parts[1]
    dep_id = parts[2]

    dep = store_deps.get(dep_id)
    if not dep:
        bot.answer_callback_query(call.id, "❌ សំណើនេះរកមិនឃើញ ឬផុតកំណត់ហើយ!", show_alert=True)
        return

    target_uid = int(dep["uid"])
    amount = float(dep["amount"])
    total_credit = amount

    if action == "approve":
        if dep.get("status") == "confirmed":
            bot.answer_callback_query(call.id, "⚠️ សំណើនេះបានបញ្ជាក់រួចរាល់ហើយ!", show_alert=True)
            return

        add_bal(target_uid, total_credit)
        dep["status"] = "confirmed"
        _save(STORE_DEP_FILE, store_deps)

        bot.answer_callback_query(call.id, "✅ បានដាក់ប្រាក់ឱ្យគេរួចរាល់!")
        
        try:
            bot.edit_message_text(
                f"✅ <b>បានដាក់ប្រាក់ឱ្យគេរួចរាល់!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: <code>{target_uid}</code>\n"
                f"💰 ចំនួន: <b>${total_credit:.2f}</b>",
                chat_id=uid, message_id=call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

        try:
            msg = (f"✅ <b>ដាក់លុយបានជោគជ័យ! (ដោយ Admin)</b>\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"💰 បញ្ញើ: <b>${amount:.2f}</b>\n"
                   f"💳 សាច់ប្រាក់បច្ចុប្បន្ន: <b>${bal(target_uid):.2f}</b>")
            bot.send_message(target_uid, msg, parse_mode="HTML", reply_markup=main_kb(target_uid))
        except Exception:
            pass

    elif action == "reject":
        dep["status"] = "rejected"
        _save(STORE_DEP_FILE, store_deps)

        bot.answer_callback_query(call.id, "❌ បានបដិសេធសំណើ!")
        
        try:
            bot.edit_message_text(
                f"❌ <b>បានបដិសេធ (កុំដាក់ប្រាក់ឱ្យគេ)!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: <code>{target_uid}</code>\n"
                f"💰 ចំនួន: <b>${amount:.2f}</b>",
                chat_id=uid, message_id=call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

        try:
            bot.send_message(target_uid, "❌ សំណើដាក់ប្រាក់របស់អ្នកត្រូវបានបដិសេធដោយ Admin។", parse_mode="HTML")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmapi:"))
def cb_smmapi(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    action = call.data[7:]
    bot.answer_callback_query(call.id)

    if action == "setup":
        waiting[uid] = "smm_api_url"
        bot.send_message(uid,
            "🌐 <b>ផ្ញើ SMM API URL</b>\nឧ: <code>https://smmking.net/api/v2</code>",
            parse_mode="HTML", reply_markup=cancel_kb())

    elif action == "test":
        url = smm_api.get("url",""); key = smm_api.get("key","")
        if not url or not key:
            bot.send_message(uid, "❌ API មិនទាន់ set!", reply_markup=admin_kb()); return
        try:
            r = http.post(url, data={"key": key, "action": "balance"}, timeout=10)
            d = r.json()
            balance  = d.get("balance", d.get("Balance", "?"))
            currency = d.get("currency", d.get("Currency", "USD"))
            bot.send_message(uid,
                f"✅ <b>Connection OK!</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"💰 Balance: <b>{balance} {currency}</b>",
                parse_mode="HTML", reply_markup=admin_kb())
        except Exception as e:
            bot.send_message(uid, f"❌ Connection failed: <code>{e}</code>",
                             parse_mode="HTML", reply_markup=admin_kb())

    elif action == "clear":
        smm_api.clear(); smm_api.update({"url":"","key":""})
        _save(SMM_API_FILE, smm_api)
        bot.send_message(uid, "🗑️ SMM API cleared!", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmaddcat:"))
def cb_smmaddcat(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    cat = call.data[len("smmaddcat:"):]
    bot.answer_callback_query(call.id)
    if cat == "custom":
        waiting[uid] = "smm_add_cat"
        bot.send_message(uid, "✏️ វាយ Category name (ឧ: TikTok Live, Spotify):",
                         reply_markup=cancel_kb())
    else:
        waiting[uid] = {"step": "smm_add_ids", "cat": cat}
        bot.send_message(uid,
            f"📂 Category: <b>{cat}</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"ផ្ញើ Service IDs (comma separated):\n"
            f"ឧ: <code>5441,5448,5502</code>\n\n"
            f"💡 IDs រក នៅ SMM Panel → Services",
            parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmcat:"))
def cb_smmcat(call):
    uid = call.message.chat.id
    cat = call.data[7:]
    bot.answer_callback_query(call.id)
    svcs = _smm_get_svcs_in_cat(cat)
    if not svcs:
        try: bot.answer_callback_query(call.id, "❌ គ្មាន Service", show_alert=True)
        except: pass
        return
    try:
        bot.edit_message_text(f"📂 <b>{cat}</b>\n━━━━━━━━━━━━━━━━━━\n{'ជ្រើស Service:'}",
                              chat_id=uid, message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=smm_svc_kb(cat))
    except:
        bot.send_message(uid, f"📂 <b>{cat}</b>", parse_mode="HTML", reply_markup=smm_svc_kb(cat))

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmsvc:"))
def cb_smmsvc(call):
    uid  = call.message.chat.id
    slug = call.data[7:]
    bot.answer_callback_query(call.id)
    s = smm_services.get(slug)
    if not s: return
    sr   = _smm_sell_rate(s["cost_rate"], slug)
    lang = get_lang(uid)
    txt  = (f"⚡ <b>{s.get('label',slug)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 {'តម្លៃ' if lang=='kh' else 'Price'}: <b>${sr:.2f}/1K</b>\n"
            f"📏 Min: {s.get('min',10):,}  ·  Max: {s.get('max',100000):,}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{'ជ្រើស Quantity:' if lang=='kh' else 'Choose Quantity:'}")
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=smm_qty_kb(slug, s))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=smm_qty_kb(slug, s))

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmqty:"))
def cb_smmqty(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    parts = call.data.split(":")
    slug  = parts[1]; qty = int(parts[2])
    s     = smm_services.get(slug)
    if not s: return
    sr    = _smm_sell_rate(s["cost_rate"], slug)
    price = sr * qty / 1000
    lang  = get_lang(uid)
    waiting[uid] = {"step": "smm_link", "slug": slug, "qty": qty, "price": price}
    try:
        bot.edit_message_text(
            f"🔗 <b>{'ផ្ញើ Link:' if lang=='kh' else 'Send Link:'}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 {s.get('label',slug)}\n"
            f"💰 {qty:,} — <b>${price:.4f}</b>",
            chat_id=uid, message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="back:main")]]))
    except:
        bot.send_message(uid, f"🔗 ផ្ញើ Link:", parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("smmcustom:"))
def cb_smmcustom(call):
    uid = call.message.chat.id
    slug = call.data.split(":")[1]
    bot.answer_callback_query(call.id)
    s = smm_services.get(slug)
    if not s: return
    
    waiting[uid] = {"step": "smm_custom_qty", "slug": slug}
    mn = s.get("min", 100)
    mx = s.get("max", 100000)
    
    bot.send_message(
        uid,
        f"✏️ <b>សូមបញ្ចូលចំនួន (Quantity) ដែលអ្នកចង់ទិញ៖</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📏 Min: <b>{mn:,}</b>  ·  Max: <b>{mx:,}</b>\n"
        f"<i>(សូមវាយជាតួលេខសុទ្ធ ឧទាហរណ៍: 2500)</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("delsvc:"))
def cb_delsvc(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    parts = call.data.split(":", 2)

    if len(parts) == 3 and parts[1] == "cat":
        cat = parts[2]
        to_del = [slug for slug, s in smm_services.items() if s.get("category") == cat]
        for slug in to_del:
            smm_services.pop(slug, None)
        _save(SMM_SVC_FILE, smm_services)
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=None)
        except: pass
        bot.send_message(uid,
            f"✅ Deleted <b>{len(to_del)}</b> services in <b>{cat}</b>",
            parse_mode="HTML", reply_markup=admin_kb())
        return

    slug = parts[1]
    s    = smm_services.get(slug)
    if not s:
        bot.send_message(uid, "❌ Service រកមិនឃើញ", reply_markup=admin_kb()); return
    label  = s.get("label", slug)
    api_id = s.get("api_id", "?")
    smm_services.pop(slug, None)
    _save(SMM_SVC_FILE, smm_services)
    try:
        bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=None)
    except: pass
    bot.send_message(uid,
        f"✅ Deleted: <b>[{api_id}] {label}</b>\n"
        f"📊 Remaining services: <b>{len(smm_services)}</b>",
        parse_mode="HTML", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("back:"))
def cb_back(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    dest = call.data[5:]
    waiting.pop(uid, None)
    livechat_users.discard(uid)
    if dest == "main":
        user_name = call.from_user.first_name or "User"
        caption = t(uid, "welcome", user_name)
        photo_url = "https://raw.githubusercontent.com/ngna8947-sys/SmeyLov/main/photo_url.jpg"
        try:
            bot.edit_message_caption(chat_id=uid, message_id=call.message.message_id, caption=caption, parse_mode="HTML", reply_markup=main_kb(uid))
        except:
            bot.send_message(uid, caption, parse_mode="HTML", reply_markup=main_kb(uid))
    elif dest == "shop" or dest == "movies":
        bot.send_message(uid, "🎬 <b>សូមជ្រើសរើសចំណងជើងរឿងដែលអ្នកចង់ទស្សនា៖</b>", parse_mode="HTML", reply_markup=movies_kb())
    elif dest == "smmcats":
        bot.send_message(uid, "📊 <b>SMM Services</b>", parse_mode="HTML", reply_markup=smm_cat_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("useraction:"))
def cb_useraction(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    parts  = call.data.split(":", 2)
    action = parts[1]
    target = parts[2]

    if action == "ban":
        users_db.setdefault(target, {})["banned"] = True
        _save(USERS_FILE, users_db)
        name = users_db[target].get("name","?")
        try: bot.edit_message_text(
            f"🚫 <b>Banned:</b> {name} <code>{target}</code>",
            chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass
        try: bot.send_message(int(target), "🚫 គណនីរបស់អ្នកត្រូវបាន ban!")
        except: pass

    elif action == "unban":
        users_db.setdefault(target, {})["banned"] = False
        _save(USERS_FILE, users_db)
        name = users_db[target].get("name","?")
        try: bot.edit_message_text(
            f"🔓 <b>Unbanned:</b> {name} <code>{target}</code>",
            chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass
        try: bot.send_message(int(target), "✅ គណនីរបស់អ្នកត្រូវបាន unban!")
        except: pass

    elif action == "addbal":
        waiting[uid] = {"step": "add_balance_amt", "target": target}
        name = users_db.get(target,{}).get("name","?")
        b    = float(wallets.get(target, 0))
        bot.send_message(uid,
            f"💸 <b>បន្ថែម Balance</b>\n👤 <b>{name}</b> <code>{target}</code>\n"
            f"💳 សាច់ប្រាក់: <b>${b:.2f}</b>\n━━━━━━━━━━━━━━━━━━\nផ្ញើ Amount $:",
            parse_mode="HTML", reply_markup=cancel_kb())

    elif action == "dedbal":
        waiting[uid] = {"step": "deduct_balance_amt", "target": target}
        name = users_db.get(target,{}).get("name","?")
        b    = float(wallets.get(target, 0))
        bot.send_message(uid,
            f"💔 <b>កាត់ Balance</b>\n👤 <b>{name}</b> <code>{target}</code>\n"
            f"💳 សាច់ប្រាក់: <b>${b:.2f}</b>\n━━━━━━━━━━━━━━━━━━\nផ្ញើ Amount $ ដក:",
            parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("adminpromo:"))
def cb_adminpromo(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    action = call.data.split(":")[1]
    if action == "add":
        waiting[uid] = "promo_add_code"
        bot.send_message(uid,
            "🎟️ <b>បន្ថែម Promo Code</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "ផ្ញើ: <code>CODE DISCOUNT TYPE USES</code>\n"
            "Type: <b>pct</b> (%) ឬ <b>fix</b> ($)\n"
            "ឧ: <code>SAVE50 50 pct 100</code>",
            parse_mode="HTML", reply_markup=cancel_kb())
    elif action == "list":
        _show_promos(uid)
    elif action.startswith("del_"):
        code = action[4:]
        promos.pop(code.upper(), None)
        _save(PROMO_FILE, promos)
        try:
            bot.edit_message_text(f"🗑️ Promo <b>{code}</b> លុបហើយ!",
                                  chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass

def _show_promos(uid):
    if not promos:
        bot.send_message(uid, "❌ គ្មាន Promo Code ទេ", reply_markup=admin_kb()); return
    lines = ["🎟️ <b>Promo Codes</b>\n━━━━━━━━━━━━━━━━━━"]
    btns  = []
    for code, p in promos.items():
        dtype = f"{p['discount']}%" if p.get("pct") else f"${p['discount']}"
        uses  = f"{p.get('used',0)}/{p.get('uses',0)}"
        lines.append(f"• <code>{code}</code> — <b>{dtype}</b> | {uses} ប្រើ")
        btns.append([InlineKeyboardButton(f"🗑 {code}", callback_data=f"adminpromo:del_{code}")])
    btns.append([InlineKeyboardButton("➕ Add Promo", callback_data="adminpromo:add")])
    bot.send_message(uid, "\n".join(lines), parse_mode="HTML",
                     reply_markup=InlineKeyboardMarkup(btns))

# ═══════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def handle(message):
    uid     = message.chat.id
    uid_str = str(uid)
    text    = message.text.strip() if message.text else ""
    step    = waiting.get(uid)
    lang    = get_lang(uid)

    _track_user(message)
    if is_banned(uid) and uid != ADMIN_ID:
        bot.send_message(uid, t(uid, "banned")); return

    if text in ("✕ Cancel", "❌ Cancel", "❌ បោះបង់"):
        waiting.pop(uid, None)
        livechat_users.discard(uid)
        kb = admin_kb() if uid == ADMIN_ID else main_kb(uid)
        bot.send_message(uid, t(uid, "cancel_ok"), reply_markup=kb); return

    if uid == ADMIN_ID and step == "broadcast_msg":
        _do_broadcast(uid, message)
        return

    if uid == ADMIN_ID and message.reply_to_message:
        replied_id = message.reply_to_message.message_id
        target_uid = livechat_sessions.get(str(replied_id))
        if target_uid:
            try:
                bot.copy_message(chat_id=int(target_uid), from_chat_id=ADMIN_ID, message_id=message.message_id)
            except Exception as e:
                bot.send_message(ADMIN_ID, f"❌ បញ្ជូនសារមិនទាន់បានទេ: {e}")
            return

    if uid == ADMIN_ID:

        if text == "🔥 បញ្ចុះតម្លៃទាំងអស់":
            waiting[uid] = "admin_set_discount"
            status_txt = "🟢 កំពុងបើក" if discount_config.get("active") else "🔴 កំពុងបិទ"
            cur_pct = discount_config.get("pct", 0)
            bot.send_message(uid,
                f"🔥 <b>គ្រប់គ្រងការបញ្ចុះតម្លៃសេវាកម្មទាំងអស់</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"ស្ថានភាព: <b>{status_txt}</b>\n"
                f"អភាគរយបញ្ចុះ: <b>{cur_pct}%</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"ផ្ញើទម្រង់ជា: <code>ON 20</code> (ដើម្បីបើកនិងកំណត់ 20%) ឬ <code>OFF</code> (ដើម្បីបិទ)",
                parse_mode="HTML", reply_markup=cancel_kb())
            return

        if step == "admin_set_discount":
            parts = text.strip().split()
            cmd = parts[0].upper()
            if cmd == "OFF":
                discount_config["active"] = False
                discount_config["pct"] = 0
                _save(DISCOUNT_FILE, discount_config)
                waiting.pop(uid, None)
                bot.send_message(uid, "✅ បាន **បិទ** ការបញ្ចុះតម្លៃទាំងអស់រួចរាល់!", parse_mode="HTML", reply_markup=admin_kb())
                return
            elif cmd == "ON" and len(parts) >= 2:
                try:
                    pct = float(parts[1])
                    discount_config["active"] = True
                    discount_config["pct"] = pct
                    _save(DISCOUNT_FILE, discount_config)
                    waiting.pop(uid, None)
                    bot.send_message(uid, f"✅ បាន **បើក** ការបញ្ចុះតម្លៃ **{pct}%** លើរាល់សេវាកម្មទាំងអស់!", parse_mode="HTML", reply_markup=admin_kb())
                    return
                except ValueError:
                    pass
            bot.send_message(uid, "❌ ទម្រង់មិនត្រឹមត្រូវ! ប្រើឧទាហរណ៍: <code>ON 15</code> ឬ <code>OFF</code>", parse_mode="HTML")
            return

        if text.startswith("/addbal"):
            parts = text.split()
            if len(parts) < 3:
                bot.send_message(uid, "ប្រើ: /addbal UID AMOUNT"); return
            try:
                target = parts[1]; amt = float(parts[2])
                add_bal(int(target), amt)
                bot.send_message(uid,
                    f"✅ +${amt:.2f} → <code>{target}</code>\n💳 Balance: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML", reply_markup=admin_kb())
                try: bot.send_message(int(target),
                    f"✅ <b>Admin បន្ថែមលុយ!</b>\n💰 +${amt:.2f} | សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML")
                except: pass
            except: bot.send_message(uid, "❌ Format ខុស")
            return

        if text.startswith("/deductbal"):
            parts = text.split()
            if len(parts) < 3:
                bot.send_message(uid, "ប្រើ: /deductbal UID AMOUNT"); return
            try:
                target = parts[1]; amt = float(parts[2])
                cur = bal(int(target))
                ded = min(amt, cur)
                ded_bal(int(target), ded)
                bot.send_message(uid,
                    f"✅ -${ded:.2f} → <code>{target}</code>\n💳 សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML", reply_markup=admin_kb())
            except: bot.send_message(uid, "❌ Format ខុស")
            return

        if isinstance(step, dict) and step.get("step") == "add_balance_amt":
            target = step["target"]
            try:
                amt = float(text.replace("$",""))
                add_bal(int(target), amt)
                _save(WALLETS_FILE, wallets)
                waiting.pop(uid, None)
                bot.send_message(uid,
                    f"✅ <b>បន្ថែម Balance</b>\n👤 <code>{target}</code>\n"
                    f"💰 +${amt:.2f} | សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML", reply_markup=admin_kb())
                try: bot.send_message(int(target),
                    f"✅ <b>Admin បន្ថែមលុយ!</b>\n💰 +${amt:.2f} | សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML")
                except: pass
            except: bot.send_message(uid, "❌ Amount ខុស! ឧ: <code>5.00</code>", parse_mode="HTML")
            return

        if isinstance(step, dict) and step.get("step") == "deduct_balance_amt":
            target = step["target"]
            try:
                amt  = float(text.replace("$",""))
                cur  = bal(int(target))
                ded  = min(amt, cur)
                ded_bal(int(target), ded)
                waiting.pop(uid, None)
                bot.send_message(uid,
                    f"✅ <b>កាត់ Balance</b>\n👤 <code>{target}</code>\n"
                    f"💔 -${ded:.2f} | សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML", reply_markup=admin_kb())
                try: bot.send_message(int(target),
                    f"⚠️ <b>Admin កាត់លុយ!</b>\n💔 -${ded:.2f} | សាច់ប្រាក់: <b>${bal(int(target)):.2f}</b>",
                    parse_mode="HTML")
                except: pass
            except: bot.send_message(uid, "❌ Amount ខុស!")
            return

        if step == "promo_add_code":
            parts = text.strip().split()
            if len(parts) < 4:
                bot.send_message(uid,
                    "❌ Format ខុស!\nឧ: <code>SAVE50 50 pct 100</code>", parse_mode="HTML"); return
            code = parts[0].upper()
            try:
                discount = float(parts[1])
                pct  = (parts[2].lower() == "pct")
                uses = int(parts[3])
            except:
                bot.send_message(uid, "❌ Format ខុស!", parse_mode="HTML"); return
            promos[code] = {"discount": discount, "pct": pct, "uses": uses, "used": 0}
            _save(PROMO_FILE, promos)
            waiting.pop(uid, None)
            dtype = f"{discount:.0f}%" if pct else f"${discount:.2f}"
            bot.send_message(uid,
                f"✅ <b>Promo Code Created!</b>\n"
                f"🎟 <code>{code}</code> — <b>{dtype}</b> | {uses} uses",
                parse_mode="HTML", reply_markup=admin_kb()); return

        if step == "smm_set_profit":
            try:
                pct = float(text)
                smm_profit["pct"] = pct; _save(SMM_PROFIT_FILE, smm_profit)
                waiting.pop(uid, None)
                bot.send_message(uid, f"✅ SMM Profit <b>{pct:.0f}%</b>",
                                 parse_mode="HTML", reply_markup=admin_kb())
            except: bot.send_message(uid, "❌ ត្រូវជាលេខ")
            return

        if step == "smm_api_url":
            smm_api["url"] = text.strip().rstrip("/")
            waiting[uid] = "smm_api_key"
            bot.send_message(uid,
                f"✅ URL: <code>{smm_api['url']}</code>\n\n🔑 ឥឡូវ ផ្ញើ API Key:",
                parse_mode="HTML", reply_markup=cancel_kb()); return

        if step == "smm_api_key":
            smm_api["key"] = text.strip()
            _save(SMM_API_FILE, smm_api)
            waiting.pop(uid, None)
            bot.send_message(uid, "⏳ Testing connection...", reply_markup=admin_kb())
            try:
                r = http.post(smm_api["url"],
                              data={"key": smm_api["key"], "action": "balance"},
                              timeout=10)
                d = r.json()
                balance  = d.get("balance", d.get("Balance", "?"))
                currency = d.get("currency", d.get("Currency", "USD"))
                bot.send_message(uid,
                    f"✅ <b>SMM API ភ្ជាប់ហើយ!</b>\n━━━━━━━━━━━━━━━━━━\n"
                    f"🌐 URL: <code>{smm_api['url']}</code>\n"
                    f"💰 សាច់ប្រាក់: <b>{balance} {currency}</b>",
                    parse_mode="HTML", reply_markup=admin_kb())
            except Exception as e:
                bot.send_message(uid,
                    f"⚠️ API Saved ប៉ុន្តែ test failed: <code>{e}</code>",
                    parse_mode="HTML", reply_markup=admin_kb())
            return

        if text == "🎬 គ្រប់គ្រងរឿង":
            bot.send_message(uid, "🎬 <b>បញ្ជីរឿងសព្វថ្ងៃ៖</b>\n" + "\n".join([f"• {m['title']} (${m['price']:.2f})" for m in MOVIES]), parse_mode="HTML", reply_markup=admin_kb())
            return

        if text == "📦 ការបញ្ជាទិញ":
            if not orders:
                bot.send_message(uid, "❌ គ្មានការបញ្ជាទិញ", reply_markup=admin_kb()); return
            lines = ["<b>📦 ការបញ្ជាទិញ (20 ចុងក្រោយ)</b>\n━━━━━━━━━━━━━━━━━━"]
            for oid, o in list(orders.items())[-20:]:
                lines.append(f"🆔 <code>{oid}</code> | 👤 <code>{o['uid']}</code> | ${o.get('price',0):.2f}")
            bot.send_message(uid, "\n".join(lines)[:4000], parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "📊 ការបញ្ជា SMM":
            if not smm_orders:
                bot.send_message(uid, "❌ គ្មានការបញ្ជា SMM", reply_markup=admin_kb()); return
            lines = ["<b>📊 ការបញ្ជា SMM (20 ចុងក្រោយ)</b>\n━━━━━━━━━━━━━━━━━━"]
            for oid, o in list(smm_orders.items())[-20:]:
                lines.append(f"🆔 <code>{oid}</code> | 👤 <code>{o['uid']}</code>\n  {o.get('label','?')} | Qty:{o.get('qty','?')} | ${o.get('price',0):.4f} | {o.get('status','?')}")
            bot.send_message(uid, "\n".join(lines)[:4000], parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "⚙️ កំណត់ SMM API":
            cur_url = smm_api.get("url","❌ មិនទាន់ set")
            cur_key = smm_api.get("key","❌ មិនទាន់ set")
            masked = cur_key[:6] + "****" + cur_key[-4:] if len(cur_key) > 10 else cur_key
            kb_api = InlineKeyboardMarkup([
                [InlineKeyboardButton("✏ កំណត់ URL + Key", callback_data="smmapi:setup")],
                [InlineKeyboardButton("🔌 សាកល្បងភ្ជាប់", callback_data="smmapi:test")],
                [InlineKeyboardButton("🗑️ លុប API", callback_data="smmapi:clear")],
            ])
            bot.send_message(uid,
                f"⚙️ <b>SMM API Config</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"🌐 URL: <code>{cur_url}</code>\n"
                f"🔑 Key: <code>{masked}</code>\n"
                f"━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML", reply_markup=kb_api); return

        if text == "💰 កាបូបលុយ":
            lines = ["<b>💰 កាបូបលុយអ្នកប្រើ</b>\n━━━━━━━━━━━━━━━━━━"]
            for u_id, u_info in sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)[:30]:
                b = wallets.get(u_id, 0)
                name = u_info.get("name","?")
                lines.append(f"👤 <b>{name}</b> <code>{u_id}</code> — <b>${float(b):.2f}</b>")
            bot.send_message(uid, "\n".join(lines)[:4000], parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "📊 ស្ថិតិ":
            total_orders = len(orders) + len(smm_orders)
            total_users  = len(users_db)
            total_rev    = sum(float(o.get("price",0)) for o in orders.values())
            total_rev   += sum(float(o.get("price",0)) for o in smm_orders.values())
            bot.send_message(uid,
                f"📊 <b>ស្ថិតិ</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👥 អ្នកប្រើ: <b>{total_users}</b>\n"
                f"📦 ការបញ្ជាសរុប: <b>{total_orders}</b>\n"
                f"💰 ចំណូលសរុប: <b>${total_rev:.2f}</b>\n"
                f"🎟️ Promo សកម្ម: <b>{len(promos)}</b>",
                parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "👥 អ្នកប្រើប្រាស់":
            users_sorted = sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)[:20]
            if not users_sorted:
                bot.send_message(uid, "❌ គ្មានអ្នកប្រើ", reply_markup=admin_kb()); return
            for u_id, u_info in users_sorted:
                b    = float(wallets.get(u_id, 0))
                name = u_info.get("name","?") or "?"
                uname= f"@{u_info['username']}" if u_info.get("username") else ""
                banned = u_info.get("banned", False)
                ban_label = "🔓 លែង Ban" if banned else "🚫 Ban"
                ban_cb    = f"useraction:unban:{u_id}" if banned else f"useraction:ban:{u_id}"
                status = " 🚫 BANNED" if banned else ""
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💸 បន្ថែមប្រាក់",  callback_data=f"useraction:addbal:{u_id}"),
                     InlineKeyboardButton("💔 កាត់ប្រាក់",    callback_data=f"useraction:dedbal:{u_id}")],
                    [InlineKeyboardButton(ban_label,           callback_data=ban_cb)],
                ])
                bot.send_message(uid,
                    f"👤 <b>{name}</b>{status}\n"
                    f"🆔 <code>{u_id}</code>  {uname}\n"
                    f"💳 Balance: <b>${b:.2f}</b>",
                    parse_mode="HTML", reply_markup=kb)
            return

        if text == "💳 ប្រាក់បញ្ញើ":
            pend = [(k, v) for k, v in store_deps.items() if v.get("status") == "pending"]
            if not pend:
                bot.send_message(uid, "✅ គ្មានការដាក់លុយ pending", reply_markup=admin_kb()); return
            lines = ["<b>💳 ប្រាក់បញ្ញើ រង់ចាំ</b>\n━━━━━━━━━━━━━━━━━━"]
            for k, v in pend:
                lines.append(f"👤 <code>{v.get('uid','?')}</code> | ${v.get('amount',0):.2f}\n  /addbal {v.get('uid','?')} {v.get('amount',0):.2f}")
            bot.send_message(uid, "\n".join(lines)[:4000], parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "💸 បន្ថែមប្រាក់":
            users_sorted = sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)[:15]
            btns = []
            for u_id, u_info in users_sorted:
                b    = float(wallets.get(u_id, 0))
                name = (u_info.get("name") or "?")[:18]
                btns.append([InlineKeyboardButton(
                    f"👤 {name}  ${b:.2f}", callback_data=f"useraction:addbal:{u_id}")])
            bot.send_message(uid,
                "💸 <b>បន្ថែមប្រាក់</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើសអ្នកប្រើ:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns)); return

        if text == "💔 កាត់ប្រាក់":
            users_sorted = sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)[:15]
            btns = []
            for u_id, u_info in users_sorted:
                b    = float(wallets.get(u_id, 0))
                name = (u_info.get("name") or "?")[:18]
                btns.append([InlineKeyboardButton(
                    f"👤 {name}  ${b:.2f}", callback_data=f"useraction:dedbal:{u_id}")])
            bot.send_message(uid,
                "💔 <b>កាត់ប្រាក់</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើសអ្នកប្រើ:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns)); return

        if text == "🎟️ លេខកូដPromo":
            _show_promos(uid)
            bot.send_message(uid,
                "🎟️ <b>គ្រប់គ្រង Promo Code</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ បន្ថែម Code", callback_data="adminpromo:add"),
                     InlineKeyboardButton("📋 មើលទាំងអស់", callback_data="adminpromo:list")]
                ])); return

        if text == "📢 ផ្សព្វផ្សាយ":
            waiting[uid] = "broadcast_msg"
            bot.send_message(uid,
                "📢 <b>ផ្សព្វផ្សាយ</b>\nសូមផ្ញើសារ អត្ថបទ រូបភាព ឬ វីដេអូ ដែលអ្នកចង់ផ្សាយ៖",
                parse_mode="HTML", reply_markup=cancel_kb()); return

        if text == "💹 ប្រាក់ចំណេញ SMM":
            waiting[uid] = "smm_set_profit"
            bot.send_message(uid,
                f"💹 <b>ប្រាក់ចំណេញ SMM: {_smm_profit_pct():.0f}%</b>\nផ្ញើ % ថ្មី:",
                parse_mode="HTML", reply_markup=cancel_kb()); return

        if text == "⏱ ល្បឿន Poll":
            cur = smm_poll.get("interval", 5)
            bot.send_message(uid, f"⏱ ល្បឿន Poll (បច្ចុប្បន្ន: {cur}s)",
                             reply_markup=InlineKeyboardMarkup([
                                 [InlineKeyboardButton("⚡ 3s", callback_data="poll:3"),
                                  InlineKeyboardButton("🟢 5s", callback_data="poll:5"),
                                  InlineKeyboardButton("🔵 10s", callback_data="poll:10")],
                                 [InlineKeyboardButton("🟡 15s", callback_data="poll:15"),
                                  InlineKeyboardButton("🔴 30s", callback_data="poll:30")],
                             ])); return

        if text == "🔄 ធ្វើឱ្យទាន់សម័យ":
            bot.send_message(uid, "✅ បានធ្វើឱ្យទាន់សម័យ!", reply_markup=admin_kb()); return

        if text == "➕ បន្ថែម SMM":
            cats_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 TikTok",    callback_data="smmaddcat:TikTok"),
                 InlineKeyboardButton("📘 Facebook",  callback_data="smmaddcat:Facebook")],
                [InlineKeyboardButton("📸 Instagram", callback_data="smmaddcat:Instagram"),
                 InlineKeyboardButton("▶️ YouTube",   callback_data="smmaddcat:YouTube")],
                [InlineKeyboardButton("📱 Telegram",  callback_data="smmaddcat:Telegram"),
                 InlineKeyboardButton("🐦 Twitter",   callback_data="smmaddcat:Twitter")],
                [InlineKeyboardButton("✏️ Custom Category", callback_data="smmaddcat:custom")],
            ])
            bot.send_message(uid,
                "➕ <b>បន្ថែម SMM Service</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើស Category:",
                parse_mode="HTML", reply_markup=cats_kb); return

        if text == "🗑️ លុប SMM":
            if not smm_services:
                bot.send_message(uid, "❌ គ្មាន SMM Service ទេ", reply_markup=admin_kb()); return
            cats = {}
            for slug, s in smm_services.items():
                cat = s.get("category", "Other")
                cats.setdefault(cat, []).append((slug, s))
            for cat, svcs in cats.items():
                btns = []
                for slug, s in svcs:
                    label = s.get("label", slug)[:30]
                    api_id = s.get("api_id", "?")
                    btns.append([InlineKeyboardButton(
                        f"🗑️ [{api_id}] {label}",
                        callback_data=f"delsvc:{slug}"
                    )])
                btns.append([InlineKeyboardButton(
                    f"🗑️ លុបទាំងអស់ {cat}",
                    callback_data=f"delsvc:cat:{cat}"
                )])
                bot.send_message(uid,
                    f"📂 <b>{cat}</b> — {len(svcs)} services\n━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(btns))
            return

        if text == "💰 ឆែកលុយ API":
            url = smm_api.get("url",""); key = smm_api.get("key","")
            if not url or not key:
                bot.send_message(uid, "❌ SMM API មិនទាន់ set! ចូល ⚙️ Set SMM API", reply_markup=admin_kb()); return
            try:
                r = http.post(url, data={"key": key, "action": "balance"}, timeout=10)
                d = r.json()
                balance  = d.get("balance", d.get("Balance", "?"))
                currency = d.get("currency", d.get("Currency", "USD"))
                bot.send_message(uid,
                    f"💰 <b>SMM API សាច់ប្រាក់</b>\n━━━━━━━━━━━━━━━━━━\n"
                    f"💵 សាច់ប្រាក់: <b>{balance} {currency}</b>\n"
                    f"🌐 API: <code>{url}</code>",
                    parse_mode="HTML", reply_markup=admin_kb())
            except Exception as e:
                bot.send_message(uid, f"❌ API Error: {e}", reply_markup=admin_kb())
            return

        if text.startswith("━━━"):
            bot.send_message(uid, "👇 ជ្រើស menu ខាងក្រោម:", reply_markup=admin_kb()); return

        bot.send_message(uid, f"❓ ពាក្យបញ្ជាមិនស្គាល់។ ប្រើប៊ូតុង Menu ខាងក្រោម។", reply_markup=admin_kb()); return

    # ══════════════════════════════════════════════════════
    #  USER SECTION
    # ══════════════════════════════════════════════════════

    if isinstance(step, dict) and step.get("step") == "dep_custom":
        try:
            amount = float(text.replace("$",""))
            if amount < 0.5: raise ValueError
            waiting.pop(uid, None)
            _process_deposit(uid, uid_str, amount, None)
        except:
            bot.send_message(uid, "❌ ចំនួនខុស! ឧ: <code>5.00</code>", parse_mode="HTML")
        return

    if step == "dep_custom":
        try:
            amount = float(text.replace("$",""))
            if amount < 0.5: raise ValueError
            waiting.pop(uid, None)
            _process_deposit(uid, uid_str, amount, None)
        except:
            bot.send_message(uid, "❌ ចំនួនខុស! ឧ: <code>5.00</code>", parse_mode="HTML")
        return

    if isinstance(step, dict) and step.get("step") == "smm_custom_qty":
        slug = step["slug"]
        s = smm_services.get(slug)
        waiting.pop(uid, None)
        
        if not s:
            bot.send_message(uid, "❌ Service រកមិនឃើញ", reply_markup=main_kb(uid))
            return
            
        try:
            qty = int(text.replace(",", "").replace(".", ""))
            mn = s.get("min", 100)
            mx = s.get("max", 100000)
            
            if qty < mn or qty > mx:
                bot.send_message(uid, f"❌ ចំនួនត្រូវស្ថិតចន្លោះពី <b>{mn:,}</b> ដល់ <b>{mx:,}</b>!", parse_mode="HTML", reply_markup=main_kb(uid))
                return
        except ValueError:
            bot.send_message(uid, "❌ សូមបញ្ចូលជាតួលេខត្រឹមត្រូវ!", reply_markup=main_kb(uid))
            return
            
        sr = _smm_sell_rate(s["cost_rate"], slug)
        price = sr * qty / 1000
        
        waiting[uid] = {"step": "smm_link", "slug": slug, "qty": qty, "price": price}
        
        bot.send_message(
            uid,
            f"🔗 <b>សូមផ្ញើ Link របស់អ្នកមក៖</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 {s.get('label', slug)}\n"
            f"🔢 ចំនួន: <b>{qty:,}</b>\n"
            f"💰 តម្លៃសរុប: <b>${price:.4f}</b>",
            parse_mode="HTML",
            reply_markup=cancel_kb()
        )
        return

    if isinstance(step, dict) and step.get("step") == "smm_link":
        slug  = step["slug"]
        qty   = step["qty"]
        price = step["price"]
        waiting.pop(uid, None)
        link  = text
        if bal(uid) < price:
            bot.send_message(uid,
                f"❌ Balance មិនគ្រប់!\n💳 ${bal(uid):.2f} | Need: ${price:.4f}",
                parse_mode="HTML", reply_markup=main_kb(uid)); return
        s = smm_services.get(slug)
        sr = _smm_sell_rate(s["cost_rate"], slug)
        ded_bal(uid, price)
        key = smm_api.get("key",""); api_url = smm_api.get("url","")
        res = None
        if key and api_url:
            res = _smm_api_post({"key":key,"action":"add","service":s["api_id"],"link":link,"quantity":qty})
        api_oid = str(res.get("order","")) if res else ""
        oid = _make_order_id()
        smm_orders[oid] = {
            "uid":uid_str,"slug":slug,"label":s.get("label",slug),
            "qty":qty,"price":price,"link":link,"api_order_id":api_oid,
            "status":"pending","ts":int(time.time())
        }
        _save(SMM_ORD_FILE, smm_orders)
        bot.send_message(uid,
            f"✅ <b>បញ្ជា SMM បានជោគជ័យ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{oid}</code>\n"
            f"📊 {s.get('label',slug)}\n"
            f"🔢 ចំនួន: <b>{qty:,}</b> | 💰 <b>${price:.4f}</b>\n"
            f"🔗 <code>{link}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 សាច់ប្រាក់: <b>${bal(uid):.2f}</b>",
            parse_mode="HTML", reply_markup=main_kb(uid))
        try: bot.send_message(ADMIN_ID,
            f"📊 <b>SMM Order</b>\n👤 <code>{uid_str}</code> | {s.get('label',slug)} | {qty:,} | ${price:.4f}", parse_mode="HTML")
        except: pass
        return

    if text in ("💳 ដាក់ប្រាក់", "💰 ដាក់ប្រាក់", "💰 Top Up", "💳 Top Up", "💸 បញ្ចូលលុយ"):
        livechat_users.discard(uid)
        b = bal(uid)
        waiting.pop(uid, None)
        bot.send_message(uid,
            f"💸 <b>{'ដាក់លុយ' if lang=='kh' else 'Top Up Wallet'}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 សាច់ប្រាក់: <b>${b:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{'ជ្រើស ចំនួន:' if lang=='kh' else 'Choose Amount:'}",
            parse_mode="HTML",
            reply_markup=deposit_amt_kb(uid)); return

    if text in ("🎬 មើលរឿង", "🎬 Movies"):
        livechat_users.discard(uid)
        bot.send_message(
            uid,
            "🎬 <b>សូមជ្រើសរើសចំណងជើងរឿងដែលអ្នកចង់ទស្សនា៖</b>",
            parse_mode="HTML",
            reply_markup=movies_kb()
        )
        return

    if text in ("💬 ជំនួយ Support", "💬 Support"):
        livechat_users.discard(uid)
        
        support_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 ឆាតផ្ទាល់ជាមួយ Admin (@SmeyLov008)", url="https://t.me/SmeyLov008")]
        ])
        
        bot.send_message(uid, t(uid, "support_msg"), parse_mode="HTML", reply_markup=support_kb)
        return

    if text in ("👜 កាបូបលុយ", "👜 Wallet"):
        livechat_users.discard(uid)
        b = bal(uid)
        bot.send_message(uid,
            f"👜 <b>{'កាបូបលុយ' if lang=='kh' else 'My Wallet'}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 សាច់ប្រាក់: <b>${b:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"ចុច 💳 {'ដាក់ប្រាក់' if lang=='kh' else 'Top Up'} ដើម្បីដាក់លុយ",
            parse_mode="HTML", reply_markup=main_kb(uid)); return

    if text in ("💡 របៀបប្រើប្រាស់", "💡 How to Use", "💡 របៀបប្រើ"):
        livechat_users.discard(uid)
        bot.send_message(uid, t(uid, "how_to_use"), parse_mode="HTML", reply_markup=main_kb(uid)); return

    if text in ("🌐 ភូមិភាសា / Language", "🌐 ភាសា / Language", "🌐 Language"):
        livechat_users.discard(uid)
        bot.send_message(uid, t(uid, "select_lang"),
                         parse_mode="HTML", reply_markup=lang_select_kb()); return

    bot.send_message(uid, t(uid, "fallback"), reply_markup=main_kb(uid))

# ═══════════════════════════════════════════════════════════
#  BROADCAST (Supports text, photo, video)
# ═══════════════════════════════════════════════════════════
def _do_broadcast(admin_uid, message):
    waiting.pop(admin_uid, None)
    sent = failed = 0
    msg_text = message.text or message.caption or ""
    
    bot_username = bot.get_me().username
    broadcast_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 មើលរឿងឥឡូវនេះ", url=f"https://t.me/{bot_username}?start=buy")]
    ])

    for u_id in list(users_db.keys()):
        try:
            if message.photo:
                bot.send_photo(int(u_id), message.photo[-1].file_id, caption=msg_text, parse_mode="HTML", reply_markup=broadcast_kb)
            elif message.video:
                bot.send_video(int(u_id), message.video.file_id, caption=msg_text, parse_mode="HTML", reply_markup=broadcast_kb)
            else:
                bot.send_message(int(u_id), msg_text, parse_mode="HTML", reply_markup=broadcast_kb)
            sent += 1
        except: 
            failed += 1
        time.sleep(0.05)
        
    bot.send_message(
        admin_uid,
        f"📢 <b>ផ្សព្វផ្សាយរួចរាល់!</b>\n✅ បានផ្ញើ: {sent} | ❌ បរាជ័យ: {failed}",
        parse_mode="HTML", reply_markup=admin_kb()
    )

# ═══════════════════════════════════════════════════════════
#  MEDIA HANDLERS FOR BROADCAST
# ═══════════════════════════════════════════════════════════
@bot.message_handler(content_types=["photo", "video"])
def handle_media(message):
    uid = message.chat.id
    if uid == ADMIN_ID and waiting.get(uid) == "broadcast_msg":
        _do_broadcast(uid, message); return

# ═══════════════════════════════════════════════════════════
#  FLASK CONTROL SERVER
# ═══════════════════════════════════════════════════════════
flask_app = Flask(__name__)
CONTROL_KEY = "kairozen_secret_2025"

def _check_key():
    key = flask_request.args.get("key") or (flask_request.get_json(silent=True) or {}).get("key")
    return key == CONTROL_KEY

@flask_app.route("/health")
def health():
    return jsonify({"status": "running", "bot": "Kairozen v4.1"})

@flask_app.route("/status")
def status():
    if not _check_key():
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({
        "status": "running",
        "users": len(users_db),
        "orders": len(orders) + len(smm_orders),
        "wallets": len(wallets),
    })

@flask_app.route("/shutdown", methods=["GET", "POST"])
def shutdown():
    if not _check_key():
        return jsonify({"error": "Unauthorized — wrong key"}), 403
    logger.warning(f"{CLR_RED}🛑 Shutdown requested via control server!{CLR_RESET}")
    try:
        bot.send_message(ADMIN_ID, "🛑 <b>Bot កំពុងបិទ...</b>\nបានទទួល shutdown command តាម Control Server។", parse_mode="HTML")
        time.sleep(1)
    except: pass
    def _stop():
        time.sleep(0.5)
        bot.stop_polling()
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_stop, daemon=True).start()
    return jsonify({"status": "shutting_down", "message": "Bot is stopping..."})

@flask_app.route("/restart", methods=["GET", "POST"])
def restart():
    if not _check_key():
        return jsonify({"error": "Unauthorized — wrong key"}), 403
    logger.warning(f"{CLR_YELLOW}🔄 Restart requested via control server!{CLR_RESET}")
    try:
        bot.send_message(ADMIN_ID, "🔄 <b>Bot កំពុង Restart...</b>\nបានទទួល restart command តាម Control Server។", parse_mode="HTML")
        time.sleep(1)
    except: pass
    def _restart():
        time.sleep(0.5)
        bot.stop_polling()
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({"status": "restarting", "message": "Bot is restarting..."})

@flask_app.route("/broadcast_web", methods=["POST"])
def broadcast_web():
    if not _check_key():
        return jsonify({"error": "Unauthorized"}), 403
    data = flask_request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    sent = failed = 0
    for u_id in list(users_db.keys()):
        try:
            bot.send_message(int(u_id), text, parse_mode="HTML")
            sent += 1
        except: failed += 1
        time.sleep(0.05)
    return jsonify({"sent": sent, "failed": failed})

def run_flask():
    logger.info(f"{CLR_CYAN}🌐 Control Server running on port 5055{CLR_RESET}")
    flask_app.run(host="0.0.0.0", port=5055, debug=False, use_reloader=False)

def print_banner():
    banner = f"""
{CLR_CYAN}{CLR_BOLD}╔══════════════════════════════════════════════════════════════╗
║     {CLR_GREEN}Kairozen All-in-One Bot v4.1 — カイロゼン                {CLR_CYAN}║
║     {CLR_YELLOW}ហាងរឿង (Movies Shop) + SMM Panel · ដាក់លុយ KHQR          {CLR_CYAN}║
║     {CLR_MAGENTA}Global Discount · Panel Admin                         {CLR_CYAN}║
║     {CLR_WHITE}Compatible: Python 3.10+ · Termux / Pydroid 3         {CLR_CYAN}║
╚══════════════════════════════════════════════════════════════╝{CLR_RESET}
"""
    print(banner)

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print_banner()
    logger.info(f"{CLR_BOLD}{CLR_GREEN}🚀 Kairozen All-in-One Bot v4.1 កំពុងចាប់ផ្ដើម...{CLR_RESET}")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
