#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===================================================================
   📦 𝐂𝐎𝐍𝐓𝐄𝐍𝐓 𝐕𝐀𝐔𝐋𝐓 𝐁𝐎𝐓 - 𝐀𝐥𝐥-𝐢𝐧-𝐎𝐧𝐞 𝐒𝐭𝐨𝐫𝐞 🔐
===================================================================
Developed By: Shuvom -- Team X
Description: Store videos, files, apps, text, HTML - password protected!
===================================================================
"""

import os
import sys
import sqlite3
import hashlib
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import telebot
    from telebot import types
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ForceReply
except ImportError:
    print("❌ Install: pip install pyTelegramBotAPI")
    sys.exit(1)

try:
    from flask import Flask, jsonify
except ImportError:
    print("❌ Install: pip install flask")
    sys.exit(1)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8683643826:AAEiShrd1UR70RFyXAXpJe764Mxs_JeOwdo"
ADMIN_IDS = [7479467987]  # List of admin Telegram IDs
CHANNEL_ID = "@your_channel_username"  # e.g., "@my_channel" or channel ID
DEVELOPER = "𝐒𝐇𝐔𝐕𝐎𝐌 - 𝐓𝐄𝐀𝐌 𝐗"
BOT_NAME = "📦 𝐂𝐎𝐍𝐓𝐄𝐍𝐓 𝐕𝐀𝐔𝐋𝐓"

DB_FILE = "content_vault.db"
os.makedirs("data", exist_ok=True)
DB_PATH = os.path.join("data", DB_FILE)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ==================== USER DATA STORAGE ====================
user_data = {}  # ✅ গ্লোবাল ডিকশনারি - bot.user_data-এর পরিবর্তে

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,  -- 'video', 'document', 'text', 'html', 'app'
                file_id TEXT,
                text_content TEXT,
                password_hash TEXT NOT NULL,
                uploader_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")

    def add_content(self, title: str, content_type: str, file_id: str, text_content: str, password: str, uploader_id: int) -> int:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO contents (title, content_type, file_id, text_content, password_hash, uploader_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, content_type, file_id, text_content, password_hash, uploader_id)
        )
        conn.commit()
        last_id = c.lastrowid
        conn.close()
        return last_id

    def get_content_by_title(self, title: str) -> Optional[Dict]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM contents WHERE title = ?", (title,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_contents(self) -> List[Dict]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, title, content_type, created_at FROM contents ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def verify_password(self, title: str, password: str) -> bool:
        content = self.get_content_by_title(title)
        if not content:
            return False
        return content['password_hash'] == hashlib.sha256(password.encode()).hexdigest()

    def delete_content(self, title: str) -> bool:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM contents WHERE title = ?", (title,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

db = Database()

# ==================== HELPERS ====================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_user_in_channel(user_id: int) -> bool:
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Channel check error: {e}")
        return False

def get_join_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
    keyboard.add(InlineKeyboardButton("✅ 𝐂𝐇𝐄𝐂𝐊 𝐉𝐎𝐈𝐍", callback_data="check_join"))
    return keyboard

def get_content_emoji(content_type: str) -> str:
    emojis = {
        'video': '🎬',
        'document': '📄',
        'text': '📝',
        'html': '🌐',
        'app': '📱'
    }
    return emojis.get(content_type, '📦')

# ==================== KEYBOARDS ====================
def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("📦 𝐀𝐋𝐋 𝐂𝐎𝐍𝐓𝐄𝐍𝐓"),
        KeyboardButton("🔑 𝐆𝐄𝐓 𝐂𝐎𝐍𝐓𝐄𝐍𝐓"),
        KeyboardButton("ℹ️ 𝐇𝐄𝐋𝐏")
    ]
    if is_admin(ADMIN_IDS[0]):
        buttons.append(KeyboardButton("📤 𝐔𝐏𝐋𝐎𝐀𝐃"))
    keyboard.add(*buttons)
    return keyboard

# ==================== BOT COMMANDS ====================
@bot.message_handler(commands=['start'])
def start_cmd(message: types.Message):
    user = message.from_user
    welcome = f"""
📦 <b>{BOT_NAME}</b> 🔐
━━━━━━━━━━━━━━━━━━━━━━━━

