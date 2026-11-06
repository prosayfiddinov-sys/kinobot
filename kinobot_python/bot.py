import os, random, logging, html
from pathlib import Path
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

BASE = Path(__file__).parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
MOVIE_CHANNEL = os.getenv("MOVIE_CHANNEL", "").strip()
PUBLIC_CHANNELS = [x.strip() for x in os.getenv("REQUIRED_CHANNELS", "").split(",") if x.strip()]
SUPPORT = os.getenv("SUPPORT_USERNAME", "").lstrip("@")
WELCOME_PHOTO = os.getenv("WELCOME_PHOTO", "").strip()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kinobot")

def safe_dir(kind: str, code: str) -> Path:
    if kind not in ("kino", "multfilm") or not code.isdigit():
        raise ValueError("Noto'g'ri kino kodi")
    return DATA / kind / code

def all_movies():
    items = []
    for kind in ("kino", "multfilm"):
        folder = DATA / kind
        if folder.exists():
            for p in folder.iterdir():
                if p.is_dir() and (p / "film.txt").exists():
                    items.append((kind, p.name, p))
    return items

def read(p: Path, default=""):
    try: return p.read_text(encoding="utf-8")
    except (OSError, UnicodeError): return default

def write(p: Path, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(value), encoding="utf-8")

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Kod orqali yuklash", callback_data="code")],
        [InlineKeyboardButton("🔥 Top 10", callback_data="top10"), InlineKeyboardButton("🎲 Tasodifiy kino", callback_data="random")],
        [InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about")],
    ])

def admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📥 Film yuklash"), KeyboardButton("🗑 Film o‘chirish")],
        [KeyboardButton("✉ Xabarnoma"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("📢 Kanallar"), KeyboardButton("⚙ Sozlamalar")],
        [KeyboardButton("◀️ Menyu")]
    ], resize_keyboard=True)

def is_admin(uid):
    return uid in ADMIN_IDS

async def joined(context, uid):
    for channel in PUBLIC_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, uid)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True

async def require_join(update, context):
    uid = update.effective_user.id
    if await joined(context, uid):
        return True
    rows = [[InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{c.lstrip('@')}")] for c in PUBLIC_CHANNELS]
    rows.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_join")])
    text = "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:"
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows))
    else:
        await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows))
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_join(update, context): return
    user = update.effective_user
    context.user_data.clear()
    # Deep-link orqali /start KOD yoki /start mfKOD
    if context.args:
        payload = context.args[0]
        kind = "multfilm" if payload.startswith("mf") else "kino"
        code = payload[2:] if kind == "multfilm" else payload
        if code.isdigit():
            await send_movie(update.effective_chat.id, kind, code, context)
            return
    text = (f"👋 Assalomu alaykum, {html.escape(user.first_name or '')}!\n\n"
            "📽 Bu bot orqali kino va multfilmlarni kod orqali yuklab olishingiz mumkin.")
    if WELCOME_PHOTO:
        await update.message.reply_photo(WELCOME_PHOTO, caption=text, reply_markup=main_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=main_keyboard())
    if is_admin(user.id):
        await update.message.reply_text("🗄 Admin boshqaruv paneli", reply_markup=admin_keyboard())

async def begin_code(update, context):
    if not await require_join(update, context): return
    context.user_data["state"] = "get_code"
    await update.effective_message.reply_text("📥 Kino yoki multfilm kodini yuboring (faqat raqam).")

