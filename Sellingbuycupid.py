import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import re
import time
import threading

# ========== CONFIGURATION ==========
BOT_TOKEN = "8791523809:AAGKPgRgcCO0JVofB3KEjiN4kqRXGvvRZ18"
ADMIN_IDS = [7691071175]  # Replace with actual admin Telegram user IDs

bot = telebot.TeleBot(BOT_TOKEN)

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        role TEXT DEFAULT 'buyer',
        phone TEXT,
        joined_date TEXT DEFAULT (datetime('now','localtime'))
    )''')
    
    # Seller requests table
    c.execute('''CREATE TABLE IF NOT EXISTS seller_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        phone TEXT,
        shop_name TEXT,
        shop_description TEXT,
        status TEXT DEFAULT 'pending',
        request_date TEXT DEFAULT (datetime('now','localtime')),
        reviewed_by INTEGER,
        review_date TEXT
    )''')
    
    # Categories table
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        created_date TEXT DEFAULT (datetime('now','localtime'))
    )''')
    
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        name TEXT,
        price REAL,
        description TEXT,
        category_id INTEGER,
        image_url TEXT,
        is_active INTEGER DEFAULT 1,
        created_date TEXT DEFAULT (datetime('now','localtime')),
        updated_date TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (seller_id) REFERENCES users(user_id),
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )''')
    
    # Orders / Contact requests table
    c.execute('''CREATE TABLE IF NOT EXISTS contact_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        buyer_id INTEGER,
        seller_id INTEGER,
        message TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (buyer_id) REFERENCES users(user_id),
        FOREIGN KEY (seller_id) REFERENCES users(user_id)
    )''')
    
    # Reviews table
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        user_id INTEGER,
        rating INTEGER,
        review_text TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')
    
    # Admin logs table
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT DEFAULT (datetime('now','localtime'))
    )''')
    
    conn.commit()
    conn.close()

# ========== DEFAULT CATEGORIES ==========
def create_default_categories():
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    defaults = [
        ("Instagram Bans"),
        ("Instagram unbans"),
        ("username"),
        ("Instagram id"),
        ("telegram"),
        ("Bot making"),
        ("Website developing"),
        ("Rent"),
        ("Services"),
        ("Others")
    ]
    for name, desc in defaults:
        try:
            c.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", (name, desc))
        except:
            pass
    conn.commit()
    conn.close()
    # ========== HELPER FUNCTIONS ==========
def get_user_role(user_id):
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def register_or_get_user(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                  (user_id, username, first_name))
        conn.commit()
    conn.close()

def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🛍️ Browse Products"),
        KeyboardButton("📦 My Orders"),
        KeyboardButton("⭐ My Reviews"),
        KeyboardButton("👤 My Profile"),
        KeyboardButton("❓ Help")
    )
    return markup

def admin_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("👥 Pending Sellers"),
        KeyboardButton("⭐ Pending Reviews"),
        KeyboardButton("📊 Stats"),
        KeyboardButton("📂 Categories"),
        KeyboardButton("📦 All Products"),
        KeyboardButton("👥 All Users"),
        KeyboardButton("📢 Broadcast"),
        KeyboardButton("📋 Logs"),
        KeyboardButton("🔙 Main Menu")
    )
    return markup

# ========== START COMMAND ==========
@bot.message_handler(commands=['start'])
def start(message):
    register_or_get_user(message)
    user_id = message.from_user.id
    
    # Check if admin
    if user_id in ADMIN_IDS:
        bot.reply_to(message, "👋 Welcome Admin! Use the admin panel to manage the marketplace.")
        return
    
    role = get_user_role(user_id)
    
    markup = InlineKeyboardMarkup(row_width=2)
    if role == 'seller':
        markup.add(
            InlineKeyboardButton("📋 Seller Dashboard", callback_data="seller_dashboard"),
            InlineKeyboardButton("🛍️ Browse as Buyer", callback_data="buyer_menu")
        )
        bot.reply_to(message, "👋 Welcome back! You're registered as a seller.", reply_markup=markup)
    else:
        markup.add(
            InlineKeyboardButton("🛍️ Browse Products", callback_data="buyer_menu"),
            InlineKeyboardButton("💼 Become a Seller", callback_data="become_seller")
        )
        bot.reply_to(message, "👋 Welcome to Marketplace Bot!\n\nBrowse products or become a seller to start selling!", reply_markup=markup)

