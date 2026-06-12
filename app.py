from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkeyforcraftbusiness'

# Render-ൽ ഡാറ്റാബേസ് കൃത്യമായി ക്രിയേറ്റ് ആകാൻ പാത്ത് സെറ്റ് ചെയ്യുന്നു
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            image_url TEXT
        )
    ''')
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ആപ്പ് റൺ ചെയ്യുന്നതിന് തൊട്ടുമുമ്പ് ടേബിളുകൾ ഉണ്ടെന്ന് ഉറപ്പാക്കുന്നു
init_db()

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required!', 'danger')
            return render_template('signup.html')
            
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))
            conn.commit()
            conn.close()
            flash('Registration Successful! Please Login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists!', 'danger')
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE (username=? OR email=?) AND password=?', (login_input, login_input, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials! Please try again.', 'danger')
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    products_count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    orders_count = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_sales = conn.execute('SELECT SUM(total_price) FROM orders WHERE status = "Completed"').fetchone()[0] or 0
    recent_orders = conn.execute('SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id ORDER BY o.order_date DESC LIMIT 5').fetchall()
    conn.close()
    
    return render_template('dashboard.html', 
                           username=session['username'], 
                           products_count=products_count, 
                           orders_count=orders_count, 
                           total_sales=total_sales,
                           recent_orders=recent_orders)

@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock')
        description = request.form.get('description')
        
        conn.execute('INSERT INTO products (name, price, stock, description) VALUES (?, ?, ?, ?)',
                     (name, price, stock, description))
        conn.commit()
        flash('Product added successfully!', 'success')
        
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('products.html', products=products)

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        customer_name = request.form.get('customer_name')
        quantity = int(request.form.get('quantity'))
        
        product = conn.execute('SELECT price FROM products WHERE id = ?', (product_id,)).fetchone()
        if product:
            total_price = product['price'] * quantity
            conn.execute('INSERT INTO orders (product_id, customer_name, quantity, total_price) VALUES (?, ?, ?, ?)',
                         (product_id, customer_name, quantity, total_price))
            conn.commit()
            flash('Order placed successfully!', 'success')
            
    orders = conn.execute('SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id').fetchall()
    products = conn.execute('SELECT id, name FROM products').fetchall()
    conn.close()
    return render_template('orders.html', orders=orders, products=products)

@app.route('/orders/update/<int:id>', methods=['POST'])
def update_order_status(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    status = request.form.get('status')
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    flash('Order status updated!', 'success')
    return redirect(url_for('orders'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
