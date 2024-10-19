from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import logging
import datetime
import jwt
from flask_cors import CORS
import sqlite3

# Database imports
import psycopg2
import psycopg2.extras
import sqlite3
from urllib.parse import urlparse

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')
CORS(app, resources={r"/*": {"origins": "https://note-network-frontend.vercel.app"}})

# Database connection function
def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')  # Ensure correct path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Database helper class
class DatabaseHelper:
    def __init__(self):
        self.env = os.environ.get('ENV', 'development')
        self.conn = get_db_connection()
        if self.env == 'production':
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self.param_style = 'pyformat'  # For psycopg2
        else:
            self.cursor = self.conn.cursor()
            self.param_style = 'named'  # For sqlite3

    def execute(self, query, params=None):
        if params is None:
            params = {}
        if self.env == 'production':
            # Convert named parameters to psycopg2 format
            # Replace :param with %(param)s
            import re
            query = re.sub(r":(\w+)", r"%(\1)s", query)
        self.cursor.execute(query, params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row and self.env == 'development':
            return dict(row)
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if rows and self.env == 'development':
            return [dict(row) for row in rows]
        return rows

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

# User class
class User:
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check if token is passed in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User(data['user_id'], data.get('username'), data.get('email'), data['role'])
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Routes

@app.route('/')
def index():
    return jsonify({'message': 'Welcome to the Note Network API'}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not username or not email or not password or not role:
        return jsonify({'message': 'Missing required fields.'}), 400

    try:
        db = DatabaseHelper()
        logging.debug(f"Registering user: {username}, {email}, {role}")

        # Use named parameters
        db.execute('SELECT * FROM users WHERE email = :email', {'email': email})
        existing_user = db.fetchone()

        if existing_user:
            logging.debug(f"User already exists: {email}")
            db.close()
            return jsonify({'message': 'An account with this email already exists.'}), 400

        password_hash = generate_password_hash(password)
        db.execute('INSERT INTO users (username, email, password_hash, role) VALUES (:username, :email, :password_hash, :role)',
                   {'username': username, 'email': email, 'password_hash': password_hash, 'role': role})
        db.commit()
        db.close()
        logging.debug(f"User registered successfully: {username}")
        return jsonify({'message': 'Registration successful! Please log in.'}), 201
    except Exception as e:
        logging.error(f"Error during registration: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        db = DatabaseHelper()
        db.execute('SELECT id, username, email, password_hash, role FROM users WHERE email = :email', {'email': email})
        user = db.fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm='HS256')
            return jsonify({'token': token}), 200
        else:
            return jsonify({'message': 'Invalid email or password.'}), 401
    except Exception as e:
        logging.error(f"Error during login: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

@app.route('/vacancies', methods=['GET'])
def get_vacancies():
    try:
        db = DatabaseHelper()
        db.execute('SELECT id, title, description, school_name, user_id, created_at FROM vacancies ORDER BY created_at DESC')
        vacancies = db.fetchall()
        db.close()
        # Convert vacancies to list of dicts
        vacancies_list = []
        for vacancy in vacancies:
            vacancies_list.append({
                'id': vacancy['id'],
                'title': vacancy['title'],
                'description': vacancy['description'],
                'school_name': vacancy['school_name'],
                'user_id': vacancy['user_id'],
                'created_at': vacancy['created_at'].isoformat() if vacancy['created_at'] else None
            })
        return jsonify({'vacancies': vacancies_list}), 200
    except Exception as e:
        logging.error(f"Error fetching vacancies: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

@app.route('/vacancy/<int:id>', methods=['GET'])
def get_vacancy(id):
    try:
        db = DatabaseHelper()
        db.execute('SELECT id, title, description, school_name, user_id, created_at FROM vacancies WHERE id = :id', {'id': id})
        vacancy = db.fetchone()
        db.close()
        if vacancy is None:
            return jsonify({'message': 'Vacancy not found.'}), 404
        vacancy_dict = {
            'id': vacancy['id'],
            'title': vacancy['title'],
            'description': vacancy['description'],
            'school_name': vacancy['school_name'],
            'user_id': vacancy['user_id'],
            'created_at': vacancy['created_at'].isoformat() if vacancy['created_at'] else None
        }
        return jsonify({'vacancy': vacancy_dict}), 200
    except Exception as e:
        logging.error(f"Error fetching vacancy: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

@app.route('/post_vacancy', methods=['POST'])
@token_required
def post_vacancy(current_user):
    if current_user.role != 'poster':
        return jsonify({'message': 'You are not authorized to post vacancies.'}), 403
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    school_name = data.get('school_name')

    if not title or not description or not school_name:
        return jsonify({'message': 'Missing required fields.'}), 400

    try:
        db = DatabaseHelper()
        db.execute('INSERT INTO vacancies (title, description, school_name, user_id) VALUES (:title, :description, :school_name, :user_id)',
                   {'title': title, 'description': description, 'school_name': school_name, 'user_id': current_user.id})
        db.commit()
        db.close()
        return jsonify({'message': 'Vacancy posted successfully.'}), 201
    except Exception as e:
        logging.error(f"Error posting vacancy: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

@app.route('/connect/<int:vacancy_id>', methods=['POST'])
@token_required
def connect(current_user, vacancy_id):
    if current_user.role != 'jobseeker':
        return jsonify({'message': 'You are not authorized to apply for vacancies.'}), 403
    try:
        db = DatabaseHelper()
        db.execute('SELECT * FROM vacancies WHERE id = :id', {'id': vacancy_id})
        vacancy = db.fetchone()
        if vacancy is None:
            db.close()
            return jsonify({'message': 'Vacancy not found.'}), 404

        data = request.get_json()
        message = data.get('message')
        if not message:
            db.close()
            return jsonify({'message': 'Message is required.'}), 400

        # In a real application, you would send an email or notification to the vacancy poster
        db.close()
        return jsonify({'message': 'Your application has been sent to the school.'}), 200
    except Exception as e:
        logging.error(f"Error applying to vacancy: {str(e)}")
        return jsonify({'message': f'Internal server error: {str(e)}'}), 500

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'message': 'Internal server error'}), 500

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