@bot.message_handler(commands=['menu'])
def show_menu(message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        bot.reply_to(message, "📋 Admin Panel:", reply_markup=admin_main_menu())
    else:
        bot.reply_to(message, "📋 Main Menu:", reply_markup=main_menu_keyboard())

# ========== BUYER: BROWSE PRODUCTS ==========
@bot.message_handler(func=lambda m: m.text == "🛍️ Browse Products")
def browse_products_prompt(message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    
    if not categories:
        bot.reply_to(message, "⚠️ No categories available yet.")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    for cat_id, cat_name in categories:
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}"))
    markup.add(InlineKeyboardButton("🔍 Search Products", callback_data="search_products"))
    markup.add(InlineKeyboardButton("❌ Close", callback_data="close"))
    
    bot.reply_to(message, "📂 **Select a Category to Browse:**\n\nChoose a category below to see all products:", 
                 reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def show_category_products(call):
    cat_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat = c.fetchone()
    
    c.execute('''SELECT p.id, p.name, p.price, p.description, u.first_name 
                 FROM products p JOIN users u ON p.seller_id = u.user_id 
                 WHERE p.category_id = ? AND p.is_active = 1''', (cat_id,))
    products = c.fetchall()
    conn.close()
    
    if not products:
        bot.edit_message_text(f"📂 **{cat[0]}**\n\nNo products available in this category yet.", 
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        return
    
    text = f"📂 **{cat[0]}**\n\n"
    for p_id, p_name, p_price, p_desc, seller_name in products:
        text += f"📌 **{p_name}**\n💰 ₹{p_price:,.2f}\n👤 Seller: {seller_name}\n"
        if p_desc:
            text += f"📝 {p_desc[:100]}\n"
        text += f"━━━━━━━━━━━━━━━\n"
    
    markup = InlineKeyboardMarkup(row_width=1)
    for p_id, p_name, p_price, p_desc, seller_name in products:
        markup.add(InlineKeyboardButton(f"📞 Contact - {p_name} (₹{p_price:,.0f})", callback_data=f"contact_{p_id}"))
    markup.add(InlineKeyboardButton("◀️ Back to Categories", callback_data="back_categories"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_categories")
def back_to_categories(call):
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    
    markup = InlineKeyboardMarkup(row_width=2)
    for cat_id, cat_name in categories:
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}"))
    markup.add(InlineKeyboardButton("🔍 Search Products", callback_data="search_products"))
    markup.add(InlineKeyboardButton("❌ Close", callback_data="close"))
    
    bot.edit_message_text("📂 **Select a Category to Browse:**", 
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

# ========== BUYER: CONTACT SELLER ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("contact_"))
def contact_seller_prompt(call):
    product_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT name, price, seller_id FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "❌ Product not found!")
        return
    
    msg = bot.edit_message_text(f"📞 **Contact Seller**\n\nProduct: {product[0]}\nPrice: ₹{product[1]:,.2f}\n\nSend your message/query to the seller:",
                               call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_contact_message, product_id, product[2])

def process_contact_message(message, product_id, seller_id):
    buyer_id = message.from_user.id
    buyer_msg = message.text
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("INSERT INTO contact_requests (product_id, buyer_id, seller_id, message) VALUES (?, ?, ?, ?)",
              (product_id, buyer_id, seller_id, buyer_msg))
    contact_id = c.lastrowid
    
    # Get product info
    c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    # Get buyer info
    c.execute("SELECT username, first_name FROM users WHERE user_id = ?", (buyer_id,))
    buyer = c.fetchone()
    
    conn.commit()
    conn.close()
    
    buyer_name = buyer[1] if buyer[1] else f"User {buyer_id}"
    buyer_username = f"@{buyer[0]}" if buyer[0] else "No username"
    
    # Notify seller
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Contact Buyer", callback_data=f"accept_contact_{contact_id}"),
        InlineKeyboardButton("❌ Skip", callback_data=f"skip_contact_{contact_id}")
    )
    
    seller_notification = (
        f"📩 **New Contact Request!**\n\n"
        f"📦 Product: {product[0]}\n"
        f"👤 Buyer: {buyer_name} ({buyer_username})\n"
        f"💬 Message: {buyer_msg}\n\n"
        f"Press 'Contact Buyer' to get their details."
    )
    
    try:
        bot.send_message(seller_id, seller_notification, reply_markup=markup, parse_mode="Markdown")
        bot.reply_to(message, "✅ Your message has been sent to the seller! They will contact you soon.")
    except:
        bot.reply_to(message, "✅ Message recorded! (Seller may need to start the bot first)")

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_contact_"))
def accept_contact(call):
    contact_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT cr.buyer_id, cr.message, p.name, u.first_name, u.username 
                 FROM contact_requests cr 
                 JOIN products p ON cr.product_id = p.id 
                 JOIN users u ON cr.buyer_id = u.user_id 
                 WHERE cr.id = ?''', (contact_id,))
    data = c.fetchone()
    
    if data:
        buyer_id, msg, prod_name, buyer_name, buyer_username = data
        buyer_contact = f"@{buyer_username}" if buyer_username else f"User ID: {buyer_id}"
        
        text = (
            f"✅ **Buyer Details:**\n\n"
            f"📦 Product: {prod_name}\n"
            f"👤 Name: {buyer_name}\n"
            f"📞 Contact: {buyer_contact}\n"
            f"💬 Their Message: {msg}\n\n"
            f"Send them a message to negotiate!"
        )
        
        c.execute("UPDATE contact_requests SET status = 'accepted' WHERE id = ?", (contact_id,))
        conn.commit()
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("skip_contact_"))
def skip_contact(call):
    contact_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE contact_requests SET status = 'skipped' WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("⏭️ Contact request skipped.", call.message.chat.id, call.message.message_id)

# ========== BUYER: SEARCH ==========
@bot.callback_query_handler(func=lambda call: call.data == "search_products")
def search_prompt(call):
    msg = bot.edit_message_text("🔍 **Search Products**\n\nType a product name or keyword to search:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text.strip()
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT p.id, p.name, p.price, p.description, u.first_name, c.name 
                 FROM products p JOIN users u ON p.seller_id = u.user_id 
                 JOIN categories c ON p.category_id = c.id
                 WHERE p.is_active = 1 AND (p.name LIKE ? OR p.description LIKE ?)''',
              (f'%{query}%', f'%{query}%'))
    products = c.fetchall()
    conn.close()
    
    if not products:
        bot.reply_to(message, f"❌ No products found matching '{query}'.")
        return
    
    text = f"🔍 **Search Results: '{query}'**\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for p_id, p_name, p_price, p_desc, seller_name, cat_name in products:
        text += f"📌 **{p_name}**\n💰 ₹{p_price:,.2f} | 📂 {cat_name}\n👤 {seller_name}\n━━━━━━━━━━\n"
        markup.add(InlineKeyboardButton(f"📞 Contact - {p_name}", callback_data=f"contact_{p_id}"))
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

# ========== MY ORDERS / CONTACT HISTORY ==========
@bot.message_handler(func=lambda m: m.text == "📦 My Orders")
def my_orders(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # As buyer
    c.execute('''SELECT cr.id, p.name, cr.message, cr.status, cr.created_date
                 FROM contact_requests cr JOIN products p ON cr.product_id = p.id
                 WHERE cr.buyer_id = ? ORDER BY cr.created_date DESC''', (user_id,))
    as_buyer = c.fetchall()
    
    # As seller
    c.execute('''SELECT cr.id, p.name, u.first_name, cr.message, cr.status, cr.created_date
                 FROM contact_requests cr 
                 JOIN products p ON cr.product_id = p.id 
                 JOIN users u ON cr.buyer_id = u.user_id
                 WHERE cr.seller_id = ? ORDER BY cr.created_date DESC''', (user_id,))
    as_seller = c.fetchall()
    conn.close()
    
    text = "📦 **My Orders & Contacts**\n\n"
    
    if as_buyer:
        text += "**As Buyer (Inquiries Sent):**\n"
        for item in as_buyer[:5]:
            status_emoji = "⏳" if item[3] == 'pending' else "✅" if item[3] == 'accepted' else "⏭️"
            text += f"{status_emoji} {item[1]} - {item[3].title()}\n"
        text += "\n"
    
    if as_seller:
        text += "**As Seller (Inquiries Received):**\n"
        for item in as_seller[:5]:
            status_emoji = "⏳" if item[4] == 'pending' else "✅" if item[4] == 'accepted' else "⏭️"
            text += f"{status_emoji} {item[1]} by {item[2]} - {item[4].title()}\n"
    
    if not as_buyer and not as_seller:
        text += "No orders or contact requests yet."
    
    bot.reply_to(message, text, parse_mode="Markdown")
    # ========== SELLER REGISTRATION ==========
@bot.callback_query_handler(func=lambda call: call.data == "become_seller")
def become_seller_start(call):
    msg = bot.edit_message_text("📝 **Seller Registration**\n\nPlease enter your **Shop/Business Name**:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_shop_name)

def process_shop_name(message):
    shop_name = message.text.strip()
    if len(shop_name) < 2:
        bot.reply_to(message, "⚠️ Shop name is too short. Please enter at least 2 characters.")
        return
    
    msg = bot.reply_to(message, f"Great! Now enter a brief **description** of your shop/business:")
    bot.register_next_step_handler(msg, process_shop_description, shop_name)

def process_shop_description(message, shop_name):
    shop_desc = message.text.strip()
    if len(shop_desc) < 5:
        bot.reply_to(message, "⚠️ Description is too short. Please provide more detail.")
        return
    
    msg = bot.reply_to(message, "📞 Finally, enter your **Phone Number** (for customers to reach you):")
    bot.register_next_step_handler(msg, process_seller_phone, shop_name, shop_desc)

def process_seller_phone(message, shop_name, shop_desc):
    phone = message.text.strip()
    
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''INSERT INTO seller_requests (user_id, username, first_name, phone, shop_name, shop_description)
                 VALUES (?, ?, ?, ?, ?, ?)''', (user_id, username, first_name, phone, shop_name, shop_desc))
    conn.commit()
    conn.close()
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_seller_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_seller_{user_id}")
            )
            bot.send_message(admin_id, 
                f"📝 **New Seller Request**\n\n"
                f"👤 Name: {first_name}\n"
                f"🆔 ID: {user_id}\n"
                f"📧 Username: @{username}\n"
                f"🏪 Shop: {shop_name}\n"
                f"📝 Description: {shop_desc}\n"
                f"📞 Phone: {phone}",
                reply_markup=markup, parse_mode="Markdown")
        except:
            pass
    
    bot.reply_to(message, "✅ **Request Sent!** Your seller registration has been submitted for admin approval. You'll be notified once reviewed.", parse_mode="Markdown")

# ========== ADMIN: APPROVE/REJECT SELLER ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_seller_"))
def approve_seller(call):
    user_id = int(call.data.split("_")[2])
    admin_id = call.from_user.id
    
    if admin_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Unauthorized!")
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # Get request details
    c.execute("SELECT shop_name FROM seller_requests WHERE user_id = ? AND status = 'pending'", (user_id,))
    req = c.fetchone()
    
    if not req:
        bot.answer_callback_query(call.id, "❌ Request already processed!")
        conn.close()
        return
    
    # Update user role
    c.execute("UPDATE users SET role = 'seller', phone = (SELECT phone FROM seller_requests WHERE user_id = ?) WHERE user_id = ?", 
              (user_id, user_id))
    c.execute("UPDATE seller_requests SET status = 'approved', reviewed_by = ?, review_date = datetime('now','localtime') WHERE user_id = ?",
              (admin_id, user_id))
    
    # Log
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'approve_seller', ?)",
              (admin_id, f"Approved seller {user_id} - {req[0]}"))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"✅ **Approved!** {req[0]} is now a seller.", 
                         call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    try:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📋 Seller Dashboard", callback_data="seller_dashboard"))
        bot.send_message(user_id, 
            f"🎉 **Congratulations!** Your seller request for **{req[0]}** has been approved!\n\n"
            f"Start adding products now!", reply_markup=markup, parse_mode="Markdown")
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_seller_"))
def reject_seller(call):
    user_id = int(call.data.split("_")[2])
    admin_id = call.from_user.id
    
    if admin_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Unauthorized!")
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    c.execute("SELECT shop_name FROM seller_requests WHERE user_id = ? AND status = 'pending'", (user_id,))
    req = c.fetchone()
    
    if not req:
        bot.answer_callback_query(call.id, "❌ Request already processed!")
        conn.close()
        return
    
    c.execute("UPDATE seller_requests SET status = 'rejected', reviewed_by = ?, review_date = datetime('now','localtime') WHERE user_id = ?",
              (admin_id, user_id))
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'reject_seller', ?)",
              (admin_id, f"Rejected seller {user_id} - {req[0]}"))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"❌ Rejected {req[0]}'s seller request.", 
                         call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    try:
        bot.send_message(user_id, f"😔 Sorry, your seller request for **{req[0]}** was not approved. Contact admin for more info.", parse_mode="Markdown")
    except:
        pass
        # ========== SELLER DASHBOARD ==========
@bot.callback_query_handler(func=lambda call: call.data == "seller_dashboard")
def seller_dashboard(call):
    user_id = call.from_user.id
    role = get_user_role(user_id)
    
    if role != 'seller':
        bot.answer_callback_query(call.id, "❌ You are not registered as a seller!")
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products WHERE seller_id = ?", (user_id,))
    total_products = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products WHERE seller_id = ? AND is_active = 1", (user_id,))
    active_products = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM contact_requests WHERE seller_id = ? AND status = 'pending'", (user_id,))
    pending_contacts = c.fetchone()[0]
    c.execute("SELECT COALESCE(AVG(r.rating), 0) FROM reviews r JOIN products p ON r.product_id = p.id WHERE p.seller_id = ? AND r.status = 'approved'", (user_id,))
    avg_rating = c.fetchone()[0]
    conn.close()
    
    text = (
        f"📋 **Seller Dashboard**\n\n"
        f"📦 Total Products: {total_products}\n"
        f"✅ Active: {active_products}\n"
        f"📩 Pending Contacts: {pending_contacts}\n"
        f"⭐ Avg Rating: {avg_rating:.1f} / 5\n\n"
        f"Choose an option below:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Add Product", callback_data="add_product"),
        InlineKeyboardButton("📦 My Products", callback_data="my_products"),
        InlineKeyboardButton("📩 Contact Requests", callback_data="seller_contacts"),
        InlineKeyboardButton("⭐ My Reviews", callback_data="seller_reviews"),
        InlineKeyboardButton("◀️ Back", callback_data="back_to_main")
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode="Markdown")

# ========== ADD PRODUCT ==========
@bot.callback_query_handler(func=lambda call: call.data == "add_product")
def add_product_start(call):
    msg = bot.edit_message_text("➕ **Add New Product**\n\nEnter the **Product Name**:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_product_name)

def process_product_name(message):
    name = message.text.strip()
    if len(name) < 2:
        bot.reply_to(message, "⚠️ Product name too short. Please try again.")
        return
    
    msg = bot.reply_to(message, f"Product: **{name}**\n\nNow enter the **Price (in ₹)**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_product_price, name)

def process_product_price(message, name):
    try:
        price = float(message.text.strip().replace(',', ''))
        if price <= 0:
            raise ValueError
    except:
        bot.reply_to(message, "⚠️ Invalid price! Please enter a valid number (e.g., 299.99).")
        return
    
    # Show category selection
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    
    markup = InlineKeyboardMarkup(row_width=2)
    for cat_id, cat_name in categories:
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"selcat_{cat_id}_{name}_{price}"))
    
    bot.reply_to(message, f"Product: **{name}** | ₹{price:,.2f}\n\nSelect **Category**:", 
                reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("selcat_"))
def process_product_category(call):
    parts = call.data.split("_", 3)
    cat_id = int(parts[1])
    name = parts[2]
    price = float(parts[3])
    
    msg = bot.edit_message_text(f"Product: **{name}** | ₹{price:,.2f}\n\nNow enter a **Description** (or type 'skip'):",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_product_description, name, price, cat_id)

def process_product_description(message, name, price, cat_id):
    description = message.text.strip()
    if description.lower() == 'skip':
        description = ""
    
    # Confirm
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat_name = c.fetchone()[0]
    conn.close()
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_prod_{name}_{price}_{cat_id}_{description[:50]}"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_prod")
    )
    
    text = (
        f"📋 **Product Summary**\n\n"
        f"📌 Name: {name}\n"
        f"💰 Price: ₹{price:,.2f}\n"
        f"📂 Category: {cat_name}\n"
        f"📝 Description: {description[:200] if description else 'N/A'}\n\n"
        f"Confirm?"
    )
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_prod_"))
def confirm_product(call):
    parts = call.data.split("_", 4)
    name = parts[2]
    price = float(parts[3])
    rest = parts[4]
    
    # Parse rest - last part is description, second last is cat_id
    last_underscore = rest.rfind("_")
    cat_id = int(rest[:last_underscore])
    description = rest[last_underscore+1:]
    
    user_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (seller_id, name, price, description, category_id) VALUES (?, ?, ?, ?, ?)",
              (user_id, name, price, description, cat_id))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"✅ **Product Added!**\n\n📌 {name}\n💰 ₹{price:,.2f}\n\nYour product is now live in the marketplace!",
                         call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_prod")
def cancel_product(call):
    bot.edit_message_text("❌ Product creation cancelled.", 
                         call.message.chat.id, call.message.message_id)
                         # ========== MY PRODUCTS ==========
@bot.callback_query_handler(func=lambda call: call.data == "my_products")
def my_products(call):
    user_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT p.id, p.name, p.price, p.is_active, c.name 
                 FROM products p JOIN categories c ON p.category_id = c.id
                 WHERE p.seller_id = ? ORDER BY p.created_date DESC''', (user_id,))
    products = c.fetchall()
    conn.close()
    
    if not products:
        bot.edit_message_text("📦 **My Products**\n\nYou haven't added any products yet.\nUse ➕ Add Product to start!",
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        return
    
    text = "📦 **My Products**\n\n"
    markup = InlineKeyboardMarkup(row_width=2)
    
    for p_id, p_name, p_price, is_active, cat_name in products:
        status = "✅ Active" if is_active else "❌ Inactive"
        text += f"📌 **{p_name}**\n💰 ₹{p_price:,.2f} | 📂 {cat_name} | {status}\n"
        markup.add(InlineKeyboardButton(f"✏️ {p_name}", callback_data=f"edit_prod_{p_id}"))
    
    if products:
        text += "\nSelect a product to manage:"
    
    markup.add(InlineKeyboardButton("◀️ Back to Dashboard", callback_data="seller_dashboard"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_prod_"))
def edit_product(call):
    product_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT p.name, p.price, p.description, p.is_active, c.name, p.category_id
                 FROM products p JOIN categories c ON p.category_id = c.id
                 WHERE p.id = ?''', (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "❌ Product not found!")
        return
    
    name, price, desc, is_active, cat_name, cat_id = product
    status = "✅ Active" if is_active else "❌ Inactive"
    
    text = (
        f"✏️ **Manage Product**\n\n"
        f"📌 Name: {name}\n"
        f"💰 Price: ₹{price:,.2f}\n"
        f"📂 Category: {cat_name}\n"
        f"📝 Description: {desc if desc else 'N/A'}\n"
        f"📊 Status: {status}\n\n"
        f"Choose action:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📛 Rename", callback_data=f"rename_{product_id}"),
        InlineKeyboardButton("💵 Change Price", callback_data=f"reprice_{product_id}"),
        InlineKeyboardButton("📝 Edit Desc", callback_data=f"redesc_{product_id}"),
        InlineKeyboardButton("📂 Change Category", callback_data=f"recat_{product_id}"),
    )
    
    toggle_text = "❌ Deactivate" if is_active else "✅ Activate"
    markup.add(
        InlineKeyboardButton(toggle_text, callback_data=f"toggle_{product_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{product_id}")
    )
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="my_products"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

# ========== EDIT: Rename ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("rename_"))
def rename_product(call):
    product_id = int(call.data.split("_")[1])
    msg = bot.edit_message_text("✏️ Enter new **Product Name**:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_rename, product_id)

def process_rename(message, product_id):
    new_name = message.text.strip()
    if len(new_name) < 2:
        bot.reply_to(message, "⚠️ Name too short!")
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE products SET name = ?, updated_date = datetime('now','localtime') WHERE id = ?",
              (new_name, product_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Product renamed to **{new_name}**!", parse_mode="Markdown")

# ========== EDIT: Reprice ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("reprice_"))
def reprice_product(call):
    product_id = int(call.data.split("_")[1])
    msg = bot.edit_message_text("💵 Enter new **Price (in ₹)**:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_reprice, product_id)

def process_reprice(message, product_id):
    try:
        price = float(message.text.strip().replace(',', ''))
        if price <= 0:
            raise ValueError
    except:
        bot.reply_to(message, "⚠️ Invalid price!")
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE products SET price = ?, updated_date = datetime('now','localtime') WHERE id = ?",
              (price, product_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Price updated to ₹{price:,.2f}!", parse_mode="Markdown")

# ========== EDIT: Description ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("redesc_"))
def redesc_product(call):
    product_id = int(call.data.split("_")[1])
    msg = bot.edit_message_text("📝 Enter new **Description** (or type 'clear' to remove):",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_redesc, product_id)

def process_redesc(message, product_id):
    desc = message.text.strip()
    if desc.lower() == 'clear':
        desc = ""
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE products SET description = ?, updated_date = datetime('now','localtime') WHERE id = ?",
              (desc, product_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Description updated!", parse_mode="Markdown")

# ========== EDIT: Change Category ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("recat_"))
def recat_product(call):
    product_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    
    markup = InlineKeyboardMarkup(row_width=2)
    for cat_id, cat_name in categories:
        markup.add(InlineKeyboardButton(cat_name, callback_data=f"setcat_{product_id}_{cat_id}"))
    
    bot.edit_message_text("📂 Select new **Category**:", call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcat_"))
def set_category(call):
    parts = call.data.split("_")
    product_id = int(parts[1])
    cat_id = int(parts[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE products SET category_id = ?, updated_date = datetime('now','localtime') WHERE id = ?",
              (cat_id, product_id))
    c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat_name = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"✅ Category changed to **{cat_name}**!", 
                         call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ========== EDIT: Toggle Active ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_product(call):
    product_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT is_active FROM products WHERE id = ?", (product_id,))
    current = c.fetchone()
    
    if current:
        new_status = 0 if current[0] else 1
        c.execute("UPDATE products SET is_active = ?, updated_date = datetime('now','localtime') WHERE id = ?",
                  (new_status, product_id))
        conn.commit()
        
        status_text = "activated" if new_status else "deactivated"
        bot.edit_message_text(f"✅ Product **{status_text}**!", 
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    conn.close()

# ========== EDIT: Delete ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_product(call):
    product_id = int(call.data.split("_")[1])
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"del_conf_{product_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"edit_prod_{product_id}")
    )
    
    bot.edit_message_text("⚠️ **Are you sure?** This cannot be undone!",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_conf_"))
def confirm_delete(call):
    product_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("🗑️ Product deleted successfully.", 
                         call.message.chat.id, call.message.message_id)

# ========== SELLER: VIEW CONTACTS ==========
@bot.callback_query_handler(func=lambda call: call.data == "seller_contacts")
def seller_contacts(call):
    user_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT cr.id, p.name, u.first_name, cr.message, cr.status, cr.created_date
                 FROM contact_requests cr 
                 JOIN products p ON cr.product_id = p.id 
                 JOIN users u ON cr.buyer_id = u.user_id
                 WHERE cr.seller_id = ? ORDER BY cr.created_date DESC LIMIT 20''', (user_id,))
    contacts = c.fetchall()
    conn.close()
    
    if not contacts:
        bot.edit_message_text("📩 **Contact Requests**\n\nNo contact requests yet.",
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        return
    
    text = "📩 **Contact Requests**\n\n"
    for c_id, p_name, buyer_name, msg, status, date in contacts:
        status_emoji = "⏳" if status == 'pending' else "✅" if status == 'accepted' else "⏭️"
        text += f"{status_emoji} **{p_name}** - {buyer_name}\n📝 {msg[:50]}\n📅 {date[:10]}\n━━━━━━━━━━\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="seller_dashboard"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")
                         # ========== REVIEW SYSTEM ==========
@bot.callback_query_handler(func=lambda call: call.data == "seller_reviews")
def seller_view_reviews(call):
    user_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT r.id, r.rating, r.review_text, r.status, p.name, r.created_date
                 FROM reviews r JOIN products p ON r.product_id = p.id
                 WHERE p.seller_id = ? ORDER BY r.created_date DESC''', (user_id,))
    reviews = c.fetchall()
    conn.close()
    
    if not reviews:
        bot.edit_message_text("⭐ **My Reviews**\n\nNo reviews yet.",
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        return
    
    text = "⭐ **My Reviews**\n\n"
    for r_id, rating, review_text, status, p_name, date in reviews:
        stars = "⭐" * rating + "☆" * (5 - rating)
        status_emoji = "⏳" if status == 'pending' else "✅"
        text += f"{stars} | {p_name}\n💬 {review_text[:80] if review_text else 'No comment'}\n📊 {status.title()} {status_emoji}\n━━━━━━━━━━\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="seller_dashboard"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

# ========== BUYER: LEAVE A REVIEW ==========
@bot.message_handler(func=lambda m: m.text == "⭐ My Reviews")
def my_reviews_menu(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # Products buyer has contacted about
    c.execute('''SELECT DISTINCT p.id, p.name, p.price, u.first_name
                 FROM contact_requests cr
                 JOIN products p ON cr.product_id = p.id
                 JOIN users u ON p.seller_id = u.user_id
                 WHERE cr.buyer_id = ? AND cr.status IN ('accepted', 'skipped')''', (user_id,))
    products = c.fetchall()
    
    # Their existing reviews
    c.execute("SELECT product_id, rating, review_text, status FROM reviews WHERE user_id = ?", (user_id,))
    existing_reviews = {r[0]: r for r in c.fetchall()}
    conn.close()
    
    text = "⭐ **My Reviews**\n\n"
    
    if existing_reviews:
        text += "**Your Reviews:**\n"
        for prod_id, (_, rating, review_text, status) in list(existing_reviews.items())[:5]:
            stars = "⭐" * rating + "☆" * (5 - rating)
            text += f"{stars} - {'✅ Approved' if status == 'approved' else '⏳ Pending'}\n"
        text += "\n"
    
    if products:
        text += "**Products you can review:**\n"
        markup = InlineKeyboardMarkup(row_width=1)
        for p_id, p_name, p_price, seller_name in products:
            if p_id not in existing_reviews or existing_reviews[p_id][3] != 'approved':
                markup.add(InlineKeyboardButton(f"⭐ Review {p_name}", callback_data=f"review_{p_id}"))
                text += f"📌 {p_name} - {seller_name}\n"
        
        if markup.keyboard:
            bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")
            return
    
    if not existing_reviews and not products:
        text += "No products to review yet. Contact a seller first!"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("review_"))
def review_product(call):
    product_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "❌ Product not found!")
        return
    
    markup = InlineKeyboardMarkup(row_width=5)
    row = []
    for i in range(1, 6):
        row.append(InlineKeyboardButton(f"{i}⭐", callback_data=f"rate_{product_id}_{i}"))
    markup.add(*row)
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="close"))
    
    bot.edit_message_text(f"⭐ **Rate {product[0]}**\n\nSelect rating (1-5 stars):",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def process_rating(call):
    parts = call.data.split("_")
    product_id = int(parts[1])
    rating = int(parts[2])
    
    msg = bot.edit_message_text(f"⭐ **Rating: {rating}/5**\n\nNow write a review (or type 'skip' to just submit rating):",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_review_text, product_id, rating)

def process_review_text(message, product_id, rating):
    user_id = message.from_user.id
    review_text = message.text.strip()
    
    if review_text.lower() == 'skip':
        review_text = ""
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # Check if already reviewed
    c.execute("SELECT id FROM reviews WHERE product_id = ? AND user_id = ?", (product_id, user_id))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE reviews SET rating = ?, review_text = ?, status = 'pending', created_date = datetime('now','localtime') WHERE id = ?",
                  (rating, review_text, existing[0]))
    else:
        c.execute("INSERT INTO reviews (product_id, user_id, rating, review_text) VALUES (?, ?, ?, ?)",
                  (product_id, user_id, rating, review_text))
    
    conn.commit()
    
    # Get product and seller info for admin notification
    c.execute("SELECT name, seller_id FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_review_{product_id}_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_review_{product_id}_{user_id}")
            )
            stars = "⭐" * rating
            bot.send_message(admin_id,
                f"📝 **New Review (Pending Approval)**\n\n"
                f"📦 Product: {product[0]}\n"
                f"⭐ Rating: {stars} ({rating}/5)\n"
                f"💬 Review: {review_text if review_text else 'No text'}\n"
                f"👤 By: User {user_id}",
                reply_markup=markup, parse_mode="Markdown")
        except:
            pass
    
    bot.reply_to(message, "✅ **Review Submitted!** It will be visible once approved by admin.", parse_mode="Markdown")
    # ========== ADMIN PANEL ==========
@bot.message_handler(func=lambda m: m.text == "👥 Pending Sellers")
def admin_pending_sellers(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, phone, shop_name, shop_description, request_date FROM seller_requests WHERE status = 'pending'")
    requests = c.fetchall()
    conn.close()
    
    if not requests:
        bot.reply_to(message, "✅ No pending seller requests.")
        return
    
    for req in requests:
        uid, uname, fname, phone, shop, desc, date = req
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_seller_{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_seller_{uid}")
        )
        bot.send_message(user_id,
            f"📝 **Seller Request**\n\n"
            f"👤 Name: {fname}\n"
            f"🆔 ID: {uid}\n"
            f"📧 @{uname}\n"
            f"🏪 Shop: {shop}\n"
            f"📝 Desc: {desc}\n"
            f"📞 Phone: {phone}\n"
            f"📅 {date}",
            reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⭐ Pending Reviews")
def admin_pending_reviews(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT r.id, r.rating, r.review_text, p.name, r.user_id, r.product_id
                 FROM reviews r JOIN products p ON r.product_id = p.id
                 WHERE r.status = 'pending' ORDER BY r.created_date DESC''')
    reviews = c.fetchall()
    conn.close()
    
    if not reviews:
        bot.reply_to(message, "✅ No pending reviews.")
        return
    
    for rev in reviews:
        rid, rating, text, pname, uid, pid = rev
        stars = "⭐" * rating
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_review_{pid}_{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_review_{pid}_{uid}")
        )
        bot.send_message(user_id,
            f"📝 **Pending Review**\n\n"
            f"📦 Product: {pname}\n"
            f"⭐ {stars} ({rating}/5)\n"
            f"💬 {text if text else 'No text'}\n"
            f"👤 By: {uid}",
            reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_review_"))
def approve_review(call):
    admin_id = call.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Unauthorized!")
        return
    
    parts = call.data.split("_")
    product_id = int(parts[2])
    reviewer_id = int(parts[3])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE reviews SET status = 'approved' WHERE product_id = ? AND user_id = ?",
              (product_id, reviewer_id))
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'approve_review', ?)",
              (admin_id, f"Approved review for product {product_id} by user {reviewer_id}"))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("✅ Review approved!",
                         call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_review_"))
def reject_review(call):
    admin_id = call.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Unauthorized!")
        return
    
    parts = call.data.split("_")
    product_id = int(parts[2])
    reviewer_id = int(parts[3])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE reviews SET status = 'rejected' WHERE product_id = ? AND user_id = ?",
              (product_id, reviewer_id))
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'reject_review', ?)",
              (admin_id, f"Rejected review for product {product_id} by user {reviewer_id}"))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("❌ Review rejected.",
                         call.message.chat.id, call.message.message_id)

