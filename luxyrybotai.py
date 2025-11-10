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
    await admin_info(update, context)

# ─────────── Các hàm khác (giả sử đầy đủ từ code truncated) ───────────
# Thêm các hàm như ai_cmd, solve_cmd, translate_cmd, ocr_cmd, time_cmd, weather_cmd, news_cmd, crypto_cmd, youtube_cmd, tiktok_cmd, facebook_cmd ở đây nếu thiếu.
# Ví dụ (dựa trên code gốc):
async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Code xử lý AI
    pass  # Thay bằng code thật

# Tương tự cho các cmd khác...

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

# Thêm tương tự cho tiktok_cmd, youtube_cmd, crypto_cmd, news_cmd, weather_cmd, time_cmd, ocr_cmd, translate_cmd, solve_cmd nếu thiếu.

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

# ========== Main ==========
# ========== Main ==========
async def main():
    print("Bot is starting...")

    app = Application.builder().token(TOKEN).concurrent_updates(True).build()

    # Thêm handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("solve", solve_cmd))
    app.add_handler(CommandHandler("translate", translate_cmd))
    app.add_handler(CommandHandler("ocr", ocr_cmd))
    app.add_handler(CommandHandler("time", time_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("crypto", crypto_cmd))
    app.add_handler(CommandHandler("youtube", youtube_cmd))
    app.add_handler(CommandHandler("tiktok", tiktok_cmd))
    app.add_handler(CommandHandler("facebook", facebook_cmd))
    app.add_handler(CommandHandler("admin", lambda u, c: admin_info(u, c, True)))
    app.add_handler(CallbackQueryHandler(on_menu_click))

    app.add_error_handler(error_handler)

    # Health server
    await _maybe_health_server(app)

    print("Bot started successfully!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())