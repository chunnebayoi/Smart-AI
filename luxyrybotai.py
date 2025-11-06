#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Smart AI Assistant ⚜️ v4.5 (Final Stable)
# Developed by Giangg Sơnn ( Chun Chun ) – All Rights Reserved © 2025

import os, io, re, time, logging, tempfile, html
from datetime import datetime
from pathlib import Path

import pytz
from sympy import symbols, Eq, solve, simplify
from PIL import Image
import pytesseract
import requests

from deep_translator import GoogleTranslator
from newsapi import NewsApiClient
import yt_dlp

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from dotenv import load_dotenv

# ───────────────── CONFIG ─────────────────
load_dotenv()

TOKEN          = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
WEATHER_API_KEY= os.getenv("WEATHER_API_KEY")

OWNER_NAME     = os.getenv("OWNER_NAME", "Admin")
OWNER_EMAIL    = os.getenv("OWNER_EMAIL", "")
OWNER_ZALO     = os.getenv("OWNER_ZALO", "")
OWNER_TG       = os.getenv("OWNER_TELEGRAM", "")
OWNER_FB       = os.getenv("OWNER_FACEBOOK", "")
OWNER_PHOTO    = os.getenv("OWNER_PHOTO_URL", "")

BOT_TITLE      = "Smart AI Assistant ⚜️"
FOOTER         = "♟ Developed by Giangg Sơnn ( Chun Chun ) – All Rights Reserved © 2025"

ENABLE_GEMINI  = bool(GEMINI_API_KEY)
ENABLE_NEWS    = bool(NEWS_API_KEY)
ENABLE_WEATHER = bool(WEATHER_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("luxury_ai")

# ─────────── Gemini client (optional) ───────────
if ENABLE_GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    _gem_model = genai.GenerativeModel(GEMINI_MODEL)

def pretty_footer() -> str:
    return f"\n\n<em>{html.escape(FOOTER)}</em>"

# ─────────── UI: Luxury menu ───────────
def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("💬 Chat AI", callback_data="m_chat"),
         InlineKeyboardButton("📚 Giải bài", callback_data="m_solve")],
        [InlineKeyboardButton("🌐 Dịch", callback_data="m_translate"),
         InlineKeyboardButton("🖼 OCR+Dịch", callback_data="m_ocr")],
        [InlineKeyboardButton("🕒 Giờ quốc tế", callback_data="m_time"),
         InlineKeyboardButton("📰 News", callback_data="m_news")],
        [InlineKeyboardButton("🎵 TikTok", callback_data="m_tiktok"),
         InlineKeyboardButton("▶️ YouTube", callback_data="m_youtube")],
        [InlineKeyboardButton("📘 Facebook", callback_data="m_facebook"),
         InlineKeyboardButton("🌤 Weather", callback_data="m_weather")],
        [InlineKeyboardButton("₿ Crypto", callback_data="m_crypto")],
        [InlineKeyboardButton("👑 Admin Info", callback_data="m_admin")],
        [InlineKeyboardButton("🆘 Help", callback_data="m_help")]
    ]
    return InlineKeyboardMarkup(rows)

def send_menu_text() -> str:
    lines = [
        f"<b>{html.escape(BOT_TITLE)}</b>",
        "Được phát triển bởi <b>Giangg Sơnn ( Chun Chun )</b> — phong cách sang trọng & trí tuệ đỉnh cao.",
        "Hỗ trợ học tập, làm việc, tra cứu, giải trí và sáng tạo — mọi lúc, mọi nơi.",
        "",
        "Chọn menu bên dưới hoặc gõ <code>/help</code> để xem lệnh chi tiết.",
        pretty_footer()
    ]
    return "\n".join(lines)

# ─────────── Helpers ───────────
def sanitize_url(u: str) -> str:
    return u.strip().strip("<>").strip()