👋 𝐇𝐞𝐥𝐥𝐨, <b>{user.first_name}</b>!

📌 <b>𝐖𝐡𝐚𝐭 𝐈 𝐜𝐚𝐧 𝐬𝐭𝐨𝐫𝐞:</b>
• 🎬 𝐕𝐢𝐝𝐞𝐨𝐬
• 📄 𝐃𝐨𝐜𝐮𝐦𝐞𝐧𝐭𝐬 (𝐚𝐧𝐲 𝐟𝐢𝐥𝐞)
• 📝 𝐓𝐞𝐱𝐭 𝐧𝐨𝐭𝐞𝐬
• 🌐 𝐇𝐓𝐌𝐋 𝐩𝐚𝐠𝐞𝐬
• 📱 𝐀𝐩𝐩𝐬 & 𝐬𝐨𝐟𝐭𝐰𝐚𝐫𝐞

🔐 <b>𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:</b>
• 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝-𝐩𝐫𝐨𝐭𝐞𝐜𝐭𝐞𝐝 𝐚𝐜𝐜𝐞𝐬𝐬
• 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐦𝐞𝐦𝐛𝐞𝐫𝐬𝐡𝐢𝐩 𝐫𝐞𝐪𝐮𝐢𝐫𝐞𝐝
• 𝐀𝐝𝐦𝐢𝐧-𝐨𝐧𝐥𝐲 𝐮𝐩𝐥𝐨𝐚𝐝

🔰 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> {DEVELOPER}
"""
    bot.reply_to(message, welcome, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message: types.Message):
    text = f"""
ℹ️ <b>𝐇𝐄𝐋𝐏 & 𝐆𝐔𝐈𝐃𝐄</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📖 <b>𝐔𝐬𝐞𝐫 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>
• /contents - 𝐋𝐢𝐬𝐭 𝐚𝐥𝐥 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐜𝐨𝐧𝐭𝐞𝐧𝐭
• /get &lt;title&gt; - 𝐆𝐞𝐭 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐛𝐲 𝐭𝐢𝐭𝐥𝐞 (𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐫𝐞𝐪𝐮𝐢𝐫𝐞𝐝)
• /start - 𝐒𝐡𝐨𝐰 𝐦𝐚𝐢𝐧 𝐦𝐞𝐧𝐮

👑 <b>𝐀𝐝𝐦𝐢𝐧 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>
• /upload - 𝐔𝐩𝐥𝐨𝐚𝐝 𝐚𝐧𝐲 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 (𝐟𝐢𝐥𝐞/𝐭𝐞𝐱𝐭/𝐇𝐓𝐌𝐋)
• /uploadtext - 𝐔𝐩𝐥𝐨𝐚𝐝 𝐭𝐞𝐱𝐭/𝐇𝐓𝐌𝐋 𝐝𝐢𝐫𝐞𝐜𝐭𝐥𝐲
• /delete &lt;title&gt; - 𝐃𝐞𝐥𝐞𝐭𝐞 𝐚 𝐜𝐨𝐧𝐭𝐞𝐧𝐭

🔐 <b>𝐑𝐞𝐪𝐮𝐢𝐫𝐞𝐦𝐞𝐧𝐭𝐬:</b>
• 𝐉𝐨𝐢𝐧 𝐜𝐡𝐚𝐧𝐧𝐞𝐥: {CHANNEL_ID}
• 𝐄𝐧𝐭𝐞𝐫 𝐜𝐨𝐫𝐫𝐞𝐜𝐭 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝

