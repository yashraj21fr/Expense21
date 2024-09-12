from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
DATABASE = 'expenses.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Function to create the database tables
def create_tables():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            expense TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# Create the necessary tables if they don't exist
create_tables()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        expense = request.form['expense']
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']

        conn = get_db_connection()
        conn.execute('INSERT INTO expenses (user_id, expense, category, amount, date, time) VALUES (?, ?, ?, ?, ?, ?)',
                     (user_id, expense, category, amount, date, time))
        conn.commit()
        conn.close()

        flash('Expense added successfully!', 'success')
        return redirect(url_for('view_expenses'))

    return render_template('add_expense.html', datetime=datetime)

@app.route('/view_expenses')
def view_expenses():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user_id = session['user_id']
    expenses = conn.execute('SELECT * FROM expenses WHERE user_id = ?', (user_id,)).fetchall()
    total_amount = conn.execute('SELECT SUM(amount) FROM expenses WHERE user_id = ?', (user_id,)).fetchone()[0]
    conn.close()

    return render_template('view_expenses.html', expenses=expenses, total_amount=total_amount or 0)

@app.route('/expense_chart')
def expense_chart():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user_id = session['user_id']
    expenses = conn.execute('SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category',
                            (user_id,)).fetchall()
    conn.close()

    categories = [expense['category'] for expense in expenses]
    totals = [expense['total'] for expense in expenses]

    plt.figure(figsize=(6, 6))
    plt.pie(totals, labels=categories, autopct='%1.1f%%')
    plt.title('Expenses by Category')

    if not os.path.exists('static'):
        os.makedirs('static')

    plt.savefig('static/expense_chart.png')
    plt.close()

    return render_template('expense_chart.html', chart_url=url_for('static', filename='expense_chart.png'))

if __name__ == '__main__':
    app.run(debug=True)
