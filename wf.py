# -*- coding: utf-8 -*-
"""
CATCH YOUR WAIFU BOT
Mudae uslubidagi waifu yig'ish/gacha o'yin boti.
Laziz uchun to'liq spec asosida yozilgan.
"""

import logging
import os
import random
import sqlite3
import time
from contextlib import contextmanager

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
#                       SOZLAMALAR
# =========================================================
BOT_TOKEN = "8850783895:AAEKkMFphOexPQ7K45MK5pj_-ICJ67KnRIY"
BOT_USERNAME = "IMBA_WAIFU_BOT"          # @ belgisisiz, botingiz username'i
OWNER_ID = 6553083044                                    # <-- O'ZINGIZNING Telegram ID'ingizni shu yerga yozing (pastda /myid orqali bilib olasiz)
SUPPORT_GROUP_ID = -1003982721971                            # <-- claim/ball/unban ishlaydigan asosiy SUPPORT guruh ID'si
SUPPORT_URL = "https://t.me/IMBA_WAIFU"
UPDATES_URL = "https://t.me/IMBA_WAIFU_UP"
MAIN_MENU_IMAGE = "AgACAgIAAxkBAAFOLllqSOhJoDgDsHrf9GcSL80SOn45bAAC0BdrGxDiQUq3j5PxpPEXqAEAAwIAA3MAAzwE"                          # xohlasangiz shu yerga file_id yoki URL qo'yishingiz mumkin, None bo'lsa rasmsiz yuboradi

DB_PATH = "waifu.db"

CLAIM_COOLDOWN = 24 * 60 * 60          # 24 soat
BALL_DAILY_LIMIT = 10
BALL_COOLDOWN = 60                     # 1 daqiqa
SPAWN_THRESHOLD_DEFAULT = 100          # necha xabardan keyin character chiqadi
MUTE_MSG_LIMIT = 10                    # ketma-ket nechta xabardan keyin mute
MUTE_DURATION = 5 * 60                 # 5 daqiqa
CHAR_ID_MIN = 101
CHAR_ID_MAX = 6665
TRADE_TIMEOUT = 24 * 60 * 60           # 24 soat
ADMIN_CONTACT_USERNAME = "Laziz_Rakhimov"   # <-- shop'dagi "Admin bilan savdo" tugmasi shu userga yo'naltiradi

CLAIM_REWARD = 777

# Boss Raid sozlamalari
BOSS_MAX_HP = 50000
BOSS_SPAWN_HOUR_UZB = 21   # har kuni 21:00 (Toshkent, UTC+5)
BOSS_DAMAGE_COOLDOWN = 30
BOSS_MIN_DAMAGE = 500
BOSS_MAX_DAMAGE = 1000
BOSS_REWARDS = {
    1: {"money": 7000, "rarity": "Exclusive"},
    2: {"money": 5000, "rarity": "Legendary"},
    3: {"money": 5000, "rarity": "Legendary"},
}
BOSS_REWARD_4_10 = 2000
BOSS_REWARD_REST = 500

# Titles
RICH_THRESHOLD = 50000
TOP_TRADER_THRESHOLD = 10

ANIME_EMOJI = {
    "naruto": "🍥",
    "one piece": "🏴‍☠️",
    "bleach": "⚔️",
}
DEFAULT_ANIME_EMOJI = "🏆"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
#                    RARITY TIZIMI
# =========================================================
ALL_RARITIES = [
    "Common", "Galaxies", "Summer", "Galactic", "Christmas", "Holi",
    "Marvelous", "Exclusive", "Manga Rush", "Mythical", "Tribe",
    "X-Mas", "Legendary", "Medium", "Winters", "Exotic", "Special",
]

RARITY_EMOJI = {
    "Common": "⚪️", "Galaxies": "🌟", "Summer": "☀️", "Galactic": "🌌",
    "Christmas": "🎄", "Holi": "🎨", "Marvelous": "🔥", "Exclusive": "🌸",
    "Manga Rush": "💎", "Mythical": "🔮", "Tribe": "🛖", "X-Mas": "🛷",
    "Legendary": "🟡", "Medium": "🟢", "Winters": "🧣", "Exotic": "🫧",
    "Special": "🔘",
}

# faqat shu 4 tasi /claim va /guess orqali random tushadi
DROP_WEIGHTS = {"Medium": 45, "Legendary": 45, "Exclusive": 5, "Mythical": 5}


def roll_rarity():
    names = list(DROP_WEIGHTS.keys())
    weights = list(DROP_WEIGHTS.values())
    return random.choices(names, weights=weights, k=1)[0]


def rarity_label(rarity: str) -> str:
    return f"{RARITY_EMOJI.get(rarity, '')} {rarity}"


# =========================================================
#                  KO'P TILLILIK (UZ / EN)
# =========================================================
TEXTS = {
    "choose_lang": {
        "uz": "🌐 Tilni tanlang / Choose your language",
        "en": "🌐 Tilni tanlang / Choose your language",
    },
    "lang_set": {
        "uz": "✅ Til o'zbekchaga o'rnatildi.",
        "en": "✅ Language set to English.",
    },
    "welcome": {
        "uz": (
            "🍃 HEY THERE...! {name}\n\n"
            "◎ ──── ❖ ──── ◎\n"
            "★ Men Catch Your Waifu botiman,\n"
            "guruhlaringizda anime characterlarini chiqarib turaman va "
            "foydalanuvchilar ularni to'plab boradi.\n"
            "★ Nima kutyapsiz, pastdagi tugma orqali meni guruhingizga qo'shing!\n"
            "◎ ──── ❖ ──── ◎\n\n"
            "Qanday ishlashimni bilish uchun HELP tugmasini bosing."
        ),
        "en": (
            "🍃 HEY THERE...! {name}\n\n"
            "◎ ──── ❖ ──── ◎\n"
            "★ I am Catch Your Waifu bot,\n"
            "I spawn anime characters in your groups, and let users collect them.\n"
            "★ So what are you waiting for, add me to your group with the button below!\n"
            "◎ ──── ❖ ──── ◎\n\n"
            "Hit HELP to find out more about how to use me."
        ),
    },
    "btn_addme": {"uz": "✦ MENI QO'SHISH ✦", "en": "✦ ADD ME ✦"},
    "btn_help": {"uz": "❓ YORDAM", "en": "❓ HELP"},
    "btn_support": {"uz": "💬 SUPPORT", "en": "💬 SUPPORT"},
    "btn_updates": {"uz": "📢 YANGILIKLAR", "en": "📢 UPDATES"},
    "btn_back": {"uz": "🔙 Orqaga", "en": "🔙 Back"},
    "help_text": {
        "uz": (
            "📖 Buyruqlar bo'limi:\n\n"
            "/guess <ism> — Guruhda chiqqan characterni tutish\n"
            "/claim — Kunlik bepul character (SUPPORT guruhda)\n"
            "/ball — Kuniga 10 marta pul yutish o'yini (SUPPORT guruhda)\n"
            "/damage — Boss Raid'ga zarba berish (SUPPORT guruhda)\n"
            "/harem — To'plamingizni ko'rish\n"
            "/profile — Profilingiz, unvonlar va streak\n"
            "/shop — Do'kon (shaxsiy chatda)\n"
            "/trade <ID> — Kimgadir reply qilib sotib olish so'rovi\n"
            "/gift <ID> — Kimgadir reply qilib character sovg'a qilish\n"
            "/fav <ID> — Character bor-yo'qligini tekshirish\n"
            "/wfav <ID> — Sevimlilarga qo'shish\n"
            "/whfav — Sevimlilar ro'yxati\n"
            "/wchar <ID> — Character haqida to'liq ma'lumot\n"
            "/wduplicate — Dublikat characterlaringiz\n"
            "/wrarity — Rarity bo'yicha statistika\n"
            "/wanimelist <anime> — Anime bo'yicha qidiruv\n"
            "/wfind <ID> — Kimda bor ekanini topish\n"
            "/wsend <miqdor> — Kimgadir reply qilib pul jo'natish\n"
            "/top, /ctop, /topgroups — Reytinglar\n"
            "/whmode — Harem ko'rinishini almashtirish\n"
            "/language — Tilni o'zgartirish"
        ),
        "en": (
            "📖 Help Section:\n\n"
            "/guess <name> — Catch the spawned character\n"
            "/claim — Daily free character (in SUPPORT group)\n"
            "/ball — Bowling money game, 10x/day (in SUPPORT group)\n"
            "/damage — Deal damage to the Boss Raid (in SUPPORT group)\n"
            "/harem — See your collection\n"
            "/profile — Your profile, titles and streak\n"
            "/shop — Shop (in private chat)\n"
            "/trade <ID> — Reply to someone to request a purchase\n"
            "/gift <ID> — Reply to someone to gift a character\n"
            "/fav <ID> — Check if a character exists\n"
            "/wfav <ID> — Add to favourites\n"
            "/whfav — Your favourites list\n"
            "/wchar <ID> — Full character info\n"
            "/wduplicate — Your duplicate characters\n"
            "/wrarity — Rarity stats\n"
            "/wanimelist <anime> — Search by anime\n"
            "/wfind <ID> — Find who owns it\n"
            "/wsend <amount> — Reply to someone to send money\n"
            "/top, /ctop, /topgroups — Leaderboards\n"
            "/whmode — Toggle harem view style\n"
            "/language — Change language"
        ),
    },
    "claim_success": {
        "uz": (
            "🎉 Tabriklaymiz! Sizga yangi character tushdi:\n\n"
            "🆔 {id}\n👤 {name}\n📺 {anime}\n{rarity}\n\n"
            "💰 +{reward} Waifu Dollar qo'shildi!"
        ),
        "en": (
            "🎉 Congrats! You got a new character:\n\n"
            "🆔 {id}\n👤 {name}\n📺 {anime}\n{rarity}\n\n"
            "💰 +{reward} Waifu Dollars added!"
        ),
    },
    "claim_wait": {
        "uz": "⏳ Siz bugun allaqachon /claim qildingiz. Faqat kuniga 1 marta ishlaydi, ertaga qayta urinib ko'ring.",
        "en": "⏳ You've already claimed today. Only once per day, try again tomorrow.",
    },
    "claim_wrong_chat": {
        "uz": "❌ Bu buyruq faqat asosiy SUPPORT guruhda ishlaydi.",
        "en": "❌ This command only works in the main SUPPORT group.",
    },
    "no_characters_yet": {
        "uz": "😔 Bazada hali random tushadigan character yo'q. Keyinroq urinib ko'ring.",
        "en": "😔 No characters available in the pool yet. Try again later.",
    },
}


