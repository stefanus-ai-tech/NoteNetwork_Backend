from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from .config import Config
import os
from flask_cors import CORS
import psycopg2

# Initialize the Flask application
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": "https://your-frontend.vercel.app"}})

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database connection function
import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('PGHOST'),
        database=os.environ.get('PGDATABASE'),
        user=os.environ.get('PGUSER'),
        password=os.environ.get('PGPASSWORD'),
        port=os.environ.get('PGPORT', 5432)
    )
    conn.autocommit = True  # Ensure auto-commit mode
    return conn


# User loader callback
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['role'])
    return None

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # 'poster' or 'jobseeker'

        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('An account with this email already exists.')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                     (username, email, password_hash, role))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['email'], user['role'])
            login_user(user_obj)
            flash('Logged in successfully.')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/vacancies')
def vacancies():
    conn = get_db_connection()
    vacancies = conn.execute('SELECT * FROM vacancies ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('vacancies.html', vacancies=vacancies)

@app.route('/vacancy/<int:id>')
def vacancy_detail(id):
    conn = get_db_connection()
    vacancy = conn.execute('SELECT * FROM vacancies WHERE id = ?', (id,)).fetchone()
    conn.close()
    if vacancy is None:
        return render_template('404.html'), 404
    return render_template('vacancy_detail.html', vacancy=vacancy)

@app.route('/post_vacancy', methods=('GET', 'POST'))
@login_required
def post_vacancy():
    if current_user.role != 'poster':
        flash('You are not authorized to post vacancies.')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        school_name = request.form['school_name']

        conn = get_db_connection()
        conn.execute('INSERT INTO vacancies (title, description, school_name, user_id) VALUES (?, ?, ?, ?)',
                     (title, description, school_name, current_user.id))
        conn.commit()
        conn.close()
        flash('Vacancy posted successfully.')
        return redirect(url_for('vacancies'))
    return render_template('post_vacancy.html')

@app.route('/connect/<int:vacancy_id>', methods=('GET', 'POST'))
@login_required
def connect(vacancy_id):
    if current_user.role != 'jobseeker':
        flash('You are not authorized to apply for vacancies.')
        return redirect(url_for('index'))
    conn = get_db_connection()
    vacancy = conn.execute('SELECT * FROM vacancies WHERE id = ?', (vacancy_id,)).fetchone()
    if vacancy is None:
        conn.close()
        flash('Vacancy not found.')
        return redirect(url_for('vacancies'))

    if request.method == 'POST':
        message = request.form['message']
        # In a real application, you would send an email to the vacancy poster
        flash('Your application has been sent to the school.')
        conn.close()
        return redirect(url_for('vacancies'))

    conn.close()
    return render_template('connect.html', vacancy=vacancy)

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
