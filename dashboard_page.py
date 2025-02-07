from flask import Flask, render_template, request, redirect, session, flash, url_for, send_file, jsonify
import sqlite3
import bcrypt
import smtplib
import secrets
import datetime
import threading
import requests
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
from email.mime.text import MIMEText
from fpdf import FPDF
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'acfe5e9fe9351dff21ce4888ef209f76'
socketio = SocketIO(app)

# LINE Notify Token และ User ID
LINE_NOTIFY_TOKEN = 'acfe5e9fe9351dff21ce4888ef209f76'
LINE_USER_ID = 'U93113b7ca281424c098b6e1d118e4991'

# ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนผ่าน LINE Notify
def send_line_notify(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    data = {'message': message}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code

# ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนไปยัง User เฉพาะเจาะจง
def send_line_message_to_user(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code

# สร้างฐานข้อมูล SQLite
DATABASE = 'data.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                phone_number TEXT UNIQUE,
                password TEXT,
                role TEXT DEFAULT 'user',
                two_factor_enabled INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                token TEXT,
                expires_at DATETIME
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                value INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Pending',
                assigned_to TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# หน้า Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[4]):
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.', 'danger')

    return render_template('login.html')

# หน้า Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            conn.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# หน้า Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    status_filter = request.form.get('status')

    task_query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if start_date and end_date:
        task_query += " AND date(created_at) BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    if status_filter:
        task_query += " AND status = ?"
        params.append(status_filter)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(task_query, params)
        tasks = cursor.fetchall()

    return render_template('dashboard.html', tasks=tasks)

# เพิ่มฟังก์ชันสำหรับสร้างงานใหม่
@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        assigned_to = request.form['assigned_to']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, description, assigned_to) VALUES (?, ?, ?)", (title, description, assigned_to))
            conn.commit()

        # แจ้งเตือนผ่าน LINE เมื่อสร้างงานใหม่
        message = f"📢 งานใหม่ถูกสร้างขึ้น: {title} สำหรับ {assigned_to}"
        send_line_notify(message)
        send_line_message_to_user(LINE_USER_ID, message)

        flash('Task created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_task.html')

if __name__ == '__main__':
    init_db()
    import os

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=10000, allow_unsafe_werkzeug=True)