def T(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in ("uz", "en") else "uz"
    text = TEXTS.get(key, {}).get(lang, key)
    if kwargs:
        return text.format(**kwargs)
    return text


# =========================================================
#                      DATABASE
# =========================================================
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT,
                balance INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                last_claim REAL DEFAULT 0,
                ball_count_today INTEGER DEFAULT 0,
                ball_day_marker TEXT DEFAULT '',
                last_ball_time REAL DEFAULT 0,
                harem_mode TEXT DEFAULT 'list',
                claim_streak INTEGER DEFAULT 0,
                last_claim_day TEXT DEFAULT '',
                rare_ticket INTEGER DEFAULT 0,
                legendary_ticket INTEGER DEFAULT 0,
                exclusive_badge INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                got_rare_pull INTEGER DEFAULT 0,
                boss_top1_count INTEGER DEFAULT 0,
                last_damage_time REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                language TEXT,
                msg_counter INTEGER DEFAULT 0,
                spawn_threshold INTEGER DEFAULT 100,
                last_sender_id INTEGER DEFAULT 0,
                last_sender_streak INTEGER DEFAULT 0,
                catches_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS characters (
                char_id INTEGER PRIMARY KEY,
                name TEXT,
                anime TEXT,
                rarity TEXT,
                file_id TEXT,
                added_by INTEGER,
                added_at REAL
            );

            CREATE TABLE IF NOT EXISTS harem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                char_id INTEGER,
                obtained_at REAL,
                obtained_chat_id INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                char_id INTEGER,
                PRIMARY KEY (user_id, char_id)
            );

            CREATE TABLE IF NOT EXISTS shop (
                char_id INTEGER PRIMARY KEY,
                price INTEGER
            );

            CREATE TABLE IF NOT EXISTS pending_spawns (
                chat_id INTEGER PRIMARY KEY,
                char_id INTEGER,
                message_id INTEGER,
                spawned_at REAL
            );

            CREATE TABLE IF NOT EXISTS pending_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                seller_id INTEGER,
                char_id INTEGER,
                price INTEGER,
                status TEXT DEFAULT 'awaiting_price',
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS collection_titles (
                user_id INTEGER,
                anime TEXT,
                earned_at REAL,
                PRIMARY KEY (user_id, anime)
            );

            CREATE TABLE IF NOT EXISTS boss_raid (
                id INTEGER PRIMARY KEY CHECK (id=1),
                hp INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 50000,
                active INTEGER DEFAULT 0,
                spawned_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS boss_damage (
                user_id INTEGER PRIMARY KEY,
                damage INTEGER DEFAULT 0
            );
            """
        )


def ensure_user(user_id, username=None, first_name=None):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            is_owner = 1 if user_id == OWNER_ID else 0
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, is_admin) VALUES (?,?,?,?)",
                (user_id, username, first_name, is_owner),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, first_name=? WHERE user_id=?",
                (username, first_name, user_id),
            )


def ensure_chat(chat_id, title=None):
    with db() as conn:
        row = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO chats (chat_id, title, spawn_threshold) VALUES (?,?,?)",
                (chat_id, title, SPAWN_THRESHOLD_DEFAULT),
            )
        elif title:
            conn.execute("UPDATE chats SET title=? WHERE chat_id=?", (title, chat_id))


def get_user(user_id):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_chat_row(chat_id):
    with db() as conn:
        return conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()


async def get_lang(update: Update) -> str:
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE:
        u = get_user(update.effective_user.id)
        return u["language"] if u and u["language"] else "uz"
    else:
        c = get_chat_row(chat.id)
        return c["language"] if c and c["language"] else "uz"


def set_user_lang(user_id, lang):
    with db() as conn:
        conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))


def set_chat_lang(chat_id, lang):
    with db() as conn:
        conn.execute("UPDATE chats SET language=? WHERE chat_id=?", (lang, chat_id))


def is_admin_user(user_id) -> bool:
    if user_id == OWNER_ID:
        return True
    u = get_user(user_id)
    return bool(u and u["is_admin"])


def is_banned_user(user_id) -> bool:
    u = get_user(user_id)
    return bool(u and u["is_banned"])


# =========================================================
#             TIL TANLASH / ASOSIY MENYU
# =========================================================
def lang_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]]
    )


def main_menu_keyboard(lang):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                T(lang, "btn_addme"),
                url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
            )],
            [
                InlineKeyboardButton(T(lang, "btn_help"), callback_data="menu_help"),
                InlineKeyboardButton(T(lang, "btn_support"), url=SUPPORT_URL),
            ],
            [InlineKeyboardButton(T(lang, "btn_updates"), url=UPDATES_URL)],
        ]
    )


def help_keyboard(lang):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(T(lang, "btn_back"), callback_data="menu_back")]]
    )


async def send_main_menu(update_or_query, lang, edit=False):
    text = T(lang, "welcome", name=update_or_query.from_user.first_name if edit else "")
    kb = main_menu_keyboard(lang)
    if edit:
        try:
            await update_or_query.edit_message_text(text, reply_markup=kb)
        except Exception:
            await update_or_query.message.reply_text(text, reply_markup=kb)
    else:
        await update_or_query.message.reply_text(text, reply_markup=kb)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    ensure_user(user.id, user.username, user.first_name)

    if chat.type == ChatType.PRIVATE:
        u = get_user(user.id)
        if not u["language"]:
            await update.message.reply_text(T("uz", "choose_lang"), reply_markup=lang_keyboard())
            context.user_data["awaiting_lang_for"] = "user"
            return
        lang = u["language"]
        await update.message.reply_text(
            T(lang, "welcome", name=user.first_name), reply_markup=main_menu_keyboard(lang)
        )
    else:
        ensure_chat(chat.id, chat.title)
        c = get_chat_row(chat.id)
        if not c["language"]:
            await update.message.reply_text(T("uz", "choose_lang"), reply_markup=lang_keyboard())
            context.chat_data["awaiting_lang_for"] = "chat"
            return
        lang = c["language"]
        await update.message.reply_text(
            T(lang, "welcome", name=chat.title or ""), reply_markup=main_menu_keyboard(lang)
        )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(T("uz", "choose_lang"), reply_markup=lang_keyboard())
    if chat.type == ChatType.PRIVATE:
        context.user_data["awaiting_lang_for"] = "user"
    else:
        context.chat_data["awaiting_lang_for"] = "chat"


async def on_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot guruhga qo'shilganda til so'raladi."""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            chat = update.effective_chat
            ensure_chat(chat.id, chat.title)
            await update.message.reply_text(T("uz", "choose_lang"), reply_markup=lang_keyboard())
            context.chat_data["awaiting_lang_for"] = "chat"


async def cb_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "uz" if query.data == "lang_uz" else "en"
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        set_user_lang(query.from_user.id, lang)
        await query.edit_message_text(T(lang, "lang_set"))
        await query.message.reply_text(
            T(lang, "welcome", name=query.from_user.first_name),
            reply_markup=main_menu_keyboard(lang),
        )
    else:
        ensure_chat(chat.id, chat.title)
        set_chat_lang(chat.id, lang)
        await query.edit_message_text(T(lang, "lang_set"))
        await query.message.reply_text(
            T(lang, "welcome", name=chat.title or ""),
            reply_markup=main_menu_keyboard(lang),
        )


async def cb_menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(update)
    await query.edit_message_text(T(lang, "help_text"), reply_markup=help_keyboard(lang))


async def cb_menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(update)
    chat = update.effective_chat
    name = query.from_user.first_name if chat.type == ChatType.PRIVATE else (chat.title or "")
    await query.edit_message_text(T(lang, "welcome", name=name), reply_markup=main_menu_keyboard(lang))


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sozlash uchun yordamchi buyruq: OWNER_ID va SUPPORT_GROUP_ID'ni bilib olish uchun."""
    chat = update.effective_chat
    await update.message.reply_text(
        f"👤 User ID: {update.effective_user.id}\n💬 Chat ID: {chat.id}"
    )


# =========================================================
#           CHARACTER QO'SHISH (/plus) — FAQAT ADMIN
# =========================================================
def char_id_exists(char_id) -> bool:
    with db() as conn:
        row = conn.execute("SELECT 1 FROM characters WHERE char_id=?", (char_id,)).fetchone()
        return row is not None


def random_free_char_id():
    for _ in range(200):
        cid = random.randint(CHAR_ID_MIN, CHAR_ID_MAX)
        if not char_id_exists(cid):
            return cid
    # ehtiyot chorasi: agar diapazon to'lib qolgan bo'lsa
    cid = CHAR_ID_MAX + 1
    while char_id_exists(cid):
        cid += 1
    return cid


def rarity_keyboard():
    rows = []
    row = []
    for i, r in enumerate(ALL_RARITIES, 1):
        row.append(InlineKeyboardButton(f"{RARITY_EMOJI.get(r,'')} {r}", callback_data=f"plus_rarity_{r}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def cmd_plus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != ChatType.PRIVATE:
        await update.message.reply_text("Bu buyruqni shaxsiy chatda ishlating.")
        return
    if not is_admin_user(user.id):
        await update.message.reply_text("⛔️ Sizda bu buyruqdan foydalanish huquqi yo'q.")
        return
    context.user_data["plus"] = {"step": "waiting_image"}
    await update.message.reply_text(
        "🖼 Character rasmini yuboring (fayl sifatida ham, oddiy rasm sifatida ham bo'ladi), "
        "yoki to'g'ridan-to'g'ri rasm havolasini (URL) yuboring.\n\n"
        "Bekor qilish uchun /cancel yozing."
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("plus", None)
    context.user_data.pop("trade_price_for", None)
    await update.message.reply_text("❌ Jarayon bekor qilindi.")


async def plus_receive_image_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    state = context.user_data.get("plus")
    state["file_id"] = file_id
    suggested_id = random_free_char_id()
    state["suggested_id"] = suggested_id
    state["step"] = "waiting_id_confirm"
    await update.message.reply_text(
        f"🆔 Taklif qilingan ID: {suggested_id}\n\n"
        f"Shu ID bilan davom etish uchun /okid yozing, "
        f"yoki o'zingiz xohlagan ID raqamini yuboring."
    )


async def plus_receive_image_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    msg = await update.message.reply_text("⏳ Rasm havoladan yuklanmoqda...")
    try:
        sent = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=url)
        file_id = sent.photo[-1].file_id
        await msg.delete()
        await plus_receive_image_file_id(update, context, file_id)
    except Exception as e:
        logger.exception(e)
        await msg.edit_text("❌ Bu yaroqli rasm havolasi emas, qaytadan urinib ko'ring.")


async def cmd_okid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("plus")
    if not state or state.get("step") != "waiting_id_confirm":
        return
    state["char_id"] = state["suggested_id"]
    state["step"] = "waiting_name"
    await update.message.reply_text("✏️ Character ismini kiriting:")


async def plus_receive_manual_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    state = context.user_data.get("plus")
    try:
        cid = int(text.strip())
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam yuboring yoki /okid yozing.")
        return
    if char_id_exists(cid):
        await update.message.reply_text(f"❌ Bu ID ({cid}) band, boshqa son tanlang.")
        return
    state["char_id"] = cid
    state["step"] = "waiting_name"
    await update.message.reply_text("✏️ Character ismini kiriting:")


async def plus_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    state = context.user_data.get("plus")
    state["name"] = text.strip()
    state["step"] = "waiting_anime"
    await update.message.reply_text("📺 Qaysi animedan? Anime nomini kiriting:")


async def plus_receive_anime(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    state = context.user_data.get("plus")
    state["anime"] = text.strip()
    state["step"] = "waiting_rarity"
    await update.message.reply_text("💠 Rarity tanlang:", reply_markup=rarity_keyboard())


async def cb_plus_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = context.user_data.get("plus")
    if not state or state.get("step") != "waiting_rarity":
        await query.edit_message_text("Jarayon topilmadi, /plus bilan qayta boshlang.")
        return

    rarity = query.data.replace("plus_rarity_", "")
    char_id = state["char_id"]
    name = state["name"]
    anime = state["anime"]
    file_id = state["file_id"]

    with db() as conn:
        conn.execute(
            "INSERT INTO characters (char_id, name, anime, rarity, file_id, added_by, added_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (char_id, name, anime, rarity, file_id, query.from_user.id, time.time()),
        )

    context.user_data.pop("plus", None)

    caption = (
        f"✅ Muvaffaqiyatli qo'shildi!\n\n"
        f"🆔 {char_id}\n👤 {name}\n📺 {anime}\n{rarity_label(rarity)}"
    )
    await query.edit_message_text("✅ Muvaffaqiyatli qo'shildi! Pastda ko'rishingiz mumkin.")
    await context.bot.send_photo(chat_id=query.from_user.id, photo=file_id, caption=caption)


async def handle_plus_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True qaytarsa — xabar /plus jarayoni ichida ishlov berildi."""
    state = context.user_data.get("plus")
    if not state:
        return False

    step = state.get("step")
    msg = update.message

    if step == "waiting_image":
        if msg.photo:
            await plus_receive_image_file_id(update, context, msg.photo[-1].file_id)
            return True
        if msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
            await plus_receive_image_file_id(update, context, msg.document.file_id)
            return True
        if msg.text and msg.text.startswith("http"):
            await plus_receive_image_url(update, context, msg.text.strip())
            return True
        await msg.reply_text("Iltimos, rasm yoki rasm havolasini yuboring.")
        return True

    if step == "waiting_id_confirm":
        if msg.text:
            await plus_receive_manual_id(update, context, msg.text)
            return True
        return True

    if step == "waiting_name" and msg.text:
        await plus_receive_name(update, context, msg.text)
        return True

    if step == "waiting_anime" and msg.text:
        await plus_receive_anime(update, context, msg.text)
        return True

    return True


# =========================================================
#              TITLES VA COLLECTION TITLES
# =========================================================
async def check_collection_titles(user_id, anime):
    """Foydalanuvchi shu anime'dagi barcha characterlarni yig'ib bo'lganini tekshiradi."""
    with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as c FROM characters WHERE anime=?", (anime,)
        ).fetchone()["c"]
        if total == 0:
            return
        owned = conn.execute(
            """
            SELECT COUNT(DISTINCT h.char_id) as c FROM harem h
            JOIN characters c ON h.char_id=c.char_id
            WHERE h.user_id=? AND c.anime=?
            """,
            (user_id, anime),
        ).fetchone()["c"]

        if owned >= total:
            already = conn.execute(
                "SELECT 1 FROM collection_titles WHERE user_id=? AND anime=?", (user_id, anime)
            ).fetchone()
            if not already:
                conn.execute(
                    "INSERT INTO collection_titles (user_id, anime, earned_at) VALUES (?,?,?)",
                    (user_id, anime, time.time()),
                )
                return True
    return False


def anime_title_text(anime: str) -> str:
    emoji = ANIME_EMOJI.get(anime.strip().lower(), DEFAULT_ANIME_EMOJI)
    return f"{emoji} {anime} Collector"


def get_user_titles(user_id) -> list:
    """Foydalanuvchining barcha unvonlarini (title) ro'yxat qilib qaytaradi."""
    titles = []
    u = get_user(user_id)
    if not u:
        return titles

    if (u["balance"] or 0) >= RICH_THRESHOLD:
        titles.append("💰 Rich")
    if (u["boss_top1_count"] or 0) >= 1:
        titles.append("⚔️ Boss Slayer")
    if u["got_rare_pull"]:
        titles.append("🍀 Lucky Player")
    if (u["total_trades"] or 0) >= TOP_TRADER_THRESHOLD:
        titles.append("🤝 Top Trader")

    with db() as conn:
        collections = conn.execute(
            "SELECT anime FROM collection_titles WHERE user_id=?", (user_id,)
        ).fetchall()
    for c in collections:
        titles.append(anime_title_text(c["anime"]))

    return titles


# =========================================================
#                    /claim
# =========================================================
def pick_random_character_by_rarity(rarity):
    with db() as conn:
        rows = conn.execute("SELECT * FROM characters WHERE rarity=?", (rarity,)).fetchall()
    return random.choice(rows) if rows else None


def pick_random_droppable_character():
    """DROP_WEIGHTS bo'yicha rarity tanlaydi, o'sha rarity'dan tasodifiy character qaytaradi."""
    tried = set()
    rarities = list(DROP_WEIGHTS.keys())
    while len(tried) < len(rarities):
        r = roll_rarity()
        if r in tried:
            continue
        char = pick_random_character_by_rarity(r)
        if char:
            return char
        tried.add(r)
    return None


async def cmd_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if is_banned_user(user.id):
        return
    if SUPPORT_GROUP_ID and chat.id != SUPPORT_GROUP_ID:
        await update.message.reply_text(T(lang, "claim_wrong_chat"))
        return

    u = get_user(user.id)
    now = time.time()
    if now - (u["last_claim"] or 0) < CLAIM_COOLDOWN:
        await update.message.reply_text(T(lang, "claim_wait"))
        return

    char = pick_random_droppable_character()
    if not char:
        await update.message.reply_text(T(lang, "no_characters_yet"))
        return

    # --- streak hisoblash ---
    yesterday = time.strftime("%Y-%m-%d", time.localtime(now - 24 * 60 * 60))
    prev_day = u["last_claim_day"] or ""
    new_streak = (u["claim_streak"] or 0) + 1 if prev_day == yesterday else 1
    today = time.strftime("%Y-%m-%d", time.localtime(now))

    bonus_lines = []
    rare_ticket_add, legendary_ticket_add, exclusive_badge_add = 0, 0, 0
    if new_streak == 7:
        rare_ticket_add = 1
        bonus_lines.append("🎫 Rare Ticket" if lang == "en" else "🎫 Rare Ticket")
    if new_streak == 30:
        legendary_ticket_add = 1
        bonus_lines.append("🎟 Legendary Ticket")
    if new_streak == 100:
        exclusive_badge_add = 1
        bonus_lines.append("🏅 Exclusive Badge")

    with db() as conn:
        conn.execute(
            "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,?)",
            (user.id, char["char_id"], now, chat.id),
        )
        conn.execute(
            """
            UPDATE users SET last_claim=?, balance=balance+?, claim_streak=?, last_claim_day=?,
            rare_ticket=rare_ticket+?, legendary_ticket=legendary_ticket+?, exclusive_badge=exclusive_badge+?,
            got_rare_pull = CASE WHEN ? IN ('Mythical','Exclusive') THEN 1 ELSE got_rare_pull END
            WHERE user_id=?
            """,
            (now, CLAIM_REWARD, new_streak, today, rare_ticket_add, legendary_ticket_add,
             exclusive_badge_add, char["rarity"], user.id),
        )

    await check_collection_titles(user.id, char["anime"])

    caption = T(
        lang, "claim_success",
        id=char["char_id"], name=char["name"], anime=char["anime"],
        rarity=rarity_label(char["rarity"]), reward=CLAIM_REWARD,
    )

    streak_line = f"\n🔥 Streak: {new_streak} kun" if lang == "uz" else f"\n🔥 Streak: {new_streak} days"
    caption += streak_line
    if bonus_lines:
        bonus_title = "\n🎁 Bonus: " if lang == "uz" else "\n🎁 Bonus: "
        caption += bonus_title + ", ".join(bonus_lines)

    await context.bot.send_photo(chat_id=chat.id, photo=char["file_id"], caption=caption)


# =========================================================
#                    /ball (bowling o'yini)
# =========================================================
def today_marker():
    return time.strftime("%Y-%m-%d")


async def cmd_ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if is_banned_user(user.id):
        return
    if SUPPORT_GROUP_ID and chat.id != SUPPORT_GROUP_ID:
        await update.message.reply_text(T(lang, "claim_wrong_chat"))
        return

    u = get_user(user.id)
    now = time.time()

    if now - (u["last_ball_time"] or 0) < BALL_COOLDOWN:
        remaining = int(BALL_COOLDOWN - (now - u["last_ball_time"]))
        if lang == "uz":
            await update.message.reply_text(f"⏳ Yana {remaining} soniyadan keyin urinib ko'ring.")
        else:
            await update.message.reply_text(f"⏳ Try again in {remaining} seconds.")
        return

    day_marker = u["ball_day_marker"] or ""
    count_today = u["ball_count_today"] or 0
    if day_marker != today_marker():
        count_today = 0

    if count_today >= BALL_DAILY_LIMIT:
        if lang == "uz":
            await update.message.reply_text("🚫 Bugungi /ball limitingiz tugadi (10/10). Ertaga urinib ko'ring.")
        else:
            await update.message.reply_text("🚫 You've used all your /ball tries today (10/10). Try tomorrow.")
        return

    dice_msg = await context.bot.send_dice(chat_id=chat.id, emoji="🎳")
    dice_value = dice_msg.dice.value  # 1..6, Telegram bowling: 6 = strike (barcha tup)

    pins = dice_value - 1  # 0..5 tup yiqiladi, 5 => hammasi (bizning tizimda "strike")
    is_strike = dice_value == 6

    if is_strike:
        reward = 100
    else:
        reward = 10 * (pins + 1)  # 0 tup=10, 1 tup=20, ...

    with db() as conn:
        conn.execute(
            "UPDATE users SET balance=balance+?, last_ball_time=?, ball_count_today=?, ball_day_marker=? "
            "WHERE user_id=?",
            (reward, now, count_today + 1, today_marker(), user.id),
        )

    remaining_tries = BALL_DAILY_LIMIT - (count_today + 1)
    if lang == "uz":
        result_text = (
            f"🎉 Siz {reward}$ yutdingiz!" if not is_strike else f"🎳 STRIKE! Siz {reward}$ yutdingiz!"
        )
        await update.message.reply_text(f"{result_text}\n🎯 Qolgan urinishlar: {remaining_tries}/{BALL_DAILY_LIMIT}")
    else:
        result_text = (
            f"🎉 You won {reward}$!" if not is_strike else f"🎳 STRIKE! You won {reward}$!"
        )
        await update.message.reply_text(f"{result_text}\n🎯 Remaining chances: {remaining_tries}/{BALL_DAILY_LIMIT}")


# =========================================================
#      GURUHDA XABAR HISOBLAGICH + SPAWN + ANTI-SPAM
# =========================================================
async def spawn_character(chat_id, context: ContextTypes.DEFAULT_TYPE, lang):
    char = pick_random_droppable_character()
    if not char:
        return
    if lang == "uz":
        caption = "🔮 Yangi waifu paydo bo'ldi!\nUni tutish uchun /guess <ism> deb yozing."
    else:
        caption = "🔮 A new waifu has just appeared!\nUse /guess <name> to catch it."
    sent = await context.bot.send_photo(chat_id=chat_id, photo=char["file_id"], caption=caption)
    with db() as conn:
        conn.execute(
            "INSERT INTO pending_spawns (chat_id, char_id, message_id, spawned_at) "
            "VALUES (?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET char_id=excluded.char_id, "
            "message_id=excluded.message_id, spawned_at=excluded.spawned_at",
            (chat_id, char["char_id"], sent.message_id, time.time()),
        )


async def group_activity_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har bir guruh xabarida: spawn hisoblagichi + ketma-ket xabar (anti-spam) tekshiruvi."""
    msg = update.message
    if not msg or update.effective_chat.type == ChatType.PRIVATE:
        return
    user = update.effective_user
    chat = update.effective_chat
    if user.is_bot:
        return

    ensure_chat(chat.id, chat.title)
    ensure_user(user.id, user.username, user.first_name)

    with db() as conn:
        c = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat.id,)).fetchone()

        # --- anti-spam: ketma-ket xabar hisoblagichi ---
        if c["last_sender_id"] == user.id:
            streak = c["last_sender_streak"] + 1
        else:
            streak = 1
        conn.execute(
            "UPDATE chats SET last_sender_id=?, last_sender_streak=? WHERE chat_id=?",
            (user.id, streak, chat.id),
        )

        # --- spawn hisoblagichi ---
        new_counter = c["msg_counter"] + 1
        threshold = c["spawn_threshold"] or SPAWN_THRESHOLD_DEFAULT
        should_spawn = new_counter >= threshold
        conn.execute(
            "UPDATE chats SET msg_counter=? WHERE chat_id=?",
            (0 if should_spawn else new_counter, chat.id),
        )

    if streak >= MUTE_MSG_LIMIT:
        try:
            until = int(time.time()) + MUTE_DURATION
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
                until_date=until,
            )
            with db() as conn:
                conn.execute(
                    "UPDATE chats SET last_sender_streak=0 WHERE chat_id=?", (chat.id,)
                )
            lang = await get_lang(update)
            if lang == "uz":
                await msg.reply_text(f"🔇 {user.first_name} ketma-ket ko'p xabar yuborgani uchun 5 daqiqaga mute qilindi.")
            else:
                await msg.reply_text(f"🔇 {user.first_name} was muted for 5 minutes for flooding.")
        except Exception as e:
            logger.warning(f"Mute qila olmadim: {e}")

    if should_spawn:
        lang = await get_lang(update)
        await spawn_character(chat.id, context, lang)


async def cmd_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = await get_lang(update)

    if is_banned_user(user.id):
        return
    if not context.args:
        return

    guess_name = " ".join(context.args).strip().lower()

    with db() as conn:
        spawn = conn.execute("SELECT * FROM pending_spawns WHERE chat_id=?", (chat.id,)).fetchone()
        if not spawn:
            return
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (spawn["char_id"],)).fetchone()
        if not char:
            return

        if char["name"].strip().lower() != guess_name:
            if lang == "uz":
                await update.message.reply_text("❌ Noto'g'ri ism.")
            else:
                await update.message.reply_text("❌ Incorrect name.")
            return

        conn.execute("DELETE FROM pending_spawns WHERE chat_id=?", (chat.id,))
        ensure_user(user.id, user.username, user.first_name)
        conn.execute(
            "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,?)",
            (user.id, char["char_id"], time.time(), chat.id),
        )
        conn.execute("UPDATE chats SET catches_count=catches_count+1 WHERE chat_id=?", (chat.id,))
        if char["rarity"] in ("Mythical", "Exclusive"):
            conn.execute("UPDATE users SET got_rare_pull=1 WHERE user_id=?", (user.id,))

    await check_collection_titles(user.id, char["anime"])

    if lang == "uz":
        text = (
            f"✅ {user.first_name} yangi character oldi!\n\n"
            f"👤 {char['name']}\n📺 {char['anime']}\n{rarity_label(char['rarity'])}\n\n"
            f"Bu character /harem ga qo'shildi."
        )
    else:
        text = (
            f"✅ {user.first_name} got a new character!\n\n"
            f"👤 {char['name']}\n📺 {char['anime']}\n{rarity_label(char['rarity'])}\n\n"
            f"Added to your /harem."
        )
    await update.message.reply_text(text)


# =========================================================
#           /harem, /profile VA STATISTIKA BUYRUQLARI
# =========================================================
async def cmd_harem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)
    u = get_user(user.id)
    mode = u["harem_mode"] or "list"

    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.char_id, c.name, c.anime, c.rarity, COUNT(*) as qty
            FROM harem h JOIN characters c ON h.char_id = c.char_id
            WHERE h.user_id=?
            GROUP BY c.char_id
            ORDER BY c.rarity, c.name
            """,
            (user.id,),
        ).fetchall()

    if not rows:
        text = "📭 Sizning haremingiz hali bo'sh." if lang == "uz" else "📭 Your harem is empty."
        await update.message.reply_text(text)
        return

    header = "✨ Sizning to'plamingiz ✨\n" if lang == "uz" else "✨ Your collection ✨\n"
    lines = [header]

    if mode == "grouped":
        by_rarity = {}
        for r in rows:
            by_rarity.setdefault(r["rarity"], []).append(r)
        for rarity in ALL_RARITIES:
            items = by_rarity.get(rarity)
            if not items:
                continue
            lines.append(f"\n{rarity_label(rarity)} ({len(items)}):")
            for r in items[:20]:
                qty_str = f" (x{r['qty']})" if r["qty"] > 1 else ""
                lines.append(f"  🆔{r['char_id']} {r['name']}{qty_str}")
    else:
        for r in rows[:50]:
            qty_str = f" (x{r['qty']})" if r["qty"] > 1 else ""
            lines.append(f"🆔{r['char_id']} {rarity_label(r['rarity'])} {r['name']} — {r['anime']}{qty_str}")
        if len(rows) > 50:
            more = f"\n...va yana {len(rows)-50} ta" if lang == "uz" else f"\n...and {len(rows)-50} more"
            lines.append(more)

    await update.message.reply_text("\n".join(lines))


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)
    u = get_user(user.id)

    with db() as conn:
        owned = conn.execute(
            "SELECT COUNT(DISTINCT char_id) as c FROM harem WHERE user_id=?", (user.id,)
        ).fetchone()["c"]
        total = conn.execute("SELECT COUNT(*) as c FROM characters").fetchone()["c"]

    percent = (owned / total * 100) if total else 0
    filled = int(percent // 10)
    bar = "🟪" * filled + "⬜️" * (10 - filled)

    status = "🚫 Banned" if u["is_banned"] else ("✅ Not Banned" if lang == "en" else "✅ Ban qilinmagan")
    titles = get_user_titles(user.id)
    titles_line = ("\n🎖 " + " | ".join(titles)) if titles else ""

    if lang == "uz":
        text = (
            f"✨ {user.first_name}ning profili ✨\n\n"
            f"🆔 ID: {user.id}\n"
            f"👤 Username: @{user.username or '-'}\n"
            f"🔒 Holat: {status}\n"
            f"💰 Balans: {u['balance']}$\n"
            f"🔥 Streak: {u['claim_streak'] or 0} kun{titles_line}\n\n"
            f"⚔️ To'plam: {owned}/{total} [{percent:.2f}%]\n"
            f"📊 Progress:\n{bar}"
        )
    else:
        text = (
            f"✨ {user.first_name}'s Profile ✨\n\n"
            f"🆔 ID: {user.id}\n"
            f"👤 Username: @{user.username or '-'}\n"
            f"🔒 Status: {status}\n"
            f"💰 Balance: {u['balance']}$\n"
            f"🔥 Streak: {u['claim_streak'] or 0} days{titles_line}\n\n"
            f"⚔️ Collection: {owned}/{total} [{percent:.2f}%]\n"
            f"📊 Progress:\n{bar}"
        )
    await update.message.reply_text(text)


async def cmd_wchar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    if not context.args:
        await update.message.reply_text("Foydalanish: /wchar <ID>" if lang == "uz" else "Usage: /wchar <ID>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak." if lang == "uz" else "ID must be a number.")
        return

    with db() as conn:
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()

    if not char:
        await update.message.reply_text("Bunday ID topilmadi." if lang == "uz" else "No character with that ID.")
        return

    caption = f"🆔 {char['char_id']}\n👤 {char['name']}\n📺 {char['anime']}\n{rarity_label(char['rarity'])}"
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=char["file_id"], caption=caption)


async def cmd_wduplicate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(update)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.char_id, c.name, c.rarity, COUNT(*) as qty
            FROM harem h JOIN characters c ON h.char_id=c.char_id
            WHERE h.user_id=?
            GROUP BY c.char_id
            HAVING qty > 1
            ORDER BY qty DESC
            """,
            (user.id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "Sizda dublikat character yo'q." if lang == "uz" else "You have no duplicate characters."
        )
        return

    title = "♻️ Dublikat characterlaringiz:\n" if lang == "uz" else "♻️ Your duplicate characters:\n"
    lines = [title]
    for r in rows[:50]:
        lines.append(f"🆔{r['char_id']} {rarity_label(r['rarity'])} {r['name']} — x{r['qty']}")
    await update.message.reply_text("\n".join(lines))


async def cmd_wrarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(update)
    with db() as conn:
        lines_data = []
        for r in ALL_RARITIES:
            total = conn.execute("SELECT COUNT(*) as c FROM characters WHERE rarity=?", (r,)).fetchone()["c"]
            owned = conn.execute(
                """
                SELECT COUNT(DISTINCT h.char_id) as c FROM harem h
                JOIN characters c ON h.char_id=c.char_id
                WHERE h.user_id=? AND c.rarity=?
                """,
                (user.id, r),
            ).fetchone()["c"]
            lines_data.append((r, owned, total))

    title = "✨ Rarity bo'yicha to'plamingiz ✨\n" if lang == "uz" else "✨ Your Collection by Rarity ✨\n"
    lines = [title]
    for r, owned, total in lines_data:
        lines.append(f"{RARITY_EMOJI.get(r,'')} {r}: {owned}/{total}")
    await update.message.reply_text("\n".join(lines))


async def cmd_wanimelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    if not context.args:
        await update.message.reply_text(
            "Foydalanish: /wanimelist <anime nomi>" if lang == "uz" else "Usage: /wanimelist <anime name>"
        )
        return
    query_text = " ".join(context.args).strip()
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM characters WHERE anime LIKE ? ORDER BY name", (f"%{query_text}%",)
        ).fetchall()

    if not rows:
        await update.message.reply_text("Hech narsa topilmadi." if lang == "uz" else "Nothing found.")
        return

    lines = [f"📺 \"{query_text}\" bo'yicha topilganlar:\n"] if lang == "uz" else [f"📺 Results for \"{query_text}\":\n"]
    for r in rows[:50]:
        lines.append(f"🆔{r['char_id']} {rarity_label(r['rarity'])} {r['name']}")
    await update.message.reply_text("\n".join(lines))


async def cmd_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    if not context.args:
        await update.message.reply_text(
            "Foydalanish: /find <character ID yoki ism>" if lang == "uz" else "Usage: /find <character ID or name>"
        )
        return
    query_text = " ".join(context.args).strip()

    with db() as conn:
        if query_text.isdigit():
            char = conn.execute("SELECT * FROM characters WHERE char_id=?", (int(query_text),)).fetchone()
        else:
            char = conn.execute(
                "SELECT * FROM characters WHERE name LIKE ? LIMIT 1", (f"%{query_text}%",)
            ).fetchone()

        if not char:
            await update.message.reply_text("Character topilmadi." if lang == "uz" else "Character not found.")
            return

        owners = conn.execute(
            """
            SELECT DISTINCT u.user_id, u.username, u.first_name
            FROM harem h JOIN users u ON h.user_id=u.user_id
            WHERE h.char_id=?
            LIMIT 30
            """,
            (char["char_id"],),
        ).fetchall()

    if not owners:
        text = f"😔 {char['name']} hali hech kimda yo'q." if lang == "uz" else f"😔 Nobody owns {char['name']} yet."
        await update.message.reply_text(text)
        return

    title = f"🔎 {char['name']}ga ega foydalanuvchilar:\n" if lang == "uz" else f"🔎 Users who own {char['name']}:\n"
    lines = [title]
    for o in owners:
        uname = f"@{o['username']}" if o["username"] else o["first_name"]
        lines.append(f"• {uname}")
    await update.message.reply_text("\n".join(lines))


# =========================================================
#     /fav, /wfav, /wfind, /wsend, /gift
# =========================================================
async def cmd_fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fav <id> — shu ID'li character bazada bor-yo'qligini tekshiradi."""
    lang = await get_lang(update)
    if not context.args:
        await update.message.reply_text("Foydalanish: /fav <ID>" if lang == "uz" else "Usage: /fav <ID>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak." if lang == "uz" else "ID must be a number.")
        return

    with db() as conn:
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()

    if char:
        text = (
            f"✅ Bu ID band: {char['name']} ({char['anime']}) {rarity_label(char['rarity'])}"
            if lang == "uz"
            else f"✅ This ID exists: {char['name']} ({char['anime']}) {rarity_label(char['rarity'])}"
        )
    else:
        text = f"❌ ID {cid} bazada mavjud emas." if lang == "uz" else f"❌ ID {cid} does not exist."
    await update.message.reply_text(text)


async def cmd_wfav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/wfav <id> — sevimlilar ro'yxatiga qo'shadi."""
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if not context.args:
        await update.message.reply_text("Foydalanish: /wfav <ID>" if lang == "uz" else "Usage: /wfav <ID>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak." if lang == "uz" else "ID must be a number.")
        return

    with db() as conn:
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()
        if not char:
            await update.message.reply_text("Bunday character topilmadi." if lang == "uz" else "Character not found.")
            return
        owns = conn.execute(
            "SELECT 1 FROM harem WHERE user_id=? AND char_id=?", (user.id, cid)
        ).fetchone()
        if not owns:
            text = "Bu character sizda yo'q, avval uni to'plashingiz kerak." if lang == "uz" \
                else "You don't own this character yet."
            await update.message.reply_text(text)
            return
        conn.execute(
            "INSERT OR IGNORE INTO favorites (user_id, char_id) VALUES (?,?)", (user.id, cid)
        )

    text = f"⭐️ {char['name']} sevimlilaringizga qo'shildi!" if lang == "uz" \
        else f"⭐️ {char['name']} added to your favourites!"
    await update.message.reply_text(text)


async def cmd_whfav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sevimlilar ro'yxatini ko'rsatadi."""
    user = update.effective_user
    lang = await get_lang(update)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.char_id, c.name, c.anime, c.rarity FROM favorites f
            JOIN characters c ON f.char_id=c.char_id
            WHERE f.user_id=?
            """,
            (user.id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "Sevimlilar ro'yxati bo'sh." if lang == "uz" else "Your favourites list is empty."
        )
        return

    title = "⭐️ Sevimlilaringiz:\n" if lang == "uz" else "⭐️ Your favourites:\n"
    lines = [title]
    for r in rows:
        lines.append(f"🆔{r['char_id']} {rarity_label(r['rarity'])} {r['name']} — {r['anime']}")
    await update.message.reply_text("\n".join(lines))


async def cmd_wfind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/wfind <id> — shu characterga kimlar ega ekanini ko'rsatadi."""
    await cmd_find(update, context)


async def cmd_wsend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/wsend <miqdor> — reply orqali o'z pulidan boshqa userga jo'natadi."""
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if not update.message.reply_to_message:
        text = "Bu buyruqni kimgadir reply qilib ishlating: /wsend <miqdor>" if lang == "uz" \
            else "Reply to someone with: /wsend <amount>"
        await update.message.reply_text(text)
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /wsend <miqdor>" if lang == "uz" else "Usage: /wsend <amount>")
        return
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Miqdor musbat son bo'lishi kerak." if lang == "uz" else "Amount must be a positive number.")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("O'zingizga pul jo'nata olmaysiz." if lang == "uz" else "You can't send money to yourself.")
        return

    ensure_user(target.id, target.username, target.first_name)
    sender = get_user(user.id)
    if (sender["balance"] or 0) < amount:
        await update.message.reply_text("Hisobingizda yetarli mablag' yo'q." if lang == "uz" else "Insufficient balance.")
        return

    with db() as conn:
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, user.id))
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, target.id))

    text = f"💸 {user.first_name} {target.first_name}ga {amount}$ jo'natdi." if lang == "uz" \
        else f"💸 {user.first_name} sent {amount}$ to {target.first_name}."
    await update.message.reply_text(text)


async def cmd_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gift <id> — reply orqali o'z haremidan characterni boshqa userga beradi."""
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if not update.message.reply_to_message:
        text = "Bu buyruqni kimgadir reply qilib ishlating: /gift <ID>" if lang == "uz" \
            else "Reply to someone with: /gift <ID>"
        await update.message.reply_text(text)
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /gift <ID>" if lang == "uz" else "Usage: /gift <ID>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak." if lang == "uz" else "ID must be a number.")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("O'zingizga sovg'a bera olmaysiz." if lang == "uz" else "You can't gift yourself.")
        return

    with db() as conn:
        harem_row = conn.execute(
            "SELECT id FROM harem WHERE user_id=? AND char_id=? LIMIT 1", (user.id, cid)
        ).fetchone()
        if not harem_row:
            await update.message.reply_text("Bu character sizda yo'q." if lang == "uz" else "You don't own this character.")
            return
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()

        ensure_user(target.id, target.username, target.first_name)
        conn.execute("DELETE FROM harem WHERE id=?", (harem_row["id"],))
        conn.execute(
            "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,?)",
            (target.id, cid, time.time(), update.effective_chat.id),
        )

    await check_collection_titles(target.id, char["anime"])

    text = f"🎁 {user.first_name} {target.first_name}ga {char['name']}ni sovg'a qildi!" if lang == "uz" \
        else f"🎁 {user.first_name} gifted {char['name']} to {target.first_name}!"
    await update.message.reply_text(text)


# =========================================================
#                       /trade
# =========================================================
async def cmd_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xaridor sotuvchining xabariga reply qilib: /trade <char_id>"""
    buyer = update.effective_user
    lang = await get_lang(update)
    ensure_user(buyer.id, buyer.username, buyer.first_name)

    if not update.message.reply_to_message:
        text = "Sotuvchining xabariga reply qilib ishlating: /trade <ID>" if lang == "uz" \
            else "Reply to the seller's message with: /trade <ID>"
        await update.message.reply_text(text)
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /trade <ID>" if lang == "uz" else "Usage: /trade <ID>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak." if lang == "uz" else "ID must be a number.")
        return

    seller = update.message.reply_to_message.from_user
    if seller.id == buyer.id:
        await update.message.reply_text("O'zingiz bilan savdo qila olmaysiz." if lang == "uz" else "You can't trade with yourself.")
        return

    ensure_user(seller.id, seller.username, seller.first_name)

    with db() as conn:
        owns = conn.execute(
            "SELECT 1 FROM harem WHERE user_id=? AND char_id=?", (seller.id, cid)
        ).fetchone()
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()

        if not char or not owns:
            text = "Sotuvchida bu character yo'q." if lang == "uz" else "The seller doesn't own this character."
            await update.message.reply_text(text)
            return

        cur = conn.execute(
            "INSERT INTO pending_trades (buyer_id, seller_id, char_id, status, created_at) "
            "VALUES (?,?,?, 'awaiting_price', ?)",
            (buyer.id, seller.id, cid, time.time()),
        )
        trade_id = cur.lastrowid

    context.bot_data.setdefault("awaiting_trade_price", {})[seller.id] = trade_id

    try:
        await context.bot.send_message(
            chat_id=seller.id,
            text=(
                f"💼 {buyer.first_name} (@{buyer.username or '-'}) sizdan "
                f"\"{char['name']}\" ({rarity_label(char['rarity'])}) characterini sotib olmoqchi.\n\n"
                f"Narxni raqam bilan yozing (Waifu Dollar):"
                if lang == "uz" else
                f"💼 {buyer.first_name} (@{buyer.username or '-'}) wants to buy "
                f"\"{char['name']}\" ({rarity_label(char['rarity'])}) from you.\n\n"
                f"Type the price (in Waifu Dollars):"
            ),
        )
        await update.message.reply_text(
            "✅ So'rov sotuvchining shaxsiy xabariga yuborildi." if lang == "uz"
            else "✅ Request sent to the seller's private chat."
        )
    except Exception:
        await update.message.reply_text(
            "⚠️ Sotuvchiga shaxsiy xabar yubora olmadim. U avval botga shaxsiy /start bosishi kerak."
            if lang == "uz" else
            "⚠️ Couldn't message the seller privately. They need to /start the bot in private first."
        )


async def handle_trade_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sotuvchi shaxsiy chatda narx kiritganda ishlaydi. True qaytarsa — ishlov berilgan."""
    seller_id = update.effective_user.id
    awaiting = context.bot_data.get("awaiting_trade_price", {})
    trade_id = awaiting.get(seller_id)
    if not trade_id:
        return False

    lang = await get_lang(update)
    text = update.message.text or ""
    try:
        price = int(text.strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Iltimos, musbat raqam yuboring." if lang == "uz" else "Please send a positive number.")
        return True

    with db() as conn:
        trade = conn.execute("SELECT * FROM pending_trades WHERE trade_id=?", (trade_id,)).fetchone()
        if not trade or trade["status"] != "awaiting_price":
            awaiting.pop(seller_id, None)
            return True
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (trade["char_id"],)).fetchone()
        conn.execute(
            "UPDATE pending_trades SET price=?, status='awaiting_confirm', created_at=? WHERE trade_id=?",
            (price, time.time(), trade_id),
        )

    awaiting.pop(seller_id, None)
    await update.message.reply_text(
        f"✅ Narx {price}$ deb belgilandi. Xaridorga yuborildi." if lang == "uz"
        else f"✅ Price set to {price}$. Sent to the buyer."
    )

    buyer_id = trade["buyer_id"]
    buyer_lang = get_user(buyer_id)["language"] or "uz"
    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Ha" if buyer_lang == "uz" else "✅ Yes", callback_data=f"trade_yes_{trade_id}"),
            InlineKeyboardButton("❌ Yo'q" if buyer_lang == "uz" else "❌ No", callback_data=f"trade_no_{trade_id}"),
        ]]
    )
    try:
        await context.bot.send_message(
            chat_id=buyer_id,
            text=(
                f"💼 Sotuvchi \"{char['name']}\" uchun {price}$ so'rayapti. Rozimisiz?"
                if buyer_lang == "uz" else
                f"💼 The seller wants {price}$ for \"{char['name']}\". Do you agree?"
            ),
            reply_markup=kb,
        )
    except Exception:
        pass
    return True