async def send_movie(chat_id, kind, code, context, as_video=False):
    folder = safe_dir(kind, code)
    film = read(folder / "film.txt")
    if not film:
        await context.bot.send_message(chat_id, "❌ Bu kod bo‘yicha kino topilmadi.")
        return
    count = int(read(folder / "downcount.txt", "0") or 0) + 1
    write(folder / "downcount.txt", count)
    name = read(folder / "nomi.txt", "Kino")
    genre = read(folder / "janr.txt", "Noma'lum")
    caption = f"🎬 <b>{html.escape(name)}</b>\n🎭 Janr: {html.escape(genre)}\n⬇️ Yuklanishlar: {count}"
    await context.bot.send_video(chat_id, film, caption=caption, parse_mode=ParseMode.HTML)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "check_join":
        if await joined(context, q.from_user.id):
            await q.message.reply_text("✅ Obuna tasdiqlandi.", reply_markup=main_keyboard())
        else:
            await require_join(update, context)
        return
    if data == "code":
        if await require_join(update, context):
            context.user_data["state"] = "get_code"
            await q.message.reply_text("📥 Kino yoki multfilm kodini yuboring (faqat raqam).")
    elif data == "about":
        await q.message.reply_text("ℹ️ Ushbu bot orqali kino va multfilmlarni kod bilan yuklab olishingiz mumkin.")
    elif data == "top10":
        items = all_movies()
        items.sort(key=lambda x: int(read(x[2] / "downcount.txt", "0") or 0), reverse=True)
        if not items:
            await q.message.reply_text("Hozircha kino mavjud emas.")
            return
        lines = ["🔥 <b>Top 10 eng ko‘p yuklangan</b>\n"]
        for i, (kind, code, folder) in enumerate(items[:10], 1):
            lines.append(f"{i}. {html.escape(read(folder/'nomi.txt','Kino'))} — kod: <code>{code}</code> — {read(folder/'downcount.txt','0')} ta")
        await q.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    elif data == "random":
        items = all_movies()
        if not items:
            await q.message.reply_text("Kino yoki multfilm topilmadi.")
            return
        kind, code, folder = random.choice(items)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Yuklab olish", callback_data=f"download|{kind}|{code}")]])
        await q.message.reply_text(f"🎲 {html.escape(read(folder/'nomi.txt','Kino'))}\nKod: {code}", reply_markup=kb)
    elif data.startswith("download|"):
        _, kind, code = data.split("|", 2)
        if await require_join(update, context):
            await send_movie(q.message.chat_id, kind, code, context)
    elif data == "menu":
        await q.message.reply_text("Asosiy menyu", reply_markup=main_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = update.effective_user.id
    text = (msg.text or "").strip()
    state = context.user_data.get("state")

    if text == "◀️ Menyu":
        context.user_data.clear()
        await msg.reply_text("Asosiy menyu", reply_markup=ReplyKeyboardRemove())
        await msg.reply_text("Kerakli bo‘limni tanlang:", reply_markup=main_keyboard())
        return

    if text == "📊 Statistika" and is_admin(uid):
        items = all_movies()
        users = read(DATA / "users.txt").splitlines()
        await msg.reply_text(f"📊 Statistika\n👥 Foydalanuvchilar: {len(set(users))}\n🎬 Filmlar: {len(items)}")
        return
    if text == "📢 Kanallar" and is_admin(uid):
        await msg.reply_text("Majburiy obuna kanallarini REQUIRED_CHANNELS muhit o‘zgaruvchisida vergul bilan ajrating.\nMasalan: @kanal1,@kanal2")
        return
    if text == "⚙ Sozlamalar" and is_admin(uid):
        await msg.reply_text(f"🎥 Kino kanali: {MOVIE_CHANNEL or 'sozlanmagan'}\n🛡 Admin ID: {', '.join(map(str, ADMIN_IDS)) or 'sozlanmagan'}")
        return
    if text == "📥 Film yuklash" and is_admin(uid):
        if not MOVIE_CHANNEL:
            await msg.reply_text("Avval .env faylida MOVIE_CHANNEL ni sozlang.")
            return
        context.user_data.clear()
        context.user_data["state"] = "upload_template"
        await msg.reply_text("Avval kanal postida ko‘rinadigan video shablonni yuboring.")
        return
    if text == "🗑 Film o‘chirish" and is_admin(uid):
        context.user_data["state"] = "delete_code"
        await msg.reply_text("O‘chiriladigan kino kodini yuboring.")
        return
    if text == "✉ Xabarnoma" and is_admin(uid):
        context.user_data["state"] = "broadcast"
        await msg.reply_text("Barcha bot foydalanuvchilariga yuboriladigan matnni jo‘nating.")
        return

    if state == "get_code":
        if not text.isdigit():
            await msg.reply_text("Kod faqat raqamlardan iborat bo‘lsin.")
            return
        context.user_data.clear()
        for kind in ("kino", "multfilm"):
            if (safe_dir(kind, text) / "film.txt").exists():
                if await require_join(update, context):
                    await send_movie(msg.chat_id, kind, text, context)
                return
        await msg.reply_text("❌ Bu kodga mos kino yoki multfilm topilmadi.")
        return

    if state == "delete_code" and is_admin(uid):
        deleted = False
        for kind in ("kino", "multfilm"):
            folder = safe_dir(kind, text)
            if folder.exists():
                import shutil
                shutil.rmtree(folder)
                deleted = True
        context.user_data.clear()
        await msg.reply_text("✅ O‘chirildi." if deleted else "❌ Kod topilmadi.", reply_markup=admin_keyboard())
        return

    if state == "broadcast" and is_admin(uid):
        users = sorted(set(read(DATA / "users.txt").splitlines()))
        sent = failed = 0
        for user_id in users:
            try:
                await context.bot.copy_message(int(user_id), msg.chat_id, msg.message_id)
                sent += 1
            except Exception:
                failed += 1
        context.user_data.clear()
        await msg.reply_text(f"Xabarnoma yakunlandi.\n✅ Yetkazildi: {sent}\n⚠️ Yetkazilmadi: {failed}", reply_markup=admin_keyboard())
        return

    if state in ("upload_template", "upload_film") and is_admin(uid):
        if not (msg.video or msg.document):
            await msg.reply_text("Iltimos, video yoki video fayl yuboring.")
            return
        file_id = msg.video.file_id if msg.video else msg.document.file_id
        if state == "upload_template":
            context.user_data["template"] = file_id
            context.user_data["state"] = "upload_film"
            await msg.reply_text("Endi asosiy kino faylini yuboring.")
        else:
            context.user_data["film"] = file_id
            context.user_data["state"] = "upload_caption"
            await msg.reply_text("Film nomi va tavsifini yuboring.")
        return

    if state == "upload_caption" and is_admin(uid):
        context.user_data["caption"] = text
        context.user_data["state"] = "upload_genre"
        buttons = [[InlineKeyboardButton(g, callback_data=f"genre|{g}")] for g in ["Dramma", "Komediya", "Jangari", "Qo‘rqinchli", "Romantik", "Fantastika", "Multfilm"]]
        await msg.reply_text("Janrni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if state == "upload_code" and is_admin(uid):
        if not text.isdigit():
            await msg.reply_text("Kod faqat raqam bo‘lishi kerak.")
            return
        kind = context.user_data.get("kind", "kino")
        folder = safe_dir(kind, text)
        if folder.exists():
            await msg.reply_text("Bu kod band. Boshqa kod kiriting.")
            return
        folder.mkdir(parents=True, exist_ok=True)
        write(folder/"film.txt", context.user_data["film"])
        write(folder/"template.txt", context.user_data["template"])
        write(folder/"nomi.txt", context.user_data["caption"])
        write(folder/"janr.txt", context.user_data["genre"])
        write(folder/"downcount.txt", "0")
        bot_info = await context.bot.get_me()
        post = f"🍿 <b>Yangi {'multfilm' if kind=='multfilm' else 'film'}</b>\n\n{html.escape(context.user_data['caption'])}\n\n🔢 Kod: <code>{text}</code>\n🎭 Janr: {html.escape(context.user_data['genre'])}"
        try:
            sent = await context.bot.send_video(MOVIE_CHANNEL, context.user_data["template"], caption=post, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Yuklab olish", url=f"https://t.me/{bot_info.username}?start={text if kind=='kino' else 'mf'+text}")]]))
            channel_link = f"https://t.me/{MOVIE_CHANNEL.lstrip('@')}/{sent.message_id}" if MOVIE_CHANNEL.startswith("@") else str(sent.message_id)
            await msg.reply_text(f"✅ Saqlandi va kanalga joylandi!\nKod: {text}\n{channel_link}", reply_markup=admin_keyboard())
        except Exception as e:
            log.exception("Channel publish failed")
            await msg.reply_text(f"Film bazaga saqlandi, ammo kanalga yuborishda xatolik: {e}", reply_markup=admin_keyboard())
        context.user_data.clear()
        return

    # Track unique users for broadcast list
    users = set(read(DATA / "users.txt").splitlines())
    users.add(str(uid))
    write(DATA / "users.txt", "\n".join(sorted(users)))
    if text.startswith("/"):
        return
    await msg.reply_text("Bot menyusidan foydalaning.", reply_markup=main_keyboard())

async def genre_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return
    if not q.data.startswith("genre|"): return
    genre = q.data.split("|", 1)[1]
    context.user_data["genre"] = genre
    context.user_data["kind"] = "multfilm" if genre == "Multfilm" else "kino"
    context.user_data["state"] = "upload_code"
    await q.message.reply_text(f"Janr: {genre}\nEndi yagona raqamli kod kiriting.")

async def error_handler(update, context):
    log.exception("Update processing error", exc_info=context.error)

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN kiritilmagan. .env.example faylidan .env yarating.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", lambda u,c: u.effective_message.reply_text("Admin panel", reply_markup=admin_keyboard()) if is_admin(u.effective_user.id) else None))
    app.add_handler(CallbackQueryHandler(genre_callback, pattern=r"^genre\|"))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    log.info("Kino bot ishga tushdi")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
