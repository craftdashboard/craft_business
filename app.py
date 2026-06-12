from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkeyforcraftbusiness'

# Database Setup
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            item_name TEXT,
            total_amount REAL,
            advance_paid REAL,
            expense_cost REAL,
            status TEXT DEFAULT 'Confirmed'
        )
    ''')
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # Default Demo Login
    try:
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", ('admin', 'admin@gmail.com', hashed_pw))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
        
    conn.close()

# 1. Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['login_input']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? OR email=?", (login_input, login_input))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['logged_in'] = True
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid Username/Email or Password!")
            
    return render_template('login.html')

# 2. Sign Up Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('signup.html', error="Username or Email already exists!")
            
    return render_template('signup.html')

# 3. Forgot Password Route
@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['password']
        hashed_pw = generate_password_hash(new_password)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed_pw, email))
            conn.commit()
            conn.close()
            return render_template('forgot.html', success="Password reset successfully! Go to Login.")
        else:
            conn.close()
            return render_template('forgot.html', error="Email not found!")
            
    return render_template('forgot.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Main Dashboard Page
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status='Confirmed'")
    active_orders = cursor.fetchall()
    cursor.execute("SELECT * FROM orders WHERE status='Completed'")
    completed_orders = cursor.fetchall()
    
    cursor.execute("SELECT SUM(total_amount), SUM(expense_cost) FROM orders WHERE status='Completed'")
    stats = cursor.fetchone()
    total_revenue = stats[0] if stats[0] else 0
    total_expense = stats[1] if stats[1] else 0
    total_profit = total_revenue - total_expense
    conn.close()
    
    return render_template('index.html', active=active_orders, completed=completed_orders, profit=total_profit, expense=total_expense)

# Add Order
@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        name, item = request.form['name'], request.form['item']
        total, advance, expense = float(request.form['total']), float(request.form['advance']), float(request.form['expense'])
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (customer_name, item_name, total_amount, advance_paid, expense_cost) VALUES (?, ?, ?, ?, ?)", (name, item, total, advance, expense))
        conn.commit(); conn.close()
        return redirect(url_for('index'))
    return render_template('add_order.html')

# 4. Edit Order Route (New Feature)
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_order(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name, item = request.form['name'], request.form['item']
        total, advance, expense = float(request.form['total']), float(request.form['advance']), float(request.form['expense'])
        cursor.execute('''
            UPDATE orders 
            SET customer_name=?, item_name=?, total_amount=?, advance_paid=?, expense_cost=? 
            WHERE id=?
        ''', (name, item, total, advance, expense, id))
        conn.commit(); conn.close()
        return redirect(url_for('index'))
        
    cursor.execute("SELECT * FROM orders WHERE id=?", (id,))
    order = cursor.fetchone(); conn.close()
    return render_template('edit_order.html', order=order)

# Complete Order
@app.route('/complete/<int:id>')
def complete_order(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status='Completed', advance_paid=total_amount WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('index'))

# Invoice Route
@app.route('/invoice/<int:id>')
def invoice(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id=?", (id,))
    order = cursor.fetchone(); conn.close()
    return render_template('invoice.html', order=order)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)