# ========== ADMIN: STATS ==========
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def admin_stats(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'seller'")
    total_sellers = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'buyer'")
    total_buyers = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    active_products = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM categories")
    total_categories = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM contact_requests")
    total_contacts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reviews WHERE status = 'approved'")
    approved_reviews = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reviews WHERE status = 'pending'")
    pending_reviews = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM seller_requests WHERE status = 'pending'")
    pending_sellers = c.fetchone()[0]
    
    conn.close()
    
    text = (
        f"📊 **Marketplace Statistics**\n\n"
        f"👥 **Users:**\n"
        f"├ Total: {total_users}\n"
        f"├ Sellers: {total_sellers}\n"
        f"└ Buyers: {total_buyers}\n\n"
        f"📦 **Products:**\n"
        f"├ Total: {total_products}\n"
        f"└ Active: {active_products}\n\n"
        f"📂 Categories: {total_categories}\n"
        f"📩 Contacts: {total_contacts}\n\n"
        f"⭐ **Reviews:**\n"
        f"├ Approved: {approved_reviews}\n"
        f"└ Pending: {pending_reviews}\n\n"
        f"⏳ Pending Seller Requests: {pending_sellers}"
    )
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ========== ADMIN: CATEGORIES CRUD ==========
@bot.message_handler(func=lambda m: m.text == "📂 Categories")
def admin_categories(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT id, name, description FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    
    text = "📂 **Manage Categories**\n\n"
    markup = InlineKeyboardMarkup(row_width=2)
    
    for cat_id, cat_name, cat_desc in categories:
        text += f"🆔 {cat_id} | **{cat_name}**\n📝 {cat_desc[:50] if cat_desc else 'N/A'}\n\n"
        markup.add(InlineKeyboardButton(f"✏️ {cat_name}", callback_data=f"admin_cat_{cat_id}"))
    
    markup.add(InlineKeyboardButton("➕ Add Category", callback_data="add_category"))
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_cat_"))
def admin_edit_category(call):
    cat_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT name, description FROM categories WHERE id = ?", (cat_id,))
    cat = c.fetchone()
    conn.close()
    
    if not cat:
        bot.answer_callback_query(call.id, "❌ Category not found!")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✏️ Rename", callback_data=f"cat_rename_{cat_id}"),
        InlineKeyboardButton("📝 Edit Desc", callback_data=f"cat_desc_{cat_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"cat_del_{cat_id}"),
        InlineKeyboardButton("◀️ Back", callback_data="close")
    )
    
    bot.edit_message_text(f"📂 **{cat[0]}**\n\n📝 {cat[1]}\n\nChoose action:",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "add_category")
def add_category_prompt(call):
    msg = bot.edit_message_text("➕ **Add New Category**\n\nEnter category name:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_new_category_name)

def process_new_category_name(message):
    name = message.text.strip()
    if len(name) < 2:
        bot.reply_to(message, "⚠️ Name too short!")
        return
    
    msg = bot.reply_to(message, f"Category: **{name}**\n\nEnter description:")
    bot.register_next_step_handler(msg, process_new_category_desc, name)

def process_new_category_desc(message, name):
    desc = message.text.strip()
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, desc))
        conn.commit()
        bot.reply_to(message, f"✅ Category **{name}** added!")
    except sqlite3.IntegrityError:
        bot.reply_to(message, f"⚠️ Category '{name}' already exists!")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_rename_"))
def cat_rename_prompt(call):
    cat_id = int(call.data.split("_")[2])
    msg = bot.edit_message_text("✏️ Enter new category name:",
                                call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(msg, process_cat_rename, cat_id)

def process_cat_rename(message, cat_id):
    new_name = message.text.strip()
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cat_id))
        conn.commit()
        bot.reply_to(message, f"✅ Category renamed to **{new_name}**!", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "⚠️ A category with that name already exists!")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_desc_"))