async def cb_trade_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buyer_id = query.from_user.id
    lang = await get_lang(update)

    parts = query.data.split("_")
    decision = parts[1]  # yes / no
    trade_id = int(parts[2])

    with db() as conn:
        trade = conn.execute("SELECT * FROM pending_trades WHERE trade_id=?", (trade_id,)).fetchone()
        if not trade or trade["status"] != "awaiting_confirm" or trade["buyer_id"] != buyer_id:
            await query.edit_message_text("Bu savdo endi amal qilmaydi." if lang == "uz" else "This trade is no longer valid.")
            return

        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (trade["char_id"],)).fetchone()

        if decision == "no":
            conn.execute("UPDATE pending_trades SET status='cancelled' WHERE trade_id=?", (trade_id,))
            await query.edit_message_text("❌ Savdo bekor qilindi." if lang == "uz" else "❌ Trade cancelled.")
            try:
                await context.bot.send_message(trade["seller_id"], "❌ Xaridor savdoni rad etdi." if lang == "uz" else "❌ Buyer declined the trade.")
            except Exception:
                pass
            return

        buyer = conn.execute("SELECT * FROM users WHERE user_id=?", (buyer_id,)).fetchone()
        if (buyer["balance"] or 0) < trade["price"]:
            await query.edit_message_text("❌ Hisobingizda yetarli mablag' yo'q." if lang == "uz" else "❌ Insufficient balance.")
            return

        seller_owns = conn.execute(
            "SELECT id FROM harem WHERE user_id=? AND char_id=? LIMIT 1", (trade["seller_id"], trade["char_id"])
        ).fetchone()
        if not seller_owns:
            await query.edit_message_text("❌ Sotuvchida bu character endi yo'q." if lang == "uz" else "❌ Seller no longer has this character.")
            conn.execute("UPDATE pending_trades SET status='cancelled' WHERE trade_id=?", (trade_id,))
            return

        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (trade["price"], buyer_id))
        conn.execute("UPDATE users SET balance=balance+?, total_trades=total_trades+1 WHERE user_id=?", (trade["price"], trade["seller_id"]))
        conn.execute("UPDATE users SET total_trades=total_trades+1 WHERE user_id=?", (buyer_id,))
        conn.execute("DELETE FROM harem WHERE id=?", (seller_owns["id"],))
        conn.execute(
            "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,0)",
            (buyer_id, trade["char_id"], time.time()),
        )
        conn.execute("UPDATE pending_trades SET status='completed' WHERE trade_id=?", (trade_id,))

    await check_collection_titles(buyer_id, char["anime"])

    await query.edit_message_text(
        f"✅ Savdo yakunlandi! {char['name']} haremingizga qo'shildi." if lang == "uz"
        else f"✅ Trade completed! {char['name']} added to your harem."
    )
    try:
        await context.bot.send_message(
            trade["seller_id"],
            f"✅ Savdo yakunlandi! Sizga {trade['price']}$ tushdi." if lang == "uz"
            else f"✅ Trade completed! You received {trade['price']}$.",
        )
    except Exception:
        pass