def resolve_redirect(url: str, timeout=20) -> str:
    try:
        r = requests.get(url, allow_redirects=True, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        return r.url
    except Exception:
        return url

async def inc_user_cmd(update: Update) -> None:
    try:
        chat = update.effective_chat
        log.info("cmd from %s (%s)", chat.id, chat.username)
    except Exception:
        pass

# ─────────── Start / Menu / Help ───────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await inc_user_cmd(update)
    await update.message.reply_text(send_menu_text(), parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=main_menu())

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⬇️ Menu chức năng:", reply_markup=main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "<b>Hướng dẫn nhanh</b>\n"
        "• /ai &lt;câu hỏi&gt;\n"
        "• /solve &lt;biểu thức/toán&gt;\n"
        "• /translate &lt;text&gt;\n"
        "• /ocr (reply ảnh)\n"
        "• /time &lt;city/country&gt;\n"
        "• /news &lt;từ khóa&gt; | /newstext &lt;từ khóa&gt;\n"
        "• /weather &lt;city&gt;\n"
        "• /youtube &lt;link&gt;  |  /tiktok &lt;link&gt;  |  /facebook &lt;link&gt;\n"
        "• /crypto &lt;symbol&gt; (vd: btc, eth)\n"
        + pretty_footer()
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# ─────────── Admin card ───────────
async def admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE, send_menu=False):
    chat = update.effective_chat
    caption = (
        "<b>👑 Thông tin Admin</b>\n"
        f"• Tên: <b>{html.escape(OWNER_NAME)}</b>\n"
        + (f"• Email: <code>{html.escape(OWNER_EMAIL)}</code>\n" if OWNER_EMAIL else "")
        + (f"• Zalo: {html.escape(OWNER_ZALO)}\n" if OWNER_ZALO else "")
        + (f"• Telegram: {html.escape(OWNER_TG)}\n" if OWNER_TG else "")
        + (f"• Facebook: <a href=\"{html.escape(OWNER_FB)}\">{html.escape(OWNER_FB)}</a>\n" if OWNER_FB else "")
        + pretty_footer()
    )
    try:
        if OWNER_PHOTO:
            img = requests.get(OWNER_PHOTO, timeout=10).content
            await chat.send_photo(photo=io.BytesIO(img), caption=caption, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
        else:
            await chat.send_message(caption, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    except Exception as e:
        await chat.send_message(f"Không thể gửi ảnh admin. {e}")

    if send_menu:
        await chat.send_message("⬇️ Menu chức năng:", reply_markup=main_menu())

async def admin_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await admin_info(q, context)

# ─────────── AI / Solve / Translate / OCR ───────────
def gemini_answer(prompt: str) -> str:
    if not ENABLE_GEMINI:
        return "❌ Gemini chưa được bật (thiếu GEMINI_API_KEY)."
    try:
        resp = _gem_model.generate_content(prompt)
        txt = resp.text or ""
        return txt.strip() or "AI không trả lời."
    except Exception as e:
        return f"Gemini error: {e}"

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await inc_user_cmd(update)
    if not context.args:
        return await update.message.reply_text("Usage: /ai <câu hỏi>")
    q = " ".join(context.args).strip()
    await update.message.chat.send_action(ChatAction.TYPING)
    ans = gemini_answer(q)
    await update.message.reply_text(html.escape(ans) + pretty_footer(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def solve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /solve 2*x+3=7  hoặc  /solve 2*x^2+3*x-2")
    expr = " ".join(context.args)
    try:
        x = symbols("x")
        if "=" in expr:
            left, right = expr.split("=", 1)
            res = solve(Eq(simplify(left), simplify(right)))
        else:
            res = simplify(expr)
        text = f"Kết quả:\n{res}"
    except Exception as e:
        text = f"❌ Lỗi giải toán: {e}"
    await update.message.reply_text(html.escape(text) + pretty_footer(), parse_mode=ParseMode.HTML)

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /translate <văn bản>")
    src = " ".join(context.args)
    try:
        vi = GoogleTranslator(source="auto", target="vi").translate(src)
        text = f"📝 Gốc:\n{src}\n\n🇻🇳 Dịch:\n{vi}"
    except Exception as e:
        text = f"❌ Lỗi dịch: {e}"
    await update.message.reply_text(html.escape(text) + pretty_footer(), parse_mode=ParseMode.HTML)

async def ocr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not (msg.reply_to_message.photo or msg.reply_to_message.document):
        return await msg.reply_text("Hãy reply vào <b>một ảnh</b> rồi gõ /ocr", parse_mode=ParseMode.HTML)
    try:
        if msg.reply_to_message.photo:
            file = await msg.reply_to_message.photo[-1].get_file()
        else:
            file = await msg.reply_to_message.document.get_file()
        b = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(b))
        text = pytesseract.image_to_string(img, lang="eng+vie")
        vi = GoogleTranslator(source="auto", target="vi").translate(text) if text.strip() else ""
        out = "📄 OCR:\n" + (text or "(trống)") + ("\n\n🇻🇳 Dịch:\n" + vi if vi else "")
        await msg.reply_text(html.escape(out) + pretty_footer(), parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Lỗi OCR: {e}")

# ─────────── Time / Weather / News / Crypto ───────────
async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /time <city/country> (vd: tokyo, việt nam, mỹ)")

    q = " ".join(context.args).strip().lower()

    tz_map = {
        "vietnam": "Asia/Bangkok", "việt nam": "Asia/Bangkok", "hanoi": "Asia/Bangkok", "sài gòn": "Asia/Bangkok",
        "my": "America/New_York", "mỹ": "America/New_York", "usa": "America/New_York", "new york": "America/New_York",
        "tokyo": "Asia/Tokyo", "nhật": "Asia/Tokyo", "japan": "Asia/Tokyo",
        "hàn": "Asia/Seoul", "korea": "Asia/Seoul",
        "trung": "Asia/Shanghai", "china": "Asia/Shanghai",
        "pháp": "Europe/Paris", "paris": "Europe/Paris",
        "anh": "Europe/London", "london": "Europe/London",
        "đức": "Europe/Berlin", "germany": "Europe/Berlin",
        "thái": "Asia/Bangkok", "thailand": "Asia/Bangkok",
        "singapore": "Asia/Singapore", "indonesia": "Asia/Jakarta",
        "dubai": "Asia/Dubai", "úc": "Australia/Sydney", "australia": "Australia/Sydney"
    }

    tz = tz_map.get(q)
    if not tz:
        # fallback: đoán theo từ khóa
        for k, v in tz_map.items():
            if k in q:
                tz = v
                break

    if not tz:
        return await update.message.reply_text("❌ Không tìm thấy timezone. Ví dụ: /time tokyo, /time việt nam")

    now = datetime.now(pytz.timezone(tz))
    text = f"🕒 Giờ hiện tại ở {q.title()}:\n<b>{now:%Y-%m-%d %H:%M:%S}</b>\n({tz})"
    await update.message.reply_text(text + pretty_footer(), parse_mode=ParseMode.HTML)

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ENABLE_WEATHER:
        return await update.message.reply_text("❌ Chưa có WEATHER_API_KEY")
    if not context.args:
        return await update.message.reply_text("Usage: /weather <city>")
    city = " ".join(context.args).strip()
    try:
        r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                         params={"q": city, "appid": WEATHER_API_KEY, "units":"metric", "lang":"vi"},
                         timeout=15)
        j = r.json()
        if j.get("cod") != 200:
            raise Exception(j.get("message"))
        main = j["main"]; wind = j.get("wind",{})
        desc = j["weather"][0]["description"].capitalize()
        text = (f"🌤 Thời tiết {city.title()}\n"
                f"🌡 Nhiệt độ: {main['temp']}°C (cảm giác {main.get('feels_like','?')}°C)\n"
                f"💧 Ẩm: {main.get('humidity','?')}%\n"
                f"💨 Gió: {wind.get('speed','?')} m/s\n"
                f"☁️ Mô tả: {desc}")
    except Exception as e:
        text = f"❌ Weather error: {e}"
    await update.message.reply_text(html.escape(text) + pretty_footer(), parse_mode=ParseMode.HTML)

async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ENABLE_NEWS:
        return await update.message.reply_text("❌ Chưa có NEWS_API_KEY")
    q = " ".join(context.args).strip() or "technology"
    try:
        client = NewsApiClient(api_key=NEWS_API_KEY)
        res = client.get_everything(q=q, language="vi", sort_by="publishedAt", page_size=5)
        items = res.get("articles", [])
        if not items:
            raise Exception("Không có tin phù hợp.")
        lines = ["📰 <b>Tin tức</b>"]
        for a in items:
            title = a.get("title") or "(không tiêu đề)"
            url = a.get("url") or ""
            lines.append(f"• <a href='{html.escape(url)}'>{html.escape(title)}</a>")
        text = "\n".join(lines) + pretty_footer()
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    except Exception as e:
        await update.message.reply_text(f"❌ News error: {e}")

async def crypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /crypto <mã coin>\nVí dụ: /crypto btc, /crypto eth, /crypto doge")

    sym = context.args[0].lower()
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": sym, "vs_currencies": "usd"},
            timeout=10
        )
        j = r.json()
        if sym not in j:
            raise Exception("Không tìm thấy coin hoặc ký hiệu không đúng.")
        price = j[sym]["usd"]
        text = f"💰 {sym.upper()} hiện tại = ${price:,}"
    except Exception as e:
        text = f"❌ Lỗi lấy giá coin: {e}"
    await update.message.reply_text(html.escape(text) + pretty_footer(), parse_mode=ParseMode.HTML)

# ─────────── Media: YouTube / TikTok / Facebook ───────────
async def youtube_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /youtube <link>")
    url = sanitize_url(context.args[0])
    await update.message.reply_text("⏳ Đang xử lý YouTube...")
    ydl_opts = {
        "format": "mp4[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": "%(title).80s.%(ext)s",
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            fn = ydl.prepare_filename(info)
            with tempfile.TemporaryDirectory() as td:
                ydl.params["outtmpl"] = str(Path(td)/"%(title).80s.%(ext)s")
                info = ydl.extract_info(url, download=True)
                fn = ydl.prepare_filename(info)
                with open(fn, "rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=f"▶️ {html.escape(info.get('title','YouTube'))}\n{pretty_footer()}",
                        parse_mode=ParseMode.HTML
                    )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi tải YouTube: {e}")

def tiktok_direct_link(url: str) -> str|None:
    try:
        url = resolve_redirect(url)
        # Một số CDN của TikTok có thể phát trực tiếp HLS/MP4 công khai:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        m = re.search(r'"downloadAddr":"([^"]+)"', r.text)
        if m:
            return m.group(1).encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return None

async def tiktok_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /tiktok <link>")
    link = sanitize_url(context.args[0])
    await update.message.reply_text("🔎 Đang kiểm tra link TikTok (resolve redirect)...")
    try:
        dl = tiktok_direct_link(link)
        if not dl:
            return await update.message.reply_text(
                "❗ Không lấy được link trực tiếp (có thể bị chặn theo vùng). Thử các trang:\n"
                "• https://snaptik.app\n• https://ssstik.io\n• https://tikwm.com"
            )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"tiktok.mp4"
            with requests.get(dl, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for chunk in r.iter_content(1<<14):
                        if chunk: f.write(chunk)
            if p.exists() and p.stat().st_size < 48*1024*1024:
                with open(p, "rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=f"🎵 TikTok\n{pretty_footer()}",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await update.message.reply_text("❗ File > 48MB. Hãy tải thủ công qua snaptik/ssstik.")
    except Exception as e:
        await update.message.reply_text(f"❌ TikTok error: {e}")

def facebook_direct_link(url: str) -> str|None:
    try:
        url = resolve_redirect(url)
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        m = re.search(r'"browser_native_format_url":"([^"]+)"', r.text)
        if m:
            return m.group(1).encode("utf-8").decode("unicode_escape")
        m = re.search(r'"playable_url":"([^"]+)"', r.text)
        if m:
            return m.group(1).encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return None

async def facebook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /facebook <link>")
    link = sanitize_url(context.args[0])
    await update.message.reply_text("🔎 Đang phân tích link Facebook ...")
    try:
        dl = facebook_direct_link(link)
        if not dl:
            return await update.message.reply_text(
                "❗ Không lấy được link trực tiếp (có thể video riêng tư hoặc bị chặn).\n"
                "Thử tải thủ công:\n• https://snapsave.app\n• https://savefrom.net/\n"
                f"Link: <a href='{html.escape(link)}'>{html.escape(link)}</a>",
                parse_mode=ParseMode.HTML
            )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"fb.mp4"
            with requests.get(dl, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for chunk in r.iter_content(1<<14):
                        if chunk: f.write(chunk)
            if p.exists() and p.stat().st_size < 48*1024*1024:
                with open(p, "rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=f"📘 Facebook\n{pretty_footer()}",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await update.message.reply_text("❗ File > 48MB. Hãy tải thủ công.")
    except Exception as e:
        await update.message.reply_text(f"❌ Facebook error: {e}")

# ─────────── Callbacks (menu clicks) ───────────
async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    k = q.data
    if   k=="m_chat":      await q.message.reply_text("Gõ: /ai <câu hỏi>")
    elif k=="m_solve":     await q.message.reply_text("Gõ: /solve <biểu thức/toán>")
    elif k=="m_translate": await q.message.reply_text("Gõ: /translate <văn bản>")
    elif k=="m_ocr":       await q.message.reply_text("Reply vào ảnh rồi gõ: /ocr")
    elif k=="m_time":      await q.message.reply_text("Gõ: /time <city/country> (vd: tokyo, paris)")
    elif k=="m_news":      await q.message.reply_text("Gõ: /news <từ khóa> (hoặc /newstext)")
    elif k=="m_youtube":   await q.message.reply_text("Gõ: /youtube <link>")
    elif k=="m_tiktok":    await q.message.reply_text("Gõ: /tiktok <link> (vt.tiktok.com ...)")
    elif k=="m_facebook":  await q.message.reply_text("Gõ: /facebook <link>")
    elif k=="m_weather":   await q.message.reply_text("Gõ: /weather <city>")
    elif k=="m_crypto":    await q.message.reply_text("Gõ: /crypto btc")
    elif k=="m_admin":     await admin_info(update, context)
    elif k=="m_help":      await help_cmd(update, context)
    else:
        await q.message.reply_text("❓ Unknown action")

# ─────────── Error handler ───────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Exception while handling an update: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            await update.effective_chat.send_message("❗ Đã có lỗi nhỏ. Bot sẽ tiếp tục chạy.")
    except Exception:
        pass

# ─────────── Health server (Render) ───────────
# Nếu chạy trên Render (có PORT), mở web server để health check.
async def _maybe_health_server(app):
    port = os.getenv("PORT")
    if not port: return
    from aiohttp import web
    async def ping(_): return web.Response(text="OK")
    srv = web.Application()
    srv.add_routes([web.get("/", ping), web.get("/health", ping)])
    runner = web.AppRunner(srv)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()
    log.info("Health server started on port %s", port)

# ─────────── Main ───────────
from telegram.ext import ApplicationBuilder

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .concurrent_updates(True)
        .build()
    )
    # Commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("menu",  menu_cmd))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(CommandHandler("ai",    ai_cmd))
    app.add_handler(CommandHandler("solve", solve_cmd))
    app.add_handler(CommandHandler("translate", translate_cmd))
    app.add_handler(CommandHandler("ocr",   ocr_cmd))
    app.add_handler(CommandHandler("time",  time_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(CommandHandler("news",  news_cmd))
    app.add_handler(CommandHandler("crypto", crypto_cmd))
    app.add_handler(CommandHandler("youtube", youtube_cmd))
    app.add_handler(CommandHandler("tiktok",  tiktok_cmd))
    app.add_handler(CommandHandler("facebook", facebook_cmd))
    app.add_handler(CommandHandler("admin",  lambda u,c: admin_info(u,c,True)))

     print("✅ Bot started successfully!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