def cat_desc_prompt(call):
    cat_id = int(call.data.split("_")[2])
    msg = bot.edit_message_text("📝 Enter new description:",
                                call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(msg, process_cat_desc, cat_id)

def process_cat_desc(message, cat_id):
    new_desc = message.text.strip()
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("UPDATE categories SET description = ? WHERE id = ?", (new_desc, cat_id))
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Description updated!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_del_"))
def cat_delete_confirm(call):
    cat_id = int(call.data.split("_")[2])
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"cat_delconf_{cat_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data="close")
    )
    
    bot.edit_message_text("⚠️ **Delete this category?** Products in this category will be set to 'Others'.",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_delconf_"))
def cat_delete_final(call):
    cat_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    # Move products to "Others" category
    c.execute("SELECT id FROM categories WHERE name = 'Others'")
    others = c.fetchone()
    others_id = others[0] if others else None
    
    if others_id:
        c.execute("UPDATE products SET category_id = ? WHERE category_id = ?", (others_id, cat_id))
    
    c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("🗑️ Category deleted. Products moved to 'Others'.",
                         call.message.chat.id, call.message.message_id)

# ========== ADMIN: ALL PRODUCTS ==========
@bot.message_handler(func=lambda m: m.text == "📦 All Products")
def admin_all_products(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT p.id, p.name, p.price, p.is_active, u.first_name, c.name
                 FROM products p JOIN users u ON p.seller_id = u.user_id
                 JOIN categories c ON p.category_id = c.id
                 ORDER BY p.created_date DESC LIMIT 20''')
    products = c.fetchall()
    conn.close()
    
    if not products:
        bot.reply_to(message, "📦 No products in the marketplace.")
        return
    
    text = "📦 **All Products (Last 20)**\n\n"
    markup = InlineKeyboardMarkup(row_width=2)
    
    for p_id, p_name, p_price, is_active, s_name, c_name in products:
        status = "✅" if is_active else "❌"
        text += f"{status} **{p_name}** - ₹{p_price:,.0f}\n👤 {s_name} | 📂 {c_name}\n"
        markup.add(InlineKeyboardButton(f"⚙️ {p_name[:20]}", callback_data=f"admin_prod_{p_id}"))
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_prod_"))
def admin_manage_product(call):
    product_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute('''SELECT p.name, p.price, p.is_active, u.first_name, c.name
                 FROM products p JOIN users u ON p.seller_id = u.user_id
                 JOIN categories c ON p.category_id = c.id
                 WHERE p.id = ?''', (product_id,))
    p = c.fetchone()
    conn.close()
    
    if not p:
        bot.answer_callback_query(call.id, "❌ Product not found!")
        return
    
    status = "✅ Active" if p[2] else "❌ Inactive"
    toggle_text = "❌ Deactivate" if p[2] else "✅ Activate"
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(toggle_text, callback_data=f"admin_toggle_{product_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"admin_del_{product_id}")
    )
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="close"))
    
    bot.edit_message_text(f"⚙️ **{p[0]}**\n💰 ₹{p[1]:,.2f}\n👤 Seller: {p[3]}\n📂 {p[4]}\n📊 {status}",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_toggle_"))
def admin_toggle_product(call):
    product_id = int(call.data.split("_")[2])
    admin_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT is_active FROM products WHERE id = ?", (product_id,))
    current = c.fetchone()
    
    if current:
        new_status = 0 if current[0] else 1
        c.execute("UPDATE products SET is_active = ?, updated_date = datetime('now','localtime') WHERE id = ?",
                  (new_status, product_id))
        c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'toggle_product', ?)",
                  (admin_id, f"{'Activated' if new_status else 'Deactivated'} product {product_id}"))
        conn.commit()
        
        status_text = "activated" if new_status else "deactivated"
        bot.edit_message_text(f"✅ Product **{status_text}**!",
                             call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_"))
def admin_delete_product(call):
    product_id = int(call.data.split("_")[2])
    admin_id = call.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'delete_product', ?)",
              (admin_id, f"Deleted product {product_id}"))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("🗑️ Product deleted.",
                         call.message.chat.id, call.message.message_id)
                         # ========== ADMIN: ALL USERS ==========
@bot.message_handler(func=lambda m: m.text == "👥 All Users")
def admin_users(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, role, joined_date FROM users ORDER BY joined_date DESC")
    users = c.fetchall()
    conn.close()
    
    if not users:
        bot.reply_to(message, "No users found.")
        return
    
    text = "👥 **All Users**\n\n"
    for uid, uname, fname, role, date in users:
        text += f"🆔 {uid}\n👤 {fname} (@{uname})\n📊 {role.title()}\n📅 {date[:10]}\n━━━━━━━━━━\n"
    
    # Split into multiple messages if too long
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000], parse_mode="Markdown")
    else:
        bot.reply_to(message, text, parse_mode="Markdown")

# ========== ADMIN: BROADCAST ==========
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_start(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 All Users", callback_data="bcast_all"),
        InlineKeyboardButton("💼 All Sellers", callback_data="bcast_sellers"),
        InlineKeyboardButton("🛍️ All Buyers", callback_data="bcast_buyers"),
        InlineKeyboardButton("❌ Cancel", callback_data="close")
    )
    
    bot.reply_to(message, "📢 **Send Broadcast**\n\nSelect target audience:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("bcast_"))
def broadcast_target(call):
    target = call.data.split("_")[1]
    
    msg = bot.edit_message_text(f"📢 **Broadcast to {'All Users' if target == 'all' else target.title()}**\n\nEnter your message:",
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_broadcast, target)

def process_broadcast(message, target):
    admin_id = message.from_user.id
    broadcast_text = message.text.strip()
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    
    if target == 'all':
        c.execute("SELECT user_id FROM users")
    elif target == 'sellers':
        c.execute("SELECT user_id FROM users WHERE role = 'seller'")
    elif target == 'buyers':
        c.execute("SELECT user_id FROM users WHERE role = 'buyer' OR role IS NULL")
    
    users = c.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for (uid,) in users:
        if uid == admin_id:
            continue
        try:
            bot.send_message(uid, f"📢 **Broadcast Message**\n\n{broadcast_text}", parse_mode="Markdown")
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    # Log
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("INSERT INTO admin_logs (admin_id, action, details) VALUES (?, 'broadcast', ?)",
              (admin_id, f"Sent broadcast to {target}: {success} sent, {failed} failed"))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"📢 **Broadcast Complete**\n\n✅ Sent: {success}\n❌ Failed: {failed}\n🎯 Target: {target.title()}", parse_mode="Markdown")

# ========== ADMIN: LOGS ==========
@bot.message_handler(func=lambda m: m.text == "📋 Logs")
def admin_logs(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT admin_id, action, details, timestamp FROM admin_logs ORDER BY timestamp DESC LIMIT 20")
    logs = c.fetchall()
    conn.close()
    
    if not logs:
        bot.reply_to(message, "📋 No logs yet.")
        return
    
    text = "📋 **Admin Logs (Last 20)**\n\n"
    for aid, action, details, ts in logs:
        text += f"🕐 {ts}\n👤 Admin: {aid}\n📌 {action.upper()}\n📝 {details}\n━━━━━━━━━━\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ========== ADMIN: MAIN MENU BUTTON ==========
@bot.message_handler(func=lambda m: m.text == "🔙 Main Menu")
def back_to_main_menu(message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        bot.reply_to(message, "📋 Back to Admin Panel:", reply_markup=admin_main_menu())
    else:
        bot.reply_to(message, "📋 Main Menu:", reply_markup=main_menu_keyboard())

# ========== BUYER MODE FOR SELLERS ==========
@bot.callback_query_handler(func=lambda call: call.data == "buyer_menu")
def buyer_menu(call):
    markup = main_menu_keyboard()
    bot.edit_message_text("🛍️ **Buyer Mode**\n\nUse the buttons below to browse and shop!",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

# ========== PROFILE ==========
@bot.message_handler(func=lambda m: m.text == "👤 My Profile")
def show_profile(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('marketplace.db')
    c = conn.cursor()
    c.execute("SELECT username, first_name, role, phone, joined_date FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    
    if user:
        uname, fname, role, phone, joined = user
        text = (
            f"👤 **My Profile**\n\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Name: {fname or 'N/A'}\n"
            f"📧 Username: @{uname or 'N/A'}\n"
            f"📊 Role: {role.title() if role else 'Buyer'}\n"
            f"📞 Phone: {phone or 'Not set'}\n"
            f"📅 Joined: {joined[:10] if joined else 'Today'}"
        )
        
        if role == 'seller':
            c.execute("SELECT COUNT(*) FROM products WHERE seller_id = ?", (user_id,))
            prod_count = c.fetchone()[0]
            text += f"\n\n📦 Products Listed: {prod_count}"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    conn.close()

# ========== HELP ==========
@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_command(message):
    help_text = (
        "❓ **Marketplace Bot Help**\n\n"
        "**For Buyers:**\n"
        "🛍️ Browse Products - View products by category\n"
        "🔍 Search - Find specific products\n"
        "📞 Contact Seller - Get in touch with sellers\n"
        "⭐ Leave Reviews - Rate products you've bought\n\n"
        "**For Sellers:**\n"
        "📋 Dashboard - Manage your shop\n"
        "➕ Add Product - List new items\n"
        "📦 My Products - Edit/delete your listings\n"
        "📩 Contact Requests - View buyer inquiries\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/menu - Show main menu\n"
        "/cancel - Cancel current action\n"
        "/help - Show this help"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_command(message)

@bot.message_handler(commands=['cancel'])
def cancel(message):
    bot.reply_to(message, "✅ Action cancelled.")
    
    # Remove any pending next_step_handlers
    bot.clear_step_handler(message)

# ========== BACK TO MAIN (CALLBACK) ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    user_id = call.from_user.id
    
    if user_id in ADMIN_IDS:
        bot.edit_message_text("📋 Admin Panel:", call.message.chat.id, call.message.message_id,
                             reply_markup=admin_main_menu())
    else:
        role = get_user_role(user_id)
        if role == 'seller':
            bot.edit_message_text("📋 Seller Mode:", call.message.chat.id, call.message.message_id,
                                 reply_markup=main_menu_keyboard())
        else:
            bot.edit_message_text("📋 Main Menu:", call.message.chat.id, call.message.message_id,
                                 reply_markup=main_menu_keyboard())

# ========== CLOSE CALLBACK ==========
@bot.callback_query_handler(func=lambda call: call.data == "close")
def close_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ========== UNKNOWN HANDLER ==========
@bot.message_handler(func=lambda m: True)
def unknown_command(message):
    user_id = message.from_user.id
    
    # If admin, ignore text and stay in admin panel
    if user_id in ADMIN_IDS:
        return
    
    bot.reply_to(message, "I don't understand that command. Use /menu to see available options.")

# ========== MAIN ==========
if __name__ == "__main__":
    print("🚀 Starting Marketplace Bot...")
    init_db()
    print("✅ Database initialized with default categories.")
    print(f"✅ Admin IDs: {ADMIN_IDS}")
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
            