async def job_expire_trades(context: ContextTypes.DEFAULT_TYPE):
    """24 soatdan oshgan savdolarni avtomatik bekor qiladi (JobQueue orqali muntazam ishlaydi)."""
    cutoff = time.time() - TRADE_TIMEOUT
    with db() as conn:
        expired = conn.execute(
            "SELECT * FROM pending_trades WHERE status IN ('awaiting_price','awaiting_confirm') AND created_at < ?",
            (cutoff,),
        ).fetchall()
        for tr in expired:
            conn.execute("UPDATE pending_trades SET status='cancelled' WHERE trade_id=?", (tr["trade_id"],))

    for tr in expired:
        awaiting = context.bot_data.get("awaiting_trade_price", {})
        awaiting.pop(tr["seller_id"], None)
        for uid in (tr["buyer_id"], tr["seller_id"]):
            try:
                await context.bot.send_message(uid, "⌛️ Savdo muddati tugadi va bekor qilindi.")
            except Exception:
                pass


# =========================================================
#                        SHOP
# =========================================================
async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    if update.effective_chat.type != ChatType.PRIVATE:
        await update.message.reply_text(
            "🛍 Shop faqat shaxsiy chatda ishlaydi." if lang == "uz" else "🛍 Shop only works in private chat."
        )
        return

    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.char_id, s.price, c.name, c.rarity FROM shop s
            JOIN characters c ON s.char_id=c.char_id
            ORDER BY s.char_id
            """
        ).fetchall()

    buttons = [
        [InlineKeyboardButton(f"🆔{r['char_id']} {r['name']} — {r['price']}$", callback_data=f"shop_view_{r['char_id']}")]
        for r in rows
    ]
    buttons.append([InlineKeyboardButton(
        "💬 Admin bilan savdo" if lang == "uz" else "💬 Trade with Admin",
        url=f"https://t.me/{ADMIN_CONTACT_USERNAME}",
    )])

    title = "🛍 Bugungi Shop:" if lang == "uz" else "🛍 Today's Shop:"
    if not rows:
        title = "🛍 Shop hozircha bo'sh." if lang == "uz" else "🛍 Shop is currently empty."

    await update.message.reply_text(title, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(update)
    cid = int(query.data.replace("shop_view_", ""))

    with db() as conn:
        row = conn.execute(
            """
            SELECT s.char_id, s.price, c.name, c.anime, c.rarity, c.file_id FROM shop s
            JOIN characters c ON s.char_id=c.char_id WHERE s.char_id=?
            """,
            (cid,),
        ).fetchone()

    if not row:
        await query.edit_message_text("Bu character shopdan olib tashlangan." if lang == "uz" else "This item was removed from the shop.")
        return

    caption = (
        f"🆔 {row['char_id']}\n👤 {row['name']}\n📺 {row['anime']}\n{rarity_label(row['rarity'])}\n\n"
        f"💵 Narx: {row['price']}$"
        if lang == "uz" else
        f"🆔 {row['char_id']}\n👤 {row['name']}\n📺 {row['anime']}\n{rarity_label(row['rarity'])}\n\n"
        f"💵 Price: {row['price']}$"
    )
    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("💰 Sotib olish" if lang == "uz" else "💰 Buy", callback_data=f"shop_buy_{cid}"),
            InlineKeyboardButton("🔙 Boshqa tanlash" if lang == "uz" else "🔙 Choose another", callback_data="shop_back"),
        ]]
    )
    await context.bot.send_photo(chat_id=query.from_user.id, photo=row["file_id"], caption=caption, reply_markup=kb)


async def cb_shop_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await get_lang(update)
    cid = int(query.data.replace("shop_buy_", ""))
    user_id = query.from_user.id
    ensure_user(user_id, query.from_user.username, query.from_user.first_name)

    with db() as conn:
        row = conn.execute(
            "SELECT s.price, c.name, c.anime FROM shop s JOIN characters c ON s.char_id=c.char_id WHERE s.char_id=?",
            (cid,),
        ).fetchone()
        if not row:
            await query.answer("Bu character endi shopda yo'q." if lang == "uz" else "No longer in shop.", show_alert=True)
            return

        u = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
        if (u["balance"] or 0) < row["price"]:
            await query.answer(
                "❌ Mablag' yetarli emas." if lang == "uz" else "❌ Insufficient balance.", show_alert=True
            )
            return

        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (row["price"], user_id))
        conn.execute(
            "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,0)",
            (user_id, cid, time.time()),
        )

    await check_collection_titles(user_id, row["anime"])
    await query.answer("✅ Muvaffaqiyatli sotib olindi!" if lang == "uz" else "✅ Purchase successful!", show_alert=True)


async def cb_shop_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()


async def cmd_shopadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shopadd <char_id> <narx> — faqat admin."""
    user = update.effective_user
    lang = await get_lang(update)
    if not is_admin_user(user.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Foydalanish: /shopadd <char_id> <narx>")
        return
    try:
        cid = int(context.args[0])
        price = int(context.args[1])
    except ValueError:
        await update.message.reply_text("char_id va narx raqam bo'lishi kerak.")
        return

    with db() as conn:
        char = conn.execute("SELECT * FROM characters WHERE char_id=?", (cid,)).fetchone()
        if not char:
            await update.message.reply_text(f"ID {cid} topilmadi.")
            return
        conn.execute(
            "INSERT INTO shop (char_id, price) VALUES (?,?) ON CONFLICT(char_id) DO UPDATE SET price=excluded.price",
            (cid, price),
        )
    await update.message.reply_text(f"✅ {char['name']} shopga {price}$ narxda qo'shildi.")


async def cmd_shopremove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shopremove <char_id> — faqat admin."""
    user = update.effective_user
    if not is_admin_user(user.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /shopremove <char_id>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("char_id raqam bo'lishi kerak.")
        return
    with db() as conn:
        conn.execute("DELETE FROM shop WHERE char_id=?", (cid,))
    await update.message.reply_text(f"🗑 ID {cid} shopdan olib tashlandi.")


# =========================================================
#                  ADMIN BUYRUQLARI
# =========================================================
def _get_reply_target(update: Update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


async def cmd_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.effective_user
    if not is_admin_user(admin.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    target = _get_reply_target(update)
    if not target or not context.args:
        await update.message.reply_text("Foydalanish: userga reply qilib /give <miqdor>")
        return
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Miqdor raqam bo'lishi kerak.")
        return

    ensure_user(target.id, target.username, target.first_name)
    with db() as conn:
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, target.id))
    await update.message.reply_text(f"✅ {target.first_name}ga {amount}$ qo'shildi.")


async def cmd_removem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.effective_user
    if not is_admin_user(admin.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    target = _get_reply_target(update)
    if not target or not context.args:
        await update.message.reply_text("Foydalanish: userga reply qilib /removem <miqdor>")
        return
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Miqdor raqam bo'lishi kerak.")
        return

    ensure_user(target.id, target.username, target.first_name)
    with db() as conn:
        conn.execute("UPDATE users SET balance=MAX(0, balance-?) WHERE user_id=?", (amount, target.id))
    await update.message.reply_text(f"✅ {target.first_name}dan {amount}$ ayirildi.")


async def cmd_removch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.effective_user
    if not is_admin_user(admin.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    target = _get_reply_target(update)
    if not target or not context.args:
        await update.message.reply_text("Foydalanish: userga reply qilib /removch <character_id>")
        return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("character_id raqam bo'lishi kerak.")
        return

    with db() as conn:
        row = conn.execute(
            "SELECT id FROM harem WHERE user_id=? AND char_id=? LIMIT 1", (target.id, cid)
        ).fetchone()
        if not row:
            await update.message.reply_text("Bu userda bu character yo'q.")
            return
        conn.execute("DELETE FROM harem WHERE id=?", (row["id"],))
    await update.message.reply_text(f"✅ ID {cid} {target.first_name}ning haremidan olib tashlandi.")


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.effective_user
    if not is_admin_user(admin.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    target = _get_reply_target(update)
    if not target:
        await update.message.reply_text("Userga reply qilib /ban yozing.")
        return
    ensure_user(target.id, target.username, target.first_name)
    with db() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target.id,))
    await update.message.reply_text(f"🚫 {target.first_name} ban qilindi.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.effective_user
    if not is_admin_user(admin.id):
        await update.message.reply_text("⛔️ Sizda ruxsat yo'q.")
        return
    if SUPPORT_GROUP_ID and update.effective_chat.id != SUPPORT_GROUP_ID:
        await update.message.reply_text("Bu buyruq faqat SUPPORT guruhda ishlaydi.")
        return
    target = _get_reply_target(update)
    if not target:
        await update.message.reply_text("Userga reply qilib /unban yozing.")
        return
    with db() as conn:
        conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target.id,))
    await update.message.reply_text(f"✅ {target.first_name} unban qilindi.")


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Faqat bot egasi (OWNER_ID) yangi admin qo'sha oladi."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔️ Bu buyruq faqat bot egasi uchun.")
        return
    target = _get_reply_target(update)
    if not target:
        await update.message.reply_text("Userga reply qilib /addadmin yozing.")
        return
    ensure_user(target.id, target.username, target.first_name)
    with db() as conn:
        conn.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (target.id,))
    await update.message.reply_text(f"✅ {target.first_name} endi admin.")


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔️ Bu buyruq faqat bot egasi uchun.")
        return
    target = _get_reply_target(update)
    if not target:
        await update.message.reply_text("Userga reply qilib /removeadmin yozing.")
        return
    with db() as conn:
        conn.execute("UPDATE users SET is_admin=0 WHERE user_id=?", (target.id,))
    await update.message.reply_text(f"✅ {target.first_name}ning admin huquqi olib tashlandi.")


# =========================================================
#            /top, /ctop, /topgroups, /whmode, /changetime
# =========================================================
async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT u.user_id, u.username, u.first_name, COUNT(h.id) as total
            FROM users u JOIN harem h ON u.user_id=h.user_id
            GROUP BY u.user_id ORDER BY total DESC LIMIT 10
            """
        ).fetchall()

    if not rows:
        await update.message.reply_text("Hozircha ma'lumot yo'q." if lang == "uz" else "No data yet.")
        return

    title = "🏆 Global TOP foydalanuvchilar:\n" if lang == "uz" else "🏆 Global TOP users:\n"
    lines = [title]
    for i, r in enumerate(rows, 1):
        name = f"@{r['username']}" if r["username"] else r["first_name"]
        lines.append(f"{i}. {name} — {r['total']} ta character")
    await update.message.reply_text("\n".join(lines))


