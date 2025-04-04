import sqlite3
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import os
from datetime import datetime, timedelta

# Generic states
# STEP_1, STEP_2, STEP_3, STEP_4 = range(4)
STATE = {
    "OPTION": None,
    "MAIN_CATEGORY": None,
    "CATEGORY": None,
    "CATEGORY_ID": None,
    "AMOUNT": None,
    "TRANSACTION_ID": None,
    "USER": None,
    "BALANCE": None,
    "PLANNED": None,
}

USER_ID_1 = 7776960236 # Add your telegram user ID #1 here
USER_ID_2 = 1234567891 # Add your telegram user ID #2 here

USER_NAME_1 = "Lord" # Your name #1 (any string)
USER_NAME_2 = "DEF" # Your name #2 (any string)

TOKEN = '7921341221:AAHdJY3CiswKWYx7mNiua4tgj2BLaS8i_ps'

def reset_state(option=True, main_category=True, category=True, amount=True, user=True, balance=True, limit=True, transaction=True, category_id=True):
    if option:
        STATE["OPTION"] = None
    if main_category:
        STATE["MAIN_CATEGORY"] = None
    if category:
        STATE["CATEGORY"] = None
    if amount:
        STATE["AMOUNT"] = None
    if user:
        STATE["USER"] = None
    if balance:
        STATE["BALANCE"] = None
    if limit:
        STATE["PLANNED"] = None
    if transaction:
        STATE["TRANSACTION_ID"] = None
    if category_id:
        STATE["CATEGORY_ID"] = None

# Function to get the current month's database name (based on year and month)
def get_db_name():
    current_month = datetime.now().strftime("%Y_%m")  # Format as 'YYYY_MM'
    return f"finance_{current_month}.db"