━━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> {DEVELOPER}
"""
    bot.reply_to(message, text)

# ==================== ADMIN UPLOAD CONVERSATION ====================
UPLOAD_TITLE, UPLOAD_TYPE, UPLOAD_FILE, UPLOAD_PASSWORD = range(4)

@bot.message_handler(commands=['upload'])
def upload_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ 𝐀𝐝𝐦𝐢𝐧 𝐨𝐧𝐥𝐲!")
        return
    msg = bot.reply_to(message, "📝 <b>𝐄𝐧𝐭𝐞𝐫 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐭𝐢𝐭𝐥𝐞:</b>")
    bot.register_next_step_handler(msg, process_upload_title)

@bot.message_handler(commands=['uploadtext'])
def upload_text_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ 𝐀𝐝𝐦𝐢𝐧 𝐨𝐧𝐥𝐲!")
        return
    msg = bot.reply_to(message, "📝 <b>𝐄𝐧𝐭𝐞𝐫 𝐭𝐢𝐭𝐥𝐞 𝐟𝐨𝐫 𝐭𝐞𝐱𝐭/𝐇𝐓𝐌𝐋:</b>")
    bot.register_next_step_handler(msg, process_text_title)

def process_upload_title(message: types.Message):
    user_id = message.from_user.id
    title = message.text.strip()
    if not title:
        bot.reply_to(message, "❌ 𝐓𝐢𝐭𝐥𝐞 𝐜𝐚𝐧'𝐭 𝐛𝐞 𝐞𝐦𝐩𝐭𝐲.")
        return
    user_data[user_id] = {'title': title}  # ✅ ব্যবহার করুন user_data
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🎬 𝐕𝐢𝐝𝐞𝐨"),
        KeyboardButton("📄 𝐃𝐨𝐜𝐮𝐦𝐞𝐧𝐭"),
        KeyboardButton("📝 𝐓𝐞𝐱𝐭"),
        KeyboardButton("🌐 𝐇𝐓𝐌𝐋"),
        KeyboardButton("📱 𝐀𝐩𝐩")
    )
    msg = bot.reply_to(message, f"📂 <b>𝐒𝐞𝐥𝐞𝐜𝐭 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐭𝐲𝐩𝐞:</b>\n𝐓𝐢𝐭𝐥𝐞: <code>{title}</code>", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_upload_type)

def process_upload_type(message: types.Message):
    user_id = message.from_user.id
    type_map = {
        "🎬 𝐕𝐢𝐝𝐞𝐨": "video",
        "📄 𝐃𝐨𝐜𝐮𝐦𝐞𝐧𝐭": "document",
        "📝 𝐓𝐞𝐱𝐭": "text",
        "🌐 𝐇𝐓𝐌𝐋": "html",
        "📱 𝐀𝐩𝐩": "app"
    }
    content_type = type_map.get(message.text)
    if not content_type:
        bot.reply_to(message, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐬𝐞𝐥𝐞𝐜𝐭𝐢𝐨𝐧. 𝐔𝐬𝐞 /upload 𝐚𝐠𝐚𝐢𝐧.")
        return
    user_data[user_id]['content_type'] = content_type

    if content_type in ['text', 'html']:
        msg = bot.reply_to(message, f"📝 <b>𝐒𝐞𝐧𝐝 𝐭𝐡𝐞 𝐭𝐞𝐱𝐭/𝐇𝐓𝐌𝐋 𝐜𝐨𝐧𝐭𝐞𝐧𝐭:</b>\n𝐓𝐢𝐭𝐥𝐞: <code>{user_data[user_id]['title']}</code>")
        bot.register_next_step_handler(msg, process_text_content)
    else:
        msg = bot.reply_to(message, f"📤 <b>𝐒𝐞𝐧𝐝 𝐭𝐡𝐞 𝐟𝐢𝐥𝐞:</b>\n𝐓𝐢𝐭𝐥𝐞: <code>{user_data[user_id]['title']}</code>")
        bot.register_next_step_handler(msg, process_upload_file)

def process_text_title(message: types.Message):
    user_id = message.from_user.id
    title = message.text.strip()
    if not title:
        bot.reply_to(message, "❌ 𝐓𝐢𝐭𝐥𝐞 𝐜𝐚𝐧'𝐭 𝐛𝐞 𝐞𝐦𝐩𝐭𝐲.")
        return
    user_data[user_id] = {'title': title}
    msg = bot.reply_to(message, f"📝 <b>𝐒𝐞𝐧𝐝 𝐭𝐡𝐞 𝐭𝐞𝐱𝐭/𝐇𝐓𝐌𝐋 𝐜𝐨𝐧𝐭𝐞𝐧𝐭:</b>\n𝐓𝐢𝐭𝐥𝐞: <code>{title}</code>\n\n💡 <i>𝐅𝐨𝐫 𝐇𝐓𝐌𝐋, 𝐢𝐧𝐜𝐥𝐮𝐝𝐞 &lt;html&gt; &lt;body&gt; 𝐭𝐚𝐠𝐬</i>")
    bot.register_next_step_handler(msg, process_text_content)

def process_text_content(message: types.Message):
    user_id = message.from_user.id
    text_content = message.text
    if not text_content:
        bot.reply_to(message, "❌ 𝐂𝐨𝐧𝐭𝐞𝐧𝐭 𝐜𝐚𝐧'𝐭 𝐛𝐞 𝐞𝐦𝐩𝐭𝐲.")
        return
    user_data[user_id]['text_content'] = text_content
    msg = bot.reply_to(message, "🔑 <b>𝐄𝐧𝐭𝐞𝐫 𝐚 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐟𝐨𝐫 𝐭𝐡𝐢𝐬 𝐜𝐨𝐧𝐭𝐞𝐧𝐭:</b>")
    bot.register_next_step_handler(msg, process_upload_password)

def process_upload_file(message: types.Message):
    user_id = message.from_user.id
    if not message.document and not message.video:
        bot.reply_to(message, "❌ 𝐏𝐥𝐞𝐚𝐬𝐞 𝐬𝐞𝐧𝐝 𝐚 𝐟𝐢𝐥𝐞.")
        return
    file_id = message.document.file_id if message.document else message.video.file_id
    user_data[user_id]['file_id'] = file_id
    msg = bot.reply_to(message, "🔑 <b>𝐄𝐧𝐭𝐞𝐫 𝐚 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐟𝐨𝐫 𝐭𝐡𝐢𝐬 𝐜𝐨𝐧𝐭𝐞𝐧𝐭:</b>")
    bot.register_next_step_handler(msg, process_upload_password)

def process_upload_password(message: types.Message):
    user_id = message.from_user.id
    password = message.text.strip()
    if not password:
        bot.reply_to(message, "❌ 𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐜𝐚𝐧'𝐭 𝐛𝐞 𝐞𝐦𝐩𝐭𝐲.")
        return
    data = user_data.get(user_id, {})
    title = data.get('title')
    content_type = data.get('content_type', 'document')
    file_id = data.get('file_id')
    text_content = data.get('text_content')
    
    if not title or (not file_id and not text_content):
        bot.reply_to(message, "❌ 𝐒𝐞𝐬𝐬𝐢𝐨𝐧 𝐞𝐱𝐩𝐢𝐫𝐞𝐝. 𝐔𝐬𝐞 /upload 𝐚𝐠𝐚𝐢𝐧.")
        return
    
    db.add_content(title, content_type, file_id, text_content, password, user_id)
    emoji = get_content_emoji(content_type)
    bot.reply_to(message, f"✅ <b>𝐂𝐨𝐧𝐭𝐞𝐧𝐭 𝐚𝐝𝐝𝐞𝐝 𝐬𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!</b>\n{emoji} <b>𝐓𝐢𝐭𝐥𝐞:</b> <code>{title}</code>\n📂 <b>𝐓𝐲𝐩𝐞:</b> {content_type.upper()}\n🔑 <b>𝐏𝐚𝐬𝐬𝐰𝐨𝐫𝐝:</b> <code>{password}</code>")
    user_data.pop(user_id, None)

# ==================== USER COMMANDS ====================
@bot.message_handler(commands=['contents'])
def list_contents_cmd(message: types.Message):
    if not is_user_in_channel(message.from_user.id):
        bot.reply_to(message, f"🔒 <b>𝐘𝐨𝐮 𝐦𝐮𝐬𝐭 𝐣𝐨𝐢𝐧 𝐨𝐮𝐫 𝐜𝐡𝐚𝐧𝐧𝐞𝐥 𝐟𝐢𝐫𝐬𝐭!</b>\n{CHANNEL_ID}\n\n𝐂𝐥𝐢𝐜𝐤 𝐭𝐡𝐞 𝐛𝐮𝐭𝐭𝐨𝐧 𝐭𝐨 𝐣𝐨𝐢𝐧, 𝐭𝐡𝐞𝐧 𝐩𝐫𝐞𝐬𝐬 '𝐂𝐇𝐄𝐂𝐊'.",
                     reply_markup=get_join_keyboard())
        return
    contents = db.get_all_contents()
    if not contents:
        bot.reply_to(message, "📭 <b>𝐍𝐨 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐲𝐞𝐭.</b>")
        return
    text = "📦 <b>𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐂𝐨𝐧𝐭𝐞𝐧𝐭:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for c in contents:
        emoji = get_content_emoji(c['content_type'])
        text += f"{emoji} <b>{c['title']}</b>  (📅 {c['created_at'][:10]})\n"
    text += "\n💡 <b>𝐔𝐬𝐞:</b> /get <i>title</i>  𝐭𝐨 𝐚𝐜𝐜𝐞𝐬𝐬"
    bot.reply_to(message, text)

@bot.message_handler(commands=['get'])
def get_content_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_user_in_channel(user_id):
        bot.reply_to(message, f"🔒 <b>𝐘𝐨𝐮 𝐦𝐮𝐬𝐭 𝐣𝐨𝐢𝐧 𝐨𝐮𝐫 𝐜𝐡𝐚𝐧𝐧𝐞𝐥 𝐟𝐢𝐫𝐬𝐭!</b>\n{CHANNEL_ID}\n\n𝐂𝐥𝐢𝐜𝐤 𝐭𝐡𝐞 𝐛𝐮𝐭𝐭𝐨𝐧 𝐭𝐨 𝐣𝐨𝐢𝐧, 𝐭𝐡𝐞𝐧 𝐩𝐫𝐞𝐬𝐬 '𝐂𝐇𝐄𝐂𝐊'.",
                     reply_markup=get_join_keyboard())
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ <b>𝐔𝐬𝐚𝐠𝐞:</b> /get <i>title</i>")
        return
    title = parts[1].strip()
    content = db.get_content_by_title(title)
    if not content:
        bot.reply_to(message, f"❌ <b>𝐍𝐨 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐟𝐨𝐮𝐧𝐝 𝐰𝐢𝐭𝐡 𝐭𝐢𝐭𝐥𝐞 '<i>{title}</i>'</b>")
        return
    msg = bot.reply_to(message, f"🔑 <b>𝐄𝐧𝐭𝐞𝐫 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝 𝐟𝐨𝐫:</b> <code>{title}</code>")
    bot.register_next_step_handler(msg, process_password_input, title)

@bot.message_handler(commands=['delete'])
def delete_content_cmd(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ 𝐀𝐝𝐦𝐢𝐧 𝐨𝐧𝐥𝐲!")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ <b>𝐔𝐬𝐚𝐠𝐞:</b> /delete <i>title</i>")
        return
    title = parts[1].strip()
    if db.delete_content(title):
        bot.reply_to(message, f"✅ <b>𝐂𝐨𝐧𝐭𝐞𝐧𝐭 '<i>{title}</i>' 𝐝𝐞𝐥𝐞𝐭𝐞𝐝.</b>")
    else:
        bot.reply_to(message, f"❌ <b>𝐂𝐨𝐧𝐭𝐞𝐧𝐭 '<i>{title}</i>' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.</b>")

def process_password_input(message: types.Message, title: str):
    password = message.text.strip()
    user_id = message.from_user.id
    if not is_user_in_channel(user_id):
        bot.reply_to(message, f"🔒 <b>𝐘𝐨𝐮 𝐦𝐮𝐬𝐭 𝐣𝐨𝐢𝐧 𝐭𝐡𝐞 𝐜𝐡𝐚𝐧𝐧𝐞𝐥 𝐟𝐢𝐫𝐬𝐭!</b>")
        return
    if db.verify_password(title, password):
        content = db.get_content_by_title(title)
        if content:
            try:
                content_type = content['content_type']
                emoji = get_content_emoji(content_type)
                caption = f"{emoji} <b>{title}</b>\n🔓 <b>𝐀𝐜𝐜𝐞𝐬𝐬 𝐠𝐫𝐚𝐧𝐭𝐞𝐝</b>"
                
                if content_type in ['text', 'html']:
                    bot.send_message(user_id, f"{caption}\n\n<pre>{content['text_content']}</pre>")
                elif content_type == 'video':
                    bot.send_video(user_id, content['file_id'], caption=caption)
                else:
                    bot.send_document(user_id, content['file_id'], caption=caption)
                bot.reply_to(message, "✅ <b>𝐂𝐨𝐧𝐭𝐞𝐧𝐭 𝐬𝐞𝐧𝐭 𝐬𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!</b>")
            except Exception as e:
                bot.reply_to(message, f"❌ <b>𝐅𝐚𝐢𝐥𝐞𝐝 𝐭𝐨 𝐬𝐞𝐧𝐝:</b> {e}")
        else:
            bot.reply_to(message, "❌ <b>𝐂𝐨𝐧𝐭𝐞𝐧𝐭 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.</b>")
    else:
        bot.reply_to(message, "❌ <b>𝐖𝐫𝐨𝐧𝐠 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝!</b> 𝐓𝐫𝐲 𝐚𝐠𝐚𝐢𝐧.")

# ==================== BUTTON HANDLERS ====================
@bot.message_handler(func=lambda m: m.text == "📦 𝐀𝐋𝐋 𝐂𝐎𝐍𝐓𝐄𝐍𝐓")
def contents_button(message: types.Message):
    list_contents_cmd(message)

@bot.message_handler(func=lambda m: m.text == "🔑 𝐆𝐄𝐓 𝐂𝐎𝐍𝐓𝐄𝐍𝐓")
def get_content_button(message: types.Message):
    msg = bot.reply_to(message, "📝 <b>𝐄𝐧𝐭𝐞𝐫 𝐭𝐡𝐞 𝐜𝐨𝐧𝐭𝐞𝐧𝐭 𝐭𝐢𝐭𝐥𝐞:</b>")
    bot.register_next_step_handler(msg, process_get_title)

def process_get_title(message: types.Message):
    title = message.text.strip()
    if not title:
        bot.reply_to(message, "❌ 𝐓𝐢𝐭𝐥𝐞 𝐜𝐚𝐧'𝐭 𝐛𝐞 𝐞𝐦𝐩𝐭𝐲.")
        return
    fake_msg = message
    fake_msg.text = f"/get {title}"
    get_content_cmd(fake_msg)

@bot.message_handler(func=lambda m: m.text == "ℹ️ 𝐇𝐄𝐋𝐏")
def help_button(message: types.Message):
    help_cmd(message)

@bot.message_handler(func=lambda m: m.text == "📤 𝐔𝐏𝐋𝐎𝐀𝐃")
def upload_button(message: types.Message):
    upload_cmd(message)

# ==================== CALLBACK QUERY ====================
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    if is_user_in_channel(user_id):
        bot.answer_callback_query(call.id, "✅ 𝐉𝐨𝐢𝐧 𝐯𝐞𝐫𝐢𝐟𝐢𝐞𝐝! 𝐘𝐨𝐮 𝐜𝐚𝐧 𝐧𝐨𝐰 𝐚𝐜𝐜𝐞𝐬𝐬.", show_alert=True)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(user_id, "🎉 <b>𝐀𝐜𝐜𝐞𝐬𝐬 𝐠𝐫𝐚𝐧𝐭𝐞𝐝!</b>\n𝐔𝐬𝐞 /contents 𝐭𝐨 𝐬𝐞𝐞 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐜𝐨𝐧𝐭𝐞𝐧𝐭.")
    else:
        bot.answer_callback_query(call.id, "❌ 𝐘𝐨𝐮 𝐡𝐚𝐯𝐞𝐧'𝐭 𝐣𝐨𝐢𝐧𝐞𝐝 𝐲𝐞𝐭.", show_alert=True)

# ==================== FLASK KEEP-ALIVE ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "📦 Content Vault Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ==================== MAIN ====================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   ███████╗██╗  ██╗    ███████╗████████╗ ██████╗ ██████╗    ║
    ║   ██╔════╝██║  ██║    ██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗   ║
    ║   ███████╗███████║    ███████╗   ██║   ██║   ██║██████╔╝   ║
    ║   ╚════██║██╔══██║    ╚════██║   ██║   ██║   ██║██╔══██╗   ║
    ║   ███████║██║  ██║    ███████║   ██║   ╚██████╔╝██║  ██║   ║
    ║   ╚══════╝╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ║
    ║                                                              ║
    ║         📦 CONTENT VAULT - All-in-One Store 🔐             ║
    ║                                                              ║
    ║         👑 Developer: SHUVOM - TEAM X                       ║
    ║         🚀 Bot is starting...                               ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    try:
        bot.infinity_polling(timeout=30)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        time.sleep(5)
