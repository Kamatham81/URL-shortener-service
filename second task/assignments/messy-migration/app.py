from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

@app.route('/')
def home():
    return "User Management System"

@app.route('/users', methods=['GET'])
def get_all_users():
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return str(users)

@app.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
    user = cursor.fetchone()
    
    if user:
        return str(user)
    else:
        return "User not found"

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_data()
    data = json.loads(data)
    
    name = data['name']
    email = data['email']
    password = data['password']
    
    cursor.execute(f"INSERT INTO users (name, email, password) VALUES ('{name}', '{email}', '{password}')")
    conn.commit()
    
    print("User created successfully!")
    return "User created"

@app.route('/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_data()
    data = json.loads(data)
    
    name = data.get('name')
    email = data.get('email')
    
    if name and email:
        cursor.execute(f"UPDATE users SET name = '{name}', email = '{email}' WHERE id = '{user_id}'")
        conn.commit()
        return "User updated"
    else:
        return "Invalid data"

@app.route('/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    cursor.execute(f"DELETE FROM users WHERE id = '{user_id}'")
    conn.commit()
    
    print(f"User {user_id} deleted")
    return "User deleted"

@app.route('/search', methods=['GET'])
def search_users():
    name = request.args.get('name')
    
    if not name:
        return "Please provide a name to search"
    
    cursor.execute(f"SELECT * FROM users WHERE name LIKE '%{name}%'")
    users = cursor.fetchall()
    return str(users)

@app.route('/login', methods=['POST'])
def login():
    data = json.loads(request.get_data())
    email = data['email']
    password = data['password']
    
    cursor.execute(f"SELECT * FROM users WHERE email = '{email}' AND password = '{password}'")
    user = cursor.fetchone()
    
    if user:
        return jsonify({"status": "success", "user_id": user[0]})
    else:
        return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)