# Function to initialize the database schema if it doesn't exist
def init_db():
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # users table: id, name
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # categories table: id, name, limit, main_category
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        "limit" REAL NOT NULL, 
        main_category TEXT NOT NULL,
        UNIQUE(name, main_category)
    )
    """)

    # records table: id, user_id, category_id, amount, timestamp, note
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        timestamp DATETIME DEFAULT (datetime('now','localtime')),
        note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """)
    
    # # records table: id, user_id, category, amount, timestamp, note
    # cursor.execute("""
    # CREATE TABLE IF NOT EXISTS records (
    #     id INTEGER PRIMARY KEY AUTOINCREMENT,
    #     user_id INTEGER NOT NULL,
    #     category TEXT NOT NULL,
    #     amount REAL NOT NULL,
    #     timestamp DATETIME DEFAULT (datetime('now','localtime')),
    #     note TEXT
    # )
    # """)
    # timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    # balance table: id, user_id, amount
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS balance (
        user_id INTEGER NOT NULL PRIMARY KEY,
        amount REAL NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# Function to check if the user is authorized (add user IDs in the list)
def is_authorized(update: Update):
    authorized_users = [USER_ID_1, USER_ID_2]  # Add authorized user IDs here
    return update.effective_user.id in authorized_users

# Function to init user info
def init_user():
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Check if the user is already in the database
    cursor.execute("SELECT id FROM users WHERE id = ?", (USER_ID_1,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (id, name) VALUES (?, ?)", (USER_ID_1, 'USER_NAME_1'))
        
    cursor.execute("SELECT id FROM users WHERE id = ?", (USER_ID_2,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (id, name) VALUES (?, ?)", (USER_ID_2, 'USER_NAME_2'))
    
    conn.commit()
    conn.close()
    
# Function to get user name
def get_user_name(user_id):
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Unknown"

# Function to initialize balance from the previous month or set to 0 if not available
def initialize_balance():
    current_db_name = get_db_name()
    current_month = datetime.now().strftime("%Y_%m")  # Format as 'YYYY_MM'
    previous_month = current_month[:-2] + str(int(current_month[-2:]) - 1).zfill(2)  # Get previous month
    previous_db_name = f"finance_{previous_month}.db"
    print(f"Current month: {current_month}, Previous month: {previous_month}")
    
    # get the current balance
    conn = sqlite3.connect(current_db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM balance")
    result = cursor.fetchall()
    if result:
        current_balance = {}
        for user_id, balance in result:
            current_balance[user_id] = balance
        conn.close()
    else:
        # If the current month's database is empty, initialize the database based on the previous month's data
        current_balance = {USER_ID_1: 0, USER_ID_2: 0}
    
        # Check if a previous month's database exists
        if os.path.exists(previous_db_name):
            prev_conn = sqlite3.connect(previous_db_name)
            prev_cursor = prev_conn.cursor()
            
            # Query the previous month's database for the balance
            # current_balance = {}
            for user_id in [USER_ID_1, USER_ID_2]:
                # current_balance[user_id] = 0
                prev_cursor.execute("SELECT amount FROM balance WHERE user_id = ?", (user_id,))
                result = prev_cursor.fetchone()
                if result:
                    current_balance[user_id] += result[0]
                    print(f"Balance found for {get_user_name(user_id)}: {current_balance[user_id]}")
                else:
                    print(f"No balance found for user {get_user_name(user_id)}")
            print(f"Previous month initial balance: {current_balance}")
            
            # Calculate total income and expenses for the previous month based on user ID
            for user_id in [USER_ID_1, USER_ID_2]:
                prev_cursor.execute("""
                SELECT SUM(r.amount) FROM records r
                JOIN categories c ON r.category = c.name
                WHERE c.main_category = 'income' AND r.user_id = ?
                """, (user_id,))
                income = prev_cursor.fetchone()[0] or 0
                print(f"Previous month income for {get_user_name(user_id)}: {income}")

                prev_cursor.execute("""
                SELECT SUM(r.amount) FROM records r
                JOIN categories c ON r.category = c.name
                WHERE c.main_category = 'expense' AND r.user_id = ?
                """, (user_id,))
                expenses = prev_cursor.fetchone()[0] or 0
                print(f"Previous month expenses for {get_user_name(user_id)}: {expenses}")

                # Remaining balance from the previous month
                remaining_balance = income - expenses + current_balance[user_id]
                print(f"Previous month remaining balance for {get_user_name(user_id)}: {remaining_balance}")

                # Set the current balance to the remaining balance from the previous month
                current_balance[user_id] = remaining_balance
                
            prev_conn.close()

    # Now set the balance in the new month’s database
    conn = sqlite3.connect(current_db_name)
    cursor = conn.cursor()
    for user_id in [USER_ID_1, USER_ID_2]:
        cursor.execute("REPLACE INTO balance (user_id, amount) VALUES (?, ?)", (user_id, current_balance[user_id]))
    conn.commit()
    conn.close()
    
# Function to initialize categories
def initialize_categories():
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Check if the categories are already in the database
    # initialize income categories
    subcategories = ['investment'   , 'salary'  , 'loan']
    limits =        [15000          , 5000      , 0     ] 
    main_category = 'income'
    for subcategory_id, subcategory in enumerate(subcategories):
        cursor.execute("SELECT name FROM categories WHERE name = ?", (subcategory,))
        result = cursor.fetchone()
        if not result:
            print(f"Inserting {subcategory} with limit {limits[subcategory_id]}")
            cursor.execute("INSERT INTO categories (name, 'limit', main_category) VALUES (?, ?, ?)", (subcategory, limits[subcategory_id], main_category))
            
    subcategories = ['cafe' , 'food', 'subway'  , 'bills'   , 'rent']
    limits =        [100    , 400   , 62 + 62   , 300       , 650]
    main_category = 'expense'
    for subcategory_id, subcategory in enumerate(subcategories):
        cursor.execute("SELECT name FROM categories WHERE name = ?", (subcategory,))
        result = cursor.fetchone()
        if not result:
            print(f"Inserting {subcategory} with limit {limits[subcategory_id]}")
            cursor.execute("INSERT INTO categories (name, 'limit', main_category) VALUES (?, ?, ?)", (subcategory, limits[subcategory_id], main_category))
            
    conn.commit()
    conn.close()

# Function to set the balance for the user
def set_balance(update: Update, user_id: int, balance: float):
    if not is_authorized(update):
        update.message.reply_text("Unauthorized access!")
        return

    try:
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT amount FROM balance WHERE user_id = ?", (user_id,))
        existing_balance = cursor.fetchone()
        if existing_balance:
            print(f"Existing balance: {existing_balance[0]}")

        cursor.execute("REPLACE INTO balance (user_id, amount) VALUES (?, ?)", (user_id, balance))
        conn.commit()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f"Balance successfully updated to {balance} for {get_user_name(user_id)}", reply_markup=reply_markup)
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("❕ Please provide a valid balance.", reply_markup=reply_markup)

# Add a transaction (income or expense)
def add_transaction(update: Update, category_id: str, amount: float, note, user_name=USER_NAME_1):
    if not is_authorized(update):
        update.message.reply_text("Unauthorized access!")
        return

    try:
        if user_name == USER_NAME_1:
            user_id = USER_ID_1
        elif user_name == USER_NAME_2:
            user_id = USER_ID_2
        else:
            update.message.reply_text("User not found!")
            return
        
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # # check if the category exists
        # cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
        # result = cursor.fetchone()
        # if not result:
        #     update.message.reply_text("\U0001F605 This category doesn't exist. Use /addcat <in/out> <category> <limit> to add.")
        #     return

        cursor.execute("INSERT INTO records (user_id, category_id, amount, note) VALUES (?, ?, ?, ?)", (user_id, category_id, amount, note))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.message.reply_text(f"✅ A transaction of {amount} has been added.", reply_markup=reply_markup)
        except Exception as e:
            update.callback_query.edit_message_text(f"✅ A transaction of {amount} has been added.", reply_markup=reply_markup)
    except Exception as e:
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.message.reply_text("❕ Please provide a valid amount and category.", reply_markup=reply_markup)
        except Exception as e:
            update.callback_query.edit_message_text("❕ Please provide a valid amount and category.", reply_markup=reply_markup)

# Add a category (income or expense)
def add_category(update: Update, main_category: str, subcategory: str, limit: float):
    if not is_authorized(update):
        update.message.reply_text("Unauthorized access!")
        return

    try:
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # If it's 'income', insert the category directly
        if main_category == "income":
            cursor.execute("INSERT INTO categories (name, 'limit', main_category) VALUES (?, ?, ?)",
                            (subcategory, limit, main_category))
        
        # If it's 'expense', handle subcategory and insert it
        elif main_category == "expense" and subcategory:
            cursor.execute("INSERT INTO categories (name, 'limit', main_category) VALUES (?, ?, ?)",
                           (subcategory, limit, main_category))

        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if subcategory:
            update.message.reply_text(f"✅ '{subcategory}' with a planned limit of {limit} has been added to '{main_category}'.", reply_markup=reply_markup)
        else:
            update.message.reply_text(f"✅ '{subcategory}' with a planned limit of {limit} has been added to '{main_category}'.", reply_markup=reply_markup)
    except Exception as e:
        print(f"Error in add_category: {e}")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("❕ Please provide a valid category and limit. Please double-check the category name, it might already exist.", reply_markup=reply_markup)

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2 formatting."""
    special_chars = r'_\*[\](`~>#+-.!|)'  # List of characters that need escaping in MarkdownV2
    for char in special_chars:
        text = text.replace(char, '\\' + char)  # Escape each special character
    return text

# Summarize current/expected balance based on income and expenses
def summarize(update: Update, context: CallbackContext):
    if not is_authorized(update):
        update.message.reply_text("Unauthorized access!")
        return

    try:
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT id, name, "limit", main_category FROM categories')
        categories = cursor.fetchall()

        if not categories:
            update.message.reply_text("\U0001F605 database is empty.")
            conn.close()
            return

        # Get balance for each user
        current_balance = 0
        for user_id in [USER_ID_1, USER_ID_2]:
            cursor.execute("SELECT amount FROM balance WHERE user_id = ?", (user_id,))
            user_balance = cursor.fetchone()
            current_balance += user_balance[0] if user_balance else 0

        # Calculate expected and real amounts
        expected_income = 0
        expected_expense = 0
        real_income = 0
        real_expense = 0

        detailed_income = []
        detailed_expense = []
        
        # Calculate expected and real amounts for each category
        for category_id, name, limit, main_category in categories:
            cursor.execute("SELECT SUM(amount) FROM records WHERE category_id = ?", (category_id,))
            real_amount = cursor.fetchone()[0] or 0
            if main_category == "income":
                expected_income += limit
                real_income += real_amount
                detailed_income.append([name, limit, real_amount])
            elif main_category == "expense":
                expected_expense += limit
                real_expense += real_amount
                detailed_expense.append([name, limit, real_amount])

        remaining_balance = current_balance + real_income - real_expense
            
        # Build the table header and rows
        col_1_width = 7
        col_2_width = 8
        col_3_width = 8
        col_4_width = 8
        table_header_sum = "{:<{width1}}|{:<{width2}}|{:<{width3}}|{:<{width4}}\n".format("", "  plan", "  real", "  remain", width1=col_1_width, width2=col_2_width, width3=col_3_width, width4=col_4_width) + "-" * (col_1_width + col_2_width + col_3_width + col_4_width) + "\n"
        # table_header = "{:<{width1}}| {:<{width2}}| {:<{width3}}\n".format("", "plan", "real", width1=col_1_width, width2=col_2_width, width3=col_3_width) + "-" * (col_1_width + col_2_width + col_3_width) + "\n"
        
        # Build summary table
        # Escape the markdown special characters, including '.' with '\\.'
        summary_table = "\n".join(
            [f"{escape_markdown_v2(category).ljust(col_1_width)}|" + "{:.1f}".format(limit).rjust(col_2_width) + "|" + "{:.1f}".format(real).rjust(col_3_width) + "|" + "{:.1f}".format(limit - real).rjust(col_4_width) for category, limit, real in [["income", expected_income, real_income], ["expense", expected_expense, real_expense]]]
            # [f"{escape_markdown_v2(category).ljust(col_1_width)}| " + "{:.1f}".format(limit).ljust(col_2_width) + "|" + "{:.1f}".format(real).ljust(col_3_width) for category, limit, real in [["income", expected_income, real_income], ["expense", expected_expense, real_expense]]]
        )
        
        col_1_width = 7
        col_2_width = 8
        col_3_width = 8
        col_4_width = 8
        table_header_income = "{:<{width1}}|{:<{width2}}|{:<{width3}}|{:<{width4}}\n".format("", "  plan", "  real", "  remain", width1=col_1_width, width2=col_2_width, width3=col_3_width, width4=col_4_width) + "-" * (col_1_width + col_2_width + col_3_width + col_4_width) + "\n"
        # table_header_income = "{:<{width1}}| {:<{width2}}| {:<{width3}}\n".format("", "plan", "real", width1=col_1_width, width2=col_2_width, width3=col_3_width) + "-" * (col_1_width + col_2_width + col_3_width) + "\n"
        # Build detailed income table
        detailed_income_table = "\n".join(
            [f"{escape_markdown_v2(shorten_text(category, col_1_width, False)).ljust(col_1_width)}|" + "{:.1f}".format(limit).rjust(col_2_width) + "|" + "{:.1f}".format(real).rjust(col_3_width) + "|" + "{:.1f}".format(limit - real).rjust(col_4_width) for category, limit, real in detailed_income]
            # [f"{escape_markdown_v2(category).ljust(col_1_width)}| " + "{:.1f}".format(limit).ljust(col_2_width) + "|" + "{:.1f}".format(real).ljust(col_3_width) for category, limit, real in detailed_income]
        )

        col_1_width = 7
        col_2_width = 8
        col_3_width = 8
        col_4_width = 8
        table_header_expense = "{:<{width1}}|{:<{width2}}|{:<{width3}}|{:<{width4}}\n".format("", "  plan", "  real", "  remain", width1=col_1_width, width2=col_2_width, width3=col_3_width, width4=col_4_width) + "-" * (col_1_width + col_2_width + col_3_width + col_4_width) + "\n"
        # table_header_expense = "{:<{width1}}| {:<{width2}}| {:<{width3}}\n".format("", "plan", "real", width1=col_1_width, width2=col_2_width, width3=col_3_width) + "-" * (col_1_width + col_2_width + col_3_width) + "\n"
        # Build detailed expense table
        detailed_expense_table = "\n".join(
            [f"{escape_markdown_v2(shorten_text(category, col_1_width, False)).ljust(col_1_width)}|" + "{:.1f}".format(limit).rjust(col_2_width) + "|" + "{:.1f}".format(real).rjust(col_3_width) + "|" + "{:.1f}".format(limit - real).rjust(col_4_width) for category, limit, real in detailed_expense]
            # [f"{escape_markdown_v2(category).ljust(col_1_width)}| " + "{:.1f}".format(limit).ljust(col_2_width) + "|" + "{:.1f}".format(real).ljust(col_3_width) for category, limit, real in detailed_expense]
            # [f"{escape_markdown_v2(category).ljust(col_1_width)}| {str(limit).ljust(col_2_width)}| {str(real).ljust(col_3_width)}" for category, limit, real in detailed_expense]
        )
        
        # Create a summary text
        summary_text = (
            f"*💰 Income summary:*\n"
            f"```\n{table_header_income}{detailed_income_table}\n```\n\n"
            f"*💸 Expense summary:*\n"
            f"```\n{table_header_expense}{detailed_expense_table}\n```"
            f"\n\n*🏧 Overview:*\n"
            f" - Last month balance: " + "{:.1f}".format(current_balance) + "\n"
            f" - Current balance: " + "{:.1f}".format(remaining_balance) + "\n"
            f"```\n{table_header_sum}{summary_table}\n```\n\n"
        )
        
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
                                    
        update.callback_query.edit_message_text(summary_text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        print("Error in summarize")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
        
def shorten_text(text: str, max_length: int, with_dots=True) -> str:
    if with_dots:
        return (text[:max_length] + '...') if len(text) > max_length else text
    else:
        return text[:max_length] if len(text) > max_length else text
        
# Function to get detailed transaction information for income/expenses
def detail_transaction(update: Update, category: str):
    if not is_authorized(update):
        update.message.reply_text("Unauthorized access!")
        return

    # try:
    main_category = category

    if main_category == "in":
        main_category = "income"
    elif main_category == "out":
        main_category = "expense"
    
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # category in records is subcategory of category in categories
    cursor.execute("SELECT category_id, categories.name, amount, timestamp, note FROM records JOIN categories ON records.category_id = categories.id WHERE main_category = ?", (main_category,))
    transactions = cursor.fetchall()
        
    if not transactions:
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(f"❕ No transactions found.", reply_markup=reply_markup)
        conn.close()
        return
    
    # Build the table header and rows
    col_1_width = 5
    col_2_width = 8
    col_3_width = 5
    col_4_width = 7
    
    table_header = "{:<{width1}}|{:<{width2}}|{:<{width3}}|{:<{width4}}\n".format("", " amount", "date", "note", width1=col_1_width, width2=col_2_width, width3=col_3_width, width4=col_4_width) + "-" * (col_1_width + col_2_width + col_3_width + col_4_width) + "\n"
    # table_header = "{:<{width1}}| {:<{width2}}| {:<{width3}}\n".format("", "amount", "date", width1=col_1_width, width2=col_2_width, width3=col_3_width) + "-" * (col_1_width + col_2_width + col_3_width) + "\n"

    # Build detailed transaction table
    detailed_transaction_table = ""
    for category_id, category, amount, timestamp, note in transactions:
        category = escape_markdown_v2(category)
        # keep only month and day
        timestamp = timestamp[5:10]
        note = escape_markdown_v2(note) if note else ""
        print(category, amount, timestamp, note)
        detailed_transaction = "\n".join(
            [f"{shorten_text(category, col_1_width, False).ljust(col_1_width)}|" + "{:.1f}".format(amount).rjust(col_2_width) + "|" + timestamp.ljust(col_3_width) + "|" + shorten_text(note, col_4_width).ljust(col_4_width)]
        # detailed_transaction = "\n".join(
        #     [f"{category.ljust(col_1_width)}| " + "{:.1f}".format(amount).ljust(col_2_width) + "|" + timestamp.ljust(col_3_width)]
            # [f"{category.ljust(col_1_width)}| {str(amount).ljust(col_2_width)}| {str(timestamp).ljust(col_3_width)}"]
        )
        detailed_transaction_table = detailed_transaction_table + detailed_transaction + "\n"
    
    # Create a detailed transaction text
    detailed_transaction_text = (
        f"*Detailed {main_category} transactions:*\n"
        f"```\n{table_header}{detailed_transaction_table}\n```"
    )
    
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data='view_transactions')],
        [InlineKeyboardButton("❌ Close", callback_data='home')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)    

    update.callback_query.edit_message_text(detailed_transaction_text, parse_mode='Markdown', reply_markup=reply_markup)
    # except Exception as e:
    #     keyboard = [
    #         [InlineKeyboardButton("❌ Close", callback_data='home')]
    #     ]
    #     reply_markup = InlineKeyboardMarkup(keyboard)
        
    #     update.callback_query.edit_message_text(f"❌ Database for {category} might be empty.", reply_markup=reply_markup)

def view_main_category(update: Update, context: CallbackContext, backto_loc='home', backto_text='⬅️ Back'):
    try:
        keyboard = [
            [InlineKeyboardButton("Income", callback_data='mcat:income')],
            [InlineKeyboardButton("Expense", callback_data='mcat:expense')],
            [InlineKeyboardButton("❌ Cancel", callback_data='home')],
            # [InlineKeyboardButton(backto_text, callback_data=backto_loc)],
        ]    
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(text="Choose one of the follows:", reply_markup=reply_markup)
    except Exception as e:
        print("Error in view_main_category")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
    
def view_category(update: Update, context: CallbackContext, backto_loc='view_main_category', backto_text='⬅️ Back'):
    try:
        # Loop through the income categories and create buttons
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        main_category = STATE["MAIN_CATEGORY"]
        if not main_category:
            return
        
        cursor.execute("SELECT id, name FROM categories WHERE main_category = ?", (main_category,))
        categories = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(category[1], callback_data=f'scat:' + str(category[0]))])
        # keyboard.append([InlineKeyboardButton(backto_text, callback_data=backto_loc)])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='home')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(text="Choose a category:", reply_markup=reply_markup)
    except Exception as e:
        print("Error in view_category")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
        
# Function to list all transactions using buttons
def view_transactions(update: Update, context: CallbackContext):
    # try:
    # Loop through the income categories and create buttons
    db_name = get_db_name()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # cursor.execute("SELECT * FROM records")
    cursor.execute("SELECT records.id, user_id, category_id, amount, timestamp, note, categories.id, categories.name FROM records JOIN categories ON records.category_id = categories.id")
    transactions = cursor.fetchall()
    
    # check if the database is empty
    if not transactions:
        conn.close()
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text("❕ No transactions found.", reply_markup=reply_markup)
        return
    
    conn.close()
    
    keyboard = []
    for transaction in transactions:
        keyboard.append([InlineKeyboardButton(str(transaction[0]) + ". " + transaction[7] + " | " + str(transaction[3])  + " | " + str(transaction[5]) + " @ " + transaction[4][5:10], callback_data='trans:' + str(transaction[0]))])
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data='home')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(text="Choose a transaction:", reply_markup=reply_markup)
    # except Exception as e:
    #     print("Error in view_transactions")
        
    #     keyboard = [
    #         [InlineKeyboardButton("❌ Close", callback_data='home')]
    #     ]
    #     reply_markup = InlineKeyboardMarkup(keyboard)
    #     update.callback_query.edit_message_text("❌ Database might be empty.", reply_markup=reply_markup)

# Function to show the menu with buttons
def show_menu(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 Summary", callback_data='view_summary')],
        [InlineKeyboardButton("🔍 Transaction History", callback_data='view_transactions')],
        [InlineKeyboardButton("➕ Add Transaction", callback_data='add_transaction')],
        [InlineKeyboardButton("➕ Add Category", callback_data='add_category')],
        [InlineKeyboardButton("✍🏻 Modify Transaction", callback_data='modify_transaction')],
        [InlineKeyboardButton("✍🏻 Modify Category", callback_data='modify_category')],
        [InlineKeyboardButton("⚠️ Set Balance (not recommended)", callback_data='set_balance')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        # hide the keyboard
        # context.bot.send_message(chat_id=update.effective_chat.id, text="😃 How can I help you today?", reply_markup=ReplyKeyboardRemove())
        update.message.reply_text(text="😃 How can I help you today?", reply_markup=reply_markup)
    else:
        # hide the keyboard
        # context.bot.send_message(chat_id=update.effective_chat.id, text="😃 How can I help you today?", reply_markup=ReplyKeyboardRemove())
        update.callback_query.edit_message_text(text="😃 How can I help you today?", reply_markup=reply_markup)

def view_user(update: Update, context: CallbackContext):
    try:
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT u.id, u.name, b.amount FROM users u, balance b WHERE u.id = b.user_id")
        users = cursor.fetchall()
        
        # add name names to list of buttons
        keyboard = []
        for user in users:
            keyboard.append([InlineKeyboardButton(user[1] + " (" + str(user[2]) + ")", callback_data=user[0])])
        keyboard.append([InlineKeyboardButton("❌ Close", callback_data='home')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        conn.close()
        
        update.callback_query.edit_message_text("Please select an account to set balance:", reply_markup=reply_markup)
    except Exception as e:
        print("Error in view_user")
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)

# Function to handle the button click actions
def process_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()  # Acknowledge the callback
    
    print(f"Sate: {STATE}")
    print(f"query.data: {query.data}")
        
    # ----------- main operations -----------
    # view balance summary
    if query.data == 'view_summary':
        reset_state()
        STATE["OPTION"] = 'view_summary'
        summarize(update, context)  # Call the existing summarize function to display the summary

    # view transaction history
    if query.data == 'view_transactions':
        reset_state()
        STATE["OPTION"] = 'view_transactions'
        view_main_category(update, context)
        
    # add transaction
    if query.data == 'add_transaction':
        reset_state()
        STATE["OPTION"] = 'add_transaction'
        view_main_category(update, context)
        
    # add category
    if query.data == 'add_category':
        reset_state()
        STATE["OPTION"] = 'add_category'
        view_main_category(update, context)
        
    # modify transaction
    if query.data == 'modify_transaction':
        reset_state()
        STATE["OPTION"] = 'modify_transaction'
        view_transactions(update, context)
        
    # modify category
    if query.data == 'modify_category':
        reset_state()
        STATE["OPTION"] = 'modify_category'
        view_main_category(update, context)
    
    # set balance
    if query.data == 'set_balance':
        reset_state()
        STATE["OPTION"] = 'set_balance'
        view_user(update, context)
                
    # home
    if query.data == 'home':
        reset_state()
        show_menu(update, context)
        
    # back to the previous menu
    # if query.data == 'back':
    #     reset_state()
    #     show_menu(update, context)
        
    # ----------- "detailed" operations -----------
    if STATE["OPTION"] == 'view_transactions' and query.data.startswith('mcat:'):
        reset_state()
        main_category = query.data.split(':')[1]
        detail_transaction(update, main_category)
        
    # add transactions
    if STATE["OPTION"] == 'add_transaction':
        if query.data.startswith('mcat:'):
            reset_state(option=False)
            main_category = query.data.split(':')[1]
            STATE["MAIN_CATEGORY"] = main_category
            view_category(update, context)
        
        elif query.data.startswith('scat:'):
            reset_state(option=False, main_category=False)
            category = query.data.split(':')[1]
            STATE["CATEGORY"] = category
            keyboard = [
                [InlineKeyboardButton("❌ Cancel", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.callback_query.edit_message_text(text=f"#️⃣ Please provide the amount for the transaction:", reply_markup=reply_markup)
        
        # transaction with empty note
        elif query.data == 'note_nothing':
            if STATE["MAIN_CATEGORY"] == 'income' or STATE["MAIN_CATEGORY"] == 'expense':
                if STATE["CATEGORY"]:
                    if STATE["AMOUNT"]:
                        note = None
                        add_transaction(update, STATE["CATEGORY"], STATE["AMOUNT"], note)
                        reset_state()

    # add category        
    if STATE["OPTION"] == 'add_category' and query.data.startswith('mcat:'):
        reset_state(option=False)
        main_category = query.data.split(':')[1]
        STATE["MAIN_CATEGORY"] = main_category
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(text=f"🏷️ Please provide a category name:", reply_markup=reply_markup)
        
    # modify transaction
    if STATE["OPTION"] == 'modify_transaction':
        if query.data.startswith('trans:'):
            STATE["TRANSACTION_ID"] = int(query.data.split(':')[1])
            print(f"Transaction ID: {STATE['TRANSACTION_ID']}")
            
            # ask to modify or delete
            keyboard = [
                [InlineKeyboardButton("✏️ Modify", callback_data='modify_trans')],
                [InlineKeyboardButton("⛔ Delete", callback_data='delete_trans')],
                [InlineKeyboardButton("❌ Close", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.callback_query.edit_message_text(text="❓ What do you want to do with this transaction?", reply_markup=reply_markup)
            
        elif query.data == 'modify_trans':
            STATE["OPTION"] = 'modify_transaction_amount'
            print(f"Modifying transaction {STATE['TRANSACTION_ID']}")
            
            # add a button with the current amount
            conn = sqlite3.connect(get_db_name())
            cursor = conn.cursor()
            cursor.execute("SELECT amount FROM records WHERE id = ?", (STATE["TRANSACTION_ID"],))
            amount = cursor.fetchone()[0]
            conn.close()
            
            keyboard = [
                [InlineKeyboardButton(f"💰 {amount}", callback_data='modify_trans_amount')],
                [InlineKeyboardButton("❌ Close", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.callback_query.edit_message_text(text="️#️⃣ Please provide the new amount for the transaction:", reply_markup=reply_markup)
        elif query.data == 'delete_trans':
            print(f"Deleting transaction {STATE['TRANSACTION_ID']}")
            try:
                # Ask for confirmation
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm", callback_data='confirm_delete')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text(text="❓ Are you sure you want to delete this transaction?", reply_markup=reply_markup)
            except Exception as e:
                print("Error in delete transaction")
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
            
        elif query.data == 'confirm_delete':
            print(f"Deleting transaction {STATE['TRANSACTION_ID']}")
            try:
                # Loop through the income categories and create buttons
                db_name = get_db_name()
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM records WHERE id = ?", (STATE["TRANSACTION_ID"],))
                conn.commit()
                conn.close()
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text(text="Transaction deleted.", reply_markup=reply_markup)
            except Exception as e:
                print("Error in delete transaction")
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
        
    if STATE["OPTION"] == 'modify_transaction_amount' and query.data == 'modify_trans_amount':
        # Get the current amount and current date
        conn = sqlite3.connect(get_db_name())
        cursor = conn.cursor()
        cursor.execute("SELECT amount, timestamp FROM records WHERE id = ?", (STATE["TRANSACTION_ID"],))
        res = cursor.fetchone()
        conn.close()
        amount = res[0]
        timestamp = res[1]
        conn.close()
        
        STATE["AMOUNT"] = amount
        print(f"Modifying transaction {STATE['AMOUNT']}")
        
        keyboard = [
            [InlineKeyboardButton("🗓️ " + timestamp[5:10], callback_data='modify_trans_date')],
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.callback_query.edit_message_text(text="🗓️ Please provide a new date for the transaction:", reply_markup=reply_markup)
        except Exception as e:
            update.message.reply_text(text="🗓️ Please provide a new date for the transaction:", reply_markup=reply_markup)
        STATE["OPTION"] = 'modify_transaction_date'
            
    if STATE["OPTION"] == 'modify_transaction_date' and  query.data == 'modify_trans_date':
        # Get the current date
        conn = sqlite3.connect(get_db_name())
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM records WHERE id = ?", (STATE["TRANSACTION_ID"],))
        timestamp = cursor.fetchone()[0]
        conn.close()
        
        # modify the transaction
        date = timestamp
        
        db_name = get_db_name()
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE records SET amount = ?, timestamp = ? WHERE id = ?", (STATE["AMOUNT"], date, STATE["TRANSACTION_ID"]))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.message.reply_text(f"✍🏻 Transaction has been updated.", reply_markup=reply_markup)
        except Exception as e:
            update.callback_query.edit_message_text(f"✍🏻 Transaction has been updated.", reply_markup=reply_markup)
        reset_state()

    # modify category
    if STATE["OPTION"] == 'modify_category':
        if query.data.startswith('mcat:'):
            reset_state(option=False)
            main_category = query.data.split(':')[1]
            STATE["MAIN_CATEGORY"] = main_category
            view_category(update, context)
        elif query.data.startswith('scat:'):
            reset_state(option=False, main_category=False)
            category = query.data.split(':')[1]
            STATE["CATEGORY_ID"] = category
            keyboard = [
                [InlineKeyboardButton("✏️ Modify", callback_data='modify_cat')],
                [InlineKeyboardButton("⛔ Delete", callback_data='delete_cat')],
                [InlineKeyboardButton("❌ Close", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.callback_query.edit_message_text(text=f"❓ What do you want to do with this category?", reply_markup=reply_markup)
        elif query.data == 'modify_cat':
            print(f"Modifying category {STATE['CATEGORY']}")
            
            # add a button with the current category name
            conn = sqlite3.connect(get_db_name())
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories WHERE id = ?", (STATE["CATEGORY_ID"],))
            category = cursor.fetchone()[0]
            conn.close()
            
            keyboard = [
                [InlineKeyboardButton(f"🏷️ {category}", callback_data='modify_cat_name')],
                [InlineKeyboardButton("❌ Close", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                update.callback_query.edit_message_text(text="️#️⃣ Please provide the new name for the category:", reply_markup=reply_markup)
            except Exception as e:
                update.message.reply_text(text="️#️⃣ Please provide the new name for the category:", reply_markup=reply_markup)
            
            STATE["OPTION"] = 'modify_category_name'
        elif query.data == 'delete_cat':
            print(f"Deleting category {STATE['CATEGORY']}")
            try:
                # Ask for confirmation
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm", callback_data='confirm_delete_cat')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text(text="❓ Are you sure you want to delete this category?", reply_markup=reply_markup)
            except Exception as e:
                print("Error in delete category")
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
        elif query.data == 'confirm_delete_cat':
            print(f"Deleting category {STATE['CATEGORY']}")
            try:
                # Loop through the income categories and create buttons
                db_name = get_db_name()
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                
                # loop through the records and check if the category is used
                cursor.execute("SELECT * FROM records WHERE category_id = ?", (STATE["CATEGORY_ID"],))
                records = cursor.fetchall()
                if records:
                    keyboard = [
                        [InlineKeyboardButton("❌ Close", callback_data='home')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    update.callback_query.edit_message_text("❕ This category is used in transactions. Please delete the transactions first.", reply_markup=reply_markup)
                    return
                
                cursor.execute("DELETE FROM categories WHERE id = ?", (STATE["CATEGORY_ID"],))
                conn.commit()
                conn.close()
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text(text="Category deleted.", reply_markup=reply_markup)
            except Exception as e:
                print("Error in delete category")
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.callback_query.edit_message_text("❕ Database might be empty.", reply_markup=reply_markup)
            
    if query.data == 'modify_cat_name':
        # Get the current name
        conn = sqlite3.connect(get_db_name())
        cursor = conn.cursor()
        print(f"STATE['CATEGORY_ID']: {STATE['CATEGORY_ID']}")
        cursor.execute("SELECT categories.name, categories.'limit' FROM categories WHERE id = ?", (STATE["CATEGORY_ID"],))
        res = cursor.fetchone()
        category = res[0]
        limit = res[1]
        conn.close()
        
        STATE["CATEGORY"] = category
        
        # add a button with the current category limit
        keyboard = [
            [InlineKeyboardButton("💰 " + str(limit), callback_data='modify_cat_limit')],
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.callback_query.edit_message_text(text="️#️⃣ Please provide the new planned limit for the category:", reply_markup=reply_markup)
        except Exception as e:
            update.message.reply_text(text="️#️⃣ Please provide the new planned limit for the category:", reply_markup=reply_markup)
            
        STATE["OPTION"] = 'modify_category_limit'
    if query.data == 'modify_cat_limit':
        # Get the current limit
        conn = sqlite3.connect(get_db_name())
        cursor = conn.cursor()
        cursor.execute("SELECT categories.'limit' FROM categories WHERE id = ?", (STATE["CATEGORY_ID"],))
        limit = cursor.fetchone()[0]
        conn.close()
    
        # update the category based on the new name and limit
        category_id = STATE["CATEGORY_ID"]
        new_name = STATE["CATEGORY"]
        new_limit = limit
        conn = sqlite3.connect(get_db_name())
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET name = ?, 'limit' = ? WHERE id = ?", (new_name, new_limit, category_id))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("❌ Close", callback_data='home')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            update.callback_query.edit_message_text(f"✍🏻 Category has been updated.", reply_markup=reply_markup)
        except Exception as e:
            update.message.reply_text(f"✍🏻 Category has been updated.", reply_markup=reply_markup)
        reset_state()
        # elif query.data == 'delete_cat':
        
    # set balance
    if STATE["OPTION"] == 'set_balance':
        if query.data == str(USER_ID_1) or query.data == str(USER_ID_2):
            reset_state(option=False)
            STATE["USER"] = query.data
            keyboard = [
                [InlineKeyboardButton("❌ Close", callback_data='home')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.callback_query.edit_message_text(text=f"Please manually set the balance for {get_user_name(int(query.data))}:", reply_markup=reply_markup)

# Function to process the user's input
def process_text(update: Update, context: CallbackContext):
    user_input = update.message.text  # Get the user's input message
    
    # print(f"User input: {user_input}")
    # print(f"Current state: {STATE}")
    
    if not STATE["OPTION"]:
        show_menu(update, context)
        
    # Amount for the transaction
    if STATE["OPTION"] == 'add_transaction':
        if STATE["MAIN_CATEGORY"] == 'income' or STATE["MAIN_CATEGORY"] == 'expense':
            if STATE["CATEGORY"]:
                if not STATE["AMOUNT"]:
                    try:
                        amount = float(user_input)  # Convert the input to a float
                        STATE["AMOUNT"] = amount
                        keyboard = [
                            [InlineKeyboardButton("🗒️ Nothing", callback_data='note_nothing')],
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.message.reply_text(f"✍🏻 Please provide a note for the '{STATE['CATEGORY']}' transaction, e.g., lẩu buffet (optional)", reply_markup=reply_markup)
                    except Exception as e:
                        keyboard = [
                            [InlineKeyboardButton("❌ Close", callback_data='home')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.message.reply_text("❕ Please provide a valid amount.", reply_markup=reply_markup)
                else:
                    try:
                        note = user_input
                        add_transaction(update, STATE["CATEGORY"], STATE["AMOUNT"], note)
                        reset_state()
                    except Exception as e:
                        print(f"Error in add_transaction: {e}")
                        keyboard = [
                            [InlineKeyboardButton("❌ Close", callback_data='home')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.message.reply_text("❕ Please provide a valid note.", reply_markup=reply_markup)
                        reset_state()
                    
    # New category for income or expense
    if STATE["OPTION"] == 'add_category':
        if STATE["MAIN_CATEGORY"] == 'income' or STATE["MAIN_CATEGORY"] == 'expense':
            if STATE["CATEGORY"]:
                try:
                    planned_limit = float(user_input)
                    add_category(update, STATE["MAIN_CATEGORY"], STATE["CATEGORY"], planned_limit)
                    reset_state()
                except Exception as e:
                    print(f"Error in add_category: {e}")
                    keyboard = [
                        [InlineKeyboardButton("❌ Close", callback_data='home')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    update.message.reply_text("❕ Please provide a valid planned limit.", reply_markup=reply_markup)
                    reset_state()
            else:
                STATE["CATEGORY"] = user_input
                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(f"#️⃣ Please provide a planned limit for the '{user_input}' category:", reply_markup=reply_markup)
                
    # Modify transaction amount
    if STATE["OPTION"] == 'modify_transaction_amount':
        if STATE["TRANSACTION_ID"]:
            try:
                amount = float(user_input)                
                STATE["AMOUNT"] = amount

                # Get the current amount and current date
                conn = sqlite3.connect(get_db_name())
                cursor = conn.cursor()
                cursor.execute("SELECT amount, timestamp FROM records WHERE id = ?", (STATE["TRANSACTION_ID"],))
                res = cursor.fetchone()
                conn.close()
                amount = res[0]
                timestamp = res[1]
                conn.close()
                
                keyboard = [
                    [InlineKeyboardButton("🗓️ " + timestamp[5:10], callback_data='modify_trans_date')],
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(f"Please provide the correct date for the transaction (MMDD):", reply_markup=reply_markup)
                STATE["OPTION"] = 'modify_transaction_date'

            except Exception as e:
                print(f"Error in modify_transaction: {e}")
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("❕ Please provide a valid amount.", reply_markup=reply_markup)
                reset_state()
    elif STATE["OPTION"] == 'modify_transaction_date':
        if STATE["TRANSACTION_ID"]:
            try:
                date = user_input
                # convert to timestamp using current year and time
                date = f"{datetime.now().year}-{date[:2]}-{date[2:]}" + datetime.now().strftime(" %H:%M:%S")
                print(f"Date: {date}")
                # check if the date is valid
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                if not is_valid_date(date):
                    update.message.reply_text("❕ Please provide a valid date in the format MMDD. For example, 0128 for January 28th.", reply_markup=reply_markup)
                    return
                
                db_name = get_db_name()
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                
                cursor.execute("UPDATE records SET amount = ?, timestamp = ? WHERE id = ?", (STATE["AMOUNT"], date, STATE["TRANSACTION_ID"]))
                conn.commit()
                conn.close()
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(f"✍🏻 Transaction has been updated.", reply_markup=reply_markup)
                reset_state()

            except Exception as e:
                print(f"Error in modify_transaction: {e}")
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("❕ Please provide a valid date.", reply_markup=reply_markup)
                reset_state()
                
    # Modify category
    if STATE["OPTION"] == 'modify_category_name':
        if STATE["CATEGORY_ID"]:
            try:
                new_name = user_input
                STATE["CATEGORY"] = new_name
                conn = sqlite3.connect(get_db_name())
                cursor = conn.cursor()
                cursor.execute("SELECT categories.'limit' FROM categories WHERE id = ?", (STATE["CATEGORY_ID"],))
                limit = cursor.fetchone()[0]
                conn.close()
                                
                keyboard = [
                    [InlineKeyboardButton("💰 " + str(limit), callback_data='modify_cat_limit')],
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    update.message.reply_text(f"💰 Please provide the new planned limit for the '{new_name}' category:", reply_markup=reply_markup)
                except Exception as e:
                    update.callback_query.edit_message_text(f"💰 Please provide the new planned limit for the '{new_name}' category:", reply_markup=reply_markup)
                    
                STATE["OPTION"] = 'modify_category_limit'
            except Exception as e:
                print(f"Error in modify_category: {e}")
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    update.message.reply_text("❕ Please provide a valid category name.", reply_markup=reply_markup)
                except Exception as e:
                    update.callback_query.edit_message_text("❕ Please provide a valid category name.", reply_markup=reply_markup)
    elif STATE["OPTION"] == 'modify_category_limit':
        if STATE["CATEGORY_ID"]:
            try:
                planned_limit = float(user_input)
                category_id = STATE["CATEGORY_ID"]
                new_name = STATE["CATEGORY"]
                new_limit = planned_limit
                conn = sqlite3.connect(get_db_name())
                cursor = conn.cursor()
                cursor.execute("UPDATE categories SET name = ?, 'limit' = ? WHERE id = ?", (new_name, new_limit, category_id))
                conn.commit()
                conn.close()
                
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    update.message.reply_text(f"✍🏻 Category has been updated.", reply_markup=reply_markup)
                except Exception as e:
                    update.callback_query.edit_message_text(f"✍🏻 Category has been updated.", reply_markup=reply_markup)
                
                reset_state()
            except Exception as e:
                print(f"Error in modify_category: {e}")
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    update.message.reply_text("❕ Please provide a valid planned limit.", reply_markup=reply_markup)
                except Exception as e:
                    update.callback_query.edit_message_text("❕ Please provide a valid planned limit.", reply_markup=reply_markup)
                reset_state()
                
    # Set balance for the user
    if STATE["OPTION"] == 'set_balance':
        if STATE["USER"]:
            try:
                balance = float(user_input)
                set_balance(update, STATE["USER"], balance)
                reset_state()
            except Exception as e:
                keyboard = [
                    [InlineKeyboardButton("❌ Close", callback_data='home')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("❕ Please provide a valid balance.", reply_markup=reply_markup)
                reset_state()
    
def is_valid_date(date: str) -> bool:
    try:
        datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

# Modify main function to include the show_menu and button handler
def main():
    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Initialize the database and user info
    init_db()
    init_user()
    initialize_balance()  # Initialize balance from the previous month
    initialize_categories()  # Initialize categories

    # Command handlers
    dp.add_handler(CommandHandler("start", show_menu))  # Show the menu when the bot is started
    dp.add_handler(CallbackQueryHandler(process_button))  # Handle button presses

    # # Add other handlers for individual commands like balance, add transaction, etc.
    # dp.add_handler(CommandHandler("balance", set_balance))  # Command to set balance manually
    # dp.add_handler(CommandHandler("add", add_transaction))  # Command to add transaction
    # dp.add_handler(CommandHandler("addcat", add_category))  # Command to add category
    # dp.add_handler(CommandHandler("detail", detail_transaction))  # Command to view transaction details
    
    # Handler to process user input
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, process_text))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