async def cmd_ctop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    chat = update.effective_chat
    with db() as conn:
        rows = conn.execute(
            """
            SELECT u.username, u.first_name, COUNT(h.id) as total
            FROM harem h JOIN users u ON h.user_id=u.user_id
            WHERE h.obtained_chat_id=?
            GROUP BY h.user_id ORDER BY total DESC LIMIT 10
            """,
            (chat.id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text("Bu guruhda hali ma'lumot yo'q." if lang == "uz" else "No data in this chat yet.")
        return

    title = "🏆 Shu guruhning TOPi:\n" if lang == "uz" else "🏆 This chat's TOP:\n"
    lines = [title]
    for i, r in enumerate(rows, 1):
        name = f"@{r['username']}" if r["username"] else r["first_name"]
        lines.append(f"{i}. {name} — {r['total']} ta character")
    await update.message.reply_text("\n".join(lines))


async def cmd_topgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update)
    with db() as conn:
        rows = conn.execute(
            "SELECT title, catches_count FROM chats ORDER BY catches_count DESC LIMIT 10"
        ).fetchall()

    if not rows:
        await update.message.reply_text("Hozircha ma'lumot yo'q." if lang == "uz" else "No data yet.")
        return

    title = "🏆 Eng faol guruhlar:\n" if lang == "uz" else "🏆 Most active groups:\n"
    lines = [title]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['title'] or '—'} — {r['catches_count']} ta tutilgan")
    await update.message.reply_text("\n".join(lines))


