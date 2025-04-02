import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
JOURNAL_DIR = "journals"
os.makedirs(JOURNAL_DIR, exist_ok=True)

# Database connection function
def get_db_connection():
    conn = sqlite3.connect("mom_hive.db")
    conn.row_factory = sqlite3.Row
    return conn

# Function to create tables if they don't exist
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            age INTEGER,
            gender TEXT,
            address TEXT,
            married TEXT,
            working TEXT,
            contact TEXT,
            partner TEXT,
            dob TEXT,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS epds_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            score INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    
    conn.commit()
    conn.close()

create_tables()

# Index Page
@app.route('/')
def index():
    return render_template('index.html')

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        address = request.form['address']
        married = request.form.get('married', 'No')
        working = request.form.get('working', 'No')
        contact = request.form['contact']
        partner = request.form['partner']
        dob = request.form['dob']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (username, age, gender, address, married, working, contact, partner, dob, password) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, age, gender, address, married, working, contact, partner, dob, password))
            conn.commit()
            session['username'] = username
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            return "Username already exists! Try another one."
        finally:
            conn.close()

    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return "Invalid Credentials! Try Again."
    
    return render_template('login.html')

# Home Page
@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get latest EPDS score
    cursor.execute("SELECT score FROM epds_scores WHERE username = ? ORDER BY date DESC LIMIT 1", (username,))
    epds_score = cursor.fetchone()
    epds_score = epds_score['score'] if epds_score else "No Data"

    # Get latest mood score
    cursor.execute("SELECT mood FROM mood_tracker WHERE username = ? ORDER BY date DESC LIMIT 1", (username,))
    mood_score = cursor.fetchone()
    mood_score = mood_score['mood'] if mood_score else "No Data"

    # Fetch mood data for graph
    cursor.execute("SELECT mood, date FROM mood_tracker WHERE username = ? ORDER BY date DESC LIMIT 5", (username,))
    mood_data = cursor.fetchall()
    conn.close()

    # Debug: Check if mood data is fetched
    print("Mood Data for Graph:", mood_data)

    graph_path = None
    if mood_data:
        moods = [row['mood'] for row in reversed(mood_data)]
        dates = [row['date'] for row in reversed(mood_data)]
        print("Mood Graph Data:", moods, dates)  # Debugging

        # Generate Mood Graph
        plt.figure(figsize=(6, 4))
        plt.plot(dates, moods, marker='o', linestyle='-', color='b', label='Mood Level')
        plt.xlabel("Date")
        plt.ylabel("Mood Score")
        plt.title(f"{username}'s Mood Trends")
        plt.xticks(rotation=30)
        plt.legend()

        graph_path = "static/mood_graph.png"
        plt.savefig(graph_path)
        plt.close()

    return render_template('home.html', username=username, epds_score=epds_score, mood_score=mood_score, graph_path=graph_path)

@app.route('/epds', methods=['GET', 'POST'])
def epds():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        scores = [int(request.form[f'q{i}']) for i in range(1, 11)]
        total_score = sum(scores)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO epds_scores (username, score) VALUES (?, ?)", (session['username'], total_score))
        conn.commit()
        conn.close()

        if total_score < 12:
            result = "You are good"
        elif 12 <= total_score <= 14:
            result = "Entering phase of PPD"
        else:
            result = "Need consultation"

        return render_template('epds.html', result=result)

    return render_template('epds.html', result=None)

@app.route('/mood_tracker', methods=['GET', 'POST'])
def mood_tracker():
    if 'username' not in session:  # Fix: Ensure session is checked
        return redirect(url_for('login'))

    if request.method == 'POST':
        mood = int(request.form['mood'])

        username = session['username']  # Make sure username is stored in session

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mood_tracker (username, mood) VALUES (?, ?)", (username, mood))
        conn.commit()
        conn.close()

        return redirect(url_for('mood_graph'))  # Ensure it redirects to mood_graph

    return render_template('mood_tracker.html')

@app.route('/mood_graph')
def mood_graph():
    if 'username' not in session:  # Fix: Ensure session is checked properly
        return redirect(url_for('login'))

    username = session['username']  # Get username from session

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT mood, date FROM mood_tracker WHERE username = ? ORDER BY date ASC", (username,))
    mood_data = cur.fetchall()
    conn.close()

    if not mood_data:
        return "No mood data available."

    # Extract mood scores and dates
    mood_scores = [row['mood'] for row in mood_data]
    mood_dates = [row['date'] for row in mood_data]

    # Generate Mood Graph
    plt.figure(figsize=(8, 5))
    plt.plot(mood_dates, mood_scores, marker='o', linestyle='-', color='b', label="Mood Score")
    plt.xlabel("Date")
    plt.ylabel("Mood Level")
    plt.title(f"{username}'s Mood Tracker Over Time")
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()
    
    graph_path = "static/mood_graph.png"
    plt.savefig(graph_path)
    plt.close()

    return render_template('mood_graph.html', graph_path=graph_path)

@app.route('/music')
def music():
    return render_template('music.html')

# Memory Box
@app.route('/memory_box', methods=['GET', 'POST'])
def memory_box():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        photo = request.files['photo']
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    photos = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('memory_box.html', photos=photos)

# Journal Page
@app.route('/journal', methods=['GET', 'POST'])
def journal():
    return render_template('journal.html')

# Save Journal
@app.route('/save_journal', methods=['POST'])
def save_journal():
    try:
        filename = request.form.get('filename', '').strip()
        content = request.form.get('content', '')

        if not filename:
            flash("Filename cannot be empty!", "error")
            return redirect(url_for('journal'))

        file_path = os.path.join(JOURNAL_DIR, f"{secure_filename(filename)}.txt")

        with open(file_path, "w") as file:
            file.write(content)

        flash("Journal saved successfully!", "success")
        return redirect(url_for('view_journals'))

    except KeyError:
        flash("Please enter a filename!", "error")
        return redirect(url_for('journal'))

# View Journals
@app.route('/view_journals')
def view_journals():
    files = os.listdir(JOURNAL_DIR)
    return render_template('view_journal.html', files=files)

# Delete Journal
@app.route('/delete_journal/<filename>')
def delete_journal(filename):
    file_path = os.path.join(JOURNAL_DIR, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        flash("Journal deleted successfully!", "success")
    else:
        flash("File not found!", "error")

    return redirect(url_for('view_journals'))

# Run Flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
