from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS  # Added for CORS
from pymysql import connections
import config

# Initialize Flask app, LoginManager, and Bcrypt
app = Flask(__name__)
app.secret_key = 'thisismysecretcode'  # Secret key for session management

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated

bcrypt = Bcrypt(app)

# Enable CORS
# CORS(app, origins=["http://achievrtodo.s3-website-us-east-1.amazonaws.com/"])  # Replace with your S3 bucket URL

from flask_cors import cross_origin

@app.route('/auth-status', methods=['GET'])
@cross_origin(origins=["http://achievrtodo.s3-website-us-east-1.amazonaws.com"])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "username": current_user.username})
    else:
        return jsonify({"authenticated": False})

# MySQL connection setup using the config file
db_conn = connections.Connection(
    host=config.customhost,
    port=config.customport,
    user=config.customuser,
    password=config.custompass,
    db=config.customdb
)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user[0], user[1])
    return None

# Route to index page (Landing page)
@app.route('/')
def index():
    return render_template("index.html")

# Route for Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = db_conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user[2], password):
            login_user(User(user[0], user[1]))
            return redirect(url_for('todo_list'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")

# Route for Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Insert user into the database
        cursor = db_conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        db_conn.commit()
        cursor.close()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# Route to view the To-Do list (requires login)
@app.route("/todo", methods=["GET"])
@login_required
def todo_list():
    cursor = db_conn.cursor()
    query = """
        SELECT id, name, category, priority, tags, status, created_at 
        FROM tasks 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """
    cursor.execute(query, (current_user.id,))
    tasks = cursor.fetchall()
    cursor.close()
    return render_template("todo_list.html", tasks=tasks)

# Route to add a new task
@app.route("/add", methods=["POST"])
@login_required
def add_task():
    task_name = request.form["task_name"]
    category = request.form["category"]
    priority = request.form["priority"]
    tags = request.form["tags"]
    
    cursor = db_conn.cursor()
    query = """
        INSERT INTO tasks (name, category, priority, tags, user_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (task_name, category, priority, tags, current_user.id))
    db_conn.commit()
    cursor.close()
    flash("Task added successfully!", "success")
    return redirect("/todo")

# Route to mark a task as completed
@app.route("/update/<int:task_id>", methods=["POST"])
@login_required
def update_task(task_id):
    cursor = db_conn.cursor()
    query = "UPDATE tasks SET status = 'Completed' WHERE id = %s AND user_id = %s"
    cursor.execute(query, (task_id, current_user.id))
    db_conn.commit()
    cursor.close()
    flash("Task marked as completed!", "success")
    return redirect("/todo")

# Route to delete a task
@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    cursor = db_conn.cursor()
    query = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
    cursor.execute(query, (task_id, current_user.id))
    db_conn.commit()
    cursor.close()
    flash("Task deleted successfully!", "success")
    return redirect("/todo")

# Route for Logout
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()  # Logs out the current user
    flash("You have been logged out.", "info")  # Optional: Show a logout message
    return redirect(url_for('index'))  # Redirect to the index page



# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