async def cmd_whmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Harem ko'rinishini list <-> grouped(rarity) rejimlari orasida almashtiradi."""
    user = update.effective_user
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)
    u = get_user(user.id)
    new_mode = "grouped" if (u["harem_mode"] or "list") == "list" else "list"
    with db() as conn:
        conn.execute("UPDATE users SET harem_mode=? WHERE user_id=?", (new_mode, user.id))

    if lang == "uz":
        text = "✅ Harem ko'rinishi endi: Rarity bo'yicha guruhlangan" if new_mode == "grouped" else "✅ Harem ko'rinishi endi: Oddiy ro'yxat"
    else:
        text = f"✅ Harem view is now: {'Grouped by rarity' if new_mode=='grouped' else 'Simple list'}"
    await update.message.reply_text(text)


async def cmd_changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh adminlari spawn oralig'ini (necha xabardan keyin) o'zgartira oladi."""
    chat = update.effective_chat
    user = update.effective_user
    lang = await get_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("Bu buyruq faqat guruhda ishlaydi." if lang == "uz" else "This only works in groups.")
        return

    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator") and not is_admin_user(user.id):
        await update.message.reply_text("⛔️ Faqat guruh adminlari o'zgartira oladi." if lang == "uz" else "⛔️ Only group admins can change this.")
        return

    if not context.args:
        c = get_chat_row(chat.id)
        current = c["spawn_threshold"] if c else SPAWN_THRESHOLD_DEFAULT
        await update.message.reply_text(
            f"Joriy qiymat: har {current} xabardan keyin. O'zgartirish uchun: /changetime <son>"
            if lang == "uz" else
            f"Current value: every {current} messages. To change: /changetime <number>"
        )
        return

    try:
        new_val = int(context.args[0])
        if new_val < 10:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Kamida 10 bo'lishi kerak." if lang == "uz" else "Must be at least 10.")
        return

    ensure_chat(chat.id, chat.title)
    with db() as conn:
        conn.execute("UPDATE chats SET spawn_threshold=? WHERE chat_id=?", (new_val, chat.id))
    await update.message.reply_text(
        f"✅ Endi har {new_val} xabardan keyin character chiqadi." if lang == "uz"
        else f"✅ A character will now spawn every {new_val} messages."
    )


# =========================================================
#                     BOSS RAID
# =========================================================
VILLAIN_NAMES = [
    "Shadow Reaper", "Void Empress", "Crimson Tyrant", "Abyssal King",
    "Nightmare Lord", "Frost Widow", "Inferno Beast", "Chaos Serpent",
]


def get_boss_row():
    with db() as conn:
        row = conn.execute("SELECT * FROM boss_raid WHERE id=1").fetchone()
        if not row:
            conn.execute("INSERT INTO boss_raid (id, hp, max_hp, active) VALUES (1,0,?,0)", (BOSS_MAX_HP,))
            row = conn.execute("SELECT * FROM boss_raid WHERE id=1").fetchone()
        return row


async def distribute_boss_rewards(context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        ranking = conn.execute(
            "SELECT user_id, damage FROM boss_damage ORDER BY damage DESC"
        ).fetchall()

    if not ranking:
        with db() as conn:
            conn.execute("UPDATE boss_raid SET active=0 WHERE id=1")
        return

    lines = ["🏆 Boss Raid yakunlandi! Natijalar:\n"]
    with db() as conn:
        for i, r in enumerate(ranking, 1):
            uid = r["user_id"]
            if i in BOSS_REWARDS:
                reward = BOSS_REWARDS[i]
                conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (reward["money"], uid))
                char = pick_random_character_by_rarity(reward["rarity"])
                extra = ""
                if char:
                    conn.execute(
                        "INSERT INTO harem (user_id, char_id, obtained_at, obtained_chat_id) VALUES (?,?,?,?)",
                        (uid, char["char_id"], time.time(), SUPPORT_GROUP_ID),
                    )
                    extra = f" + {char['name']} ({reward['rarity']})"
                if i == 1:
                    conn.execute("UPDATE users SET boss_top1_count=boss_top1_count+1 WHERE user_id=?", (uid,))
                lines.append(f"{i}. {r['damage']} zarar — {reward['money']}$" + extra)
            elif i <= 10:
                conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (BOSS_REWARD_4_10, uid))
                lines.append(f"{i}. {r['damage']} zarar — {BOSS_REWARD_4_10}$")
            else:
                conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (BOSS_REWARD_REST, uid))

        conn.execute("DELETE FROM boss_damage")
        conn.execute("UPDATE boss_raid SET active=0, hp=0 WHERE id=1")

    if len(ranking) > 10:
        lines.append(f"...va yana {len(ranking)-10} ta qatnashchiga 500$ dan berildi.")

    if SUPPORT_GROUP_ID:
        try:
            await context.bot.send_message(SUPPORT_GROUP_ID, "\n".join(lines))
        except Exception as e:
            logger.warning(f"Boss reward xabarini yubora olmadim: {e}")


async def job_spawn_boss(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni 21:00 (UZB) da ishlaydi: eskisini yakunlaydi, yangisini chiqaradi."""
    if not SUPPORT_GROUP_ID:
        return

    boss = get_boss_row()
    if boss["active"]:
        await distribute_boss_rewards(context)

    villain = random.choice(VILLAIN_NAMES)
    with db() as conn:
        conn.execute(
            "UPDATE boss_raid SET hp=?, max_hp=?, active=1, spawned_at=? WHERE id=1",
            (BOSS_MAX_HP, BOSS_MAX_HP, time.time()),
        )
        conn.execute("DELETE FROM boss_damage")

    context.bot_data["current_villain_name"] = villain
    try:
        await context.bot.send_message(
            SUPPORT_GROUP_ID,
            f"👹 YANGI BOSS PAYDO BO'LDI: {villain}!\n"
            f"❤️ HP: {BOSS_MAX_HP}\n\n"
            f"Zarba berish uchun /damage yozing. Eng ko'p zarar bergan g'olib bo'ladi!",
        )
    except Exception as e:
        logger.warning(f"Boss e'lonini yubora olmadim: {e}")


