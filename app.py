from flask import Flask, request, redirect, url_for, session, flash, render_template_string
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
    return render_template_string('''
    <h1>Welcome, {{ username }}!</h1>
    <a href="{{ url_for('add_expense') }}">Add Expense</a> | 
    <a href="{{ url_for('view_expenses') }}">View Expenses</a> | 
    <a href="{{ url_for('expense_chart') }}">View Expense Chart</a> | 
    <a href="{{ url_for('logout') }}">Logout</a>
    ''')

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

    return render_template_string('''
    <h1>Register</h1>
    <form method="POST">
        Username: <input type="text" name="username" required><br>
        Password: <input type="password" name="password" required><br>
        <input type="submit" value="Register">
    </form>
    <a href="{{ url_for('login') }}">Login</a>
    ''')

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

    return render_template_string('''
    <h1>Login</h1>
    <form method="POST">
        Username: <input type="text" name="username" required><br>
        Password: <input type="password" name="password" required><br>
        <input type="submit" value="Login">
    </form>
    <a href="{{ url_for('register') }}">Register</a>
    ''')

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

    return render_template_string('''
    <h1>Add Expense</h1>
    <form method="POST">
        Expense: <input type="text" name="expense" required><br>
        Category: <input type="text" name="category" required><br>
        Amount: <input type="number" name="amount" required><br>
        Date: <input type="date" name="date" required><br>
        Time: <input type="time" name="time" required><br>
        <input type="submit" value="Add Expense">
    </form>
    <a href="{{ url_for('index') }}">Back</a>
    ''', datetime=datetime)

@app.route('/view_expenses')
def view_expenses():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user_id = session['user_id']
    expenses = conn.execute('SELECT * FROM expenses WHERE user_id = ?', (user_id,)).fetchall()
    total_amount = conn.execute('SELECT SUM(amount) FROM expenses WHERE user_id = ?', (user_id,)).fetchone()[0]
    conn.close()

    return render_template_string('''
    <h1>Your Expenses</h1>
    <table border="1">
        <tr><th>Expense</th><th>Category</th><th>Amount</th><th>Date</th><th>Time</th></tr>
        {% for expense in expenses %}
        <tr>
            <td>{{ expense['expense'] }}</td>
            <td>{{ expense['category'] }}</td>
            <td>{{ expense['amount'] }}</td>
            <td>{{ expense['date'] }}</td>
            <td>{{ expense['time'] }}</td>
        </tr>
        {% endfor %}
    </table>
    <h3>Total: {{ total_amount }}</h3>
    <a href="{{ url_for('index') }}">Back</a>
    ''', expenses=expenses, total_amount=total_amount or 0)

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

    return render_template_string('''
    <h1>Expense Chart</h1>
    <img src="{{ chart_url }}" alt="Expense Chart">
    <a href="{{ url_for('index') }}">Back</a>
    ''', chart_url=url_for('static', filename='expense_chart.png'))

if __name__ == '__main__':
    app.run(debug=True)