async def cmd_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang = await get_lang(update)
    ensure_user(user.id, user.username, user.first_name)

    if is_banned_user(user.id):
        return
    if SUPPORT_GROUP_ID and chat.id != SUPPORT_GROUP_ID:
        await update.message.reply_text(T(lang, "claim_wrong_chat"))
        return

    boss = get_boss_row()
    if not boss["active"] or boss["hp"] <= 0:
        await update.message.reply_text("👹 Hozircha faol boss yo'q." if lang == "uz" else "👹 There's no active boss right now.")
        return

    u = get_user(user.id)
    now = time.time()
    if now - (u["last_damage_time"] or 0) < BOSS_DAMAGE_COOLDOWN:
        remaining = int(BOSS_DAMAGE_COOLDOWN - (now - u["last_damage_time"]))
        text = f"⏳ Yana {remaining} soniyadan keyin urinib ko'ring." if lang == "uz" else f"⏳ Try again in {remaining}s."
        await update.message.reply_text(text)
        return

    dmg = random.randint(BOSS_MIN_DAMAGE, BOSS_MAX_DAMAGE)
    with db() as conn:
        conn.execute("UPDATE users SET last_damage_time=? WHERE user_id=?", (now, user.id))
        conn.execute(
            "INSERT INTO boss_damage (user_id, damage) VALUES (?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET damage=damage+excluded.damage",
            (user.id, dmg),
        )
        conn.execute("UPDATE boss_raid SET hp=MAX(0, hp-?) WHERE id=1", (dmg,))
        new_hp = conn.execute("SELECT hp FROM boss_raid WHERE id=1").fetchone()["hp"]

    villain = context.bot_data.get("current_villain_name", "Boss")
    if lang == "uz":
        text = f"⚔️ Siz {villain}ga {dmg} zarar berdingiz!\n❤️ Qolgan HP: {new_hp}/{BOSS_MAX_HP}"
    else:
        text = f"⚔️ You dealt {dmg} damage to {villain}!\n❤️ Remaining HP: {new_hp}/{BOSS_MAX_HP}"
    await update.message.reply_text(text)

    if new_hp <= 0:
        await update.message.reply_text(
            f"💀 {villain} yengildi! Mukofotlar tarqatilmoqda..." if lang == "uz"
            else f"💀 {villain} has been defeated! Distributing rewards..."
        )
        await distribute_boss_rewards(context)


# =========================================================
#          SHAXSIY CHAT XABAR ROUTERI (/plus, /trade)
# =========================================================
async def private_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shaxsiy chatdagi oddiy xabarlarni /plus va /trade jarayonlariga yo'naltiradi."""
    if update.effective_chat.type != ChatType.PRIVATE:
        return

    if "plus" in context.user_data:
        await handle_plus_flow(update, context)
        return

    handled = await handle_trade_price_input(update, context)
    if handled:
        return


# =========================================================
#                        MAIN
# =========================================================
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # --- asosiy / til ---
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_chat_members))
    app.add_handler(CallbackQueryHandler(cb_lang_choice, pattern=r"^lang_(uz|en)$"))
    app.add_handler(CallbackQueryHandler(cb_menu_help, pattern=r"^menu_help$"))
    app.add_handler(CallbackQueryHandler(cb_menu_back, pattern=r"^menu_back$"))

    # --- character qo'shish ---
    app.add_handler(CommandHandler("plus", cmd_plus))
    app.add_handler(CommandHandler("okid", cmd_okid))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(cb_plus_rarity, pattern=r"^plus_rarity_"))

    # --- o'yin ---
    app.add_handler(CommandHandler("claim", cmd_claim))
    app.add_handler(CommandHandler("ball", cmd_ball))
    app.add_handler(CommandHandler("guess", cmd_guess))
    app.add_handler(CommandHandler("damage", cmd_damage))

    # --- to'plam / statistika ---
    app.add_handler(CommandHandler("harem", cmd_harem))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("wchar", cmd_wchar))
    app.add_handler(CommandHandler("wduplicate", cmd_wduplicate))
    app.add_handler(CommandHandler("wrarity", cmd_wrarity))
    app.add_handler(CommandHandler("wanimelist", cmd_wanimelist))
    app.add_handler(CommandHandler("find", cmd_find))
    app.add_handler(CommandHandler("wfind", cmd_wfind))
    app.add_handler(CommandHandler("fav", cmd_fav))
    app.add_handler(CommandHandler("wfav", cmd_wfav))
    app.add_handler(CommandHandler("whfav", cmd_whfav))
    app.add_handler(CommandHandler("whmode", cmd_whmode))
    app.add_handler(CommandHandler("changetime", cmd_changetime))

    # --- pul / sovg'a / savdo ---
    app.add_handler(CommandHandler("wsend", cmd_wsend))
    app.add_handler(CommandHandler("gift", cmd_gift))
    app.add_handler(CommandHandler("trade", cmd_trade))
    app.add_handler(CallbackQueryHandler(cb_trade_confirm, pattern=r"^trade_(yes|no)_\d+$"))

    # --- shop ---
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("shopadd", cmd_shopadd))
    app.add_handler(CommandHandler("shopremove", cmd_shopremove))
    app.add_handler(CallbackQueryHandler(cb_shop_view, pattern=r"^shop_view_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_shop_buy, pattern=r"^shop_buy_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_shop_back, pattern=r"^shop_back$"))

    # --- reytinglar ---
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("ctop", cmd_ctop))
    app.add_handler(CommandHandler("topgroups", cmd_topgroups))

    # --- admin ---
    app.add_handler(CommandHandler("give", cmd_give))
    app.add_handler(CommandHandler("removem", cmd_removem))
    app.add_handler(CommandHandler("removch", cmd_removch))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))

    # --- shaxsiy chat: /plus va /trade uchun umumiy router (matn + rasm) ---
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.TEXT | filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND,
        private_message_router,
    ))

    # --- guruh faolligi: spawn hisoblagichi + anti-spam (eng oxirida, past ustuvorlik) ---
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL, group_activity_tracker), group=1)

    # --- JobQueue: kunlik boss spawn (21:00 UZB = UTC+5) va savdo muddati tekshiruvi ---
    from datetime import time as dtime, timezone, timedelta
    uzb_tz = timezone(timedelta(hours=5))
    app.job_queue.run_daily(job_spawn_boss, time=dtime(hour=BOSS_SPAWN_HOUR_UZB, minute=0, tzinfo=uzb_tz))
    app.job_queue.run_repeating(job_expire_trades, interval=600, first=60)

    logger.info("Catch Your Waifu Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
