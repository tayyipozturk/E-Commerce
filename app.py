from flask import Flask, request, jsonify, render_template, url_for, redirect, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_cors import CORS, cross_origin
import bcrypt

app = Flask(__name__)
app.secret_key = "deployment"
CORS(app, support_credentials=True)

client = MongoClient("mongodb+srv://tayyipozturk:ceng495hw1@cluster0.egn5zal.mongodb.net/?retryWrites=true&w=majority")
db = client['commerce']
items_collection = db['items']
users_collection = db['users']
users_collection.create_index([('username', 1)], unique=True)


class Item:
    def __init__(self, name, description, price, seller, image, size=None, colour=None, spec=None):
        self.name = name
        self.description = description
        self.price = price
        self.seller = seller
        self.image = image
        self.size = size
        self.colour = colour
        self.spec = spec
        self.rating = 0
        self.reviews = []

    def save(self):
        item_dict = {'name': self.name, 'description': self.description, 'price': self.price, 'seller': self.seller,
                     'image': self.image, 'size': self.size, 'colour': self.colour, 'spec': self.spec,
                     'rating': self.rating, 'reviews': self.reviews}
        item_id = items_collection.insert_one(item_dict).inserted_id
        return str(item_id)


@app.route('/items', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_item():
    name = request.json.get('name')
    description = request.json.get('description')
    price = request.json.get('price')
    seller = request.json.get('seller')
    image = request.json.get('image')
    size = request.json.get('size')
    colour = request.json.get('colour')
    spec = request.json.get('spec')
    if name is None or price is None or seller is None:
        return jsonify({'error': 'Name, price and seller are required'})
    item = Item(name, description, price, seller, image, size, colour, spec)
    item_id = item.save()
    return jsonify({'success': True, 'item_id': item_id})


@app.route('/items/<item_id>')
@cross_origin(supports_credentials=True)
def get_item(item_id):
    item_dict = items_collection.find_one({'_id': ObjectId(item_id)})
    if item_dict is None:
        return jsonify({'error': 'Item not found'})
    else:
        item_dict['_id'] = str(item_dict['_id'])
        return jsonify(item_dict)


@app.route('/items/<item_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_item(item_id):
    name = request.json.get('name')
    description = request.json.get('description')
    price = request.json.get('price')
    seller = request.json.get('seller')
    image = request.json.get('image')
    size = request.json.get('size')
    colour = request.json.get('colour')
    spec = request.json.get('spec')
    if name is None or price is None or seller is None:
        return jsonify({'error': 'Name, price and seller are required'})
    items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'name': name, 'description': description,
                                                                      'price': price, 'seller': seller, 'image': image,
                                                                      'size': size, 'colour': colour, 'spec': spec}})
    return 'Item updated'


@app.route('/items/<item_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def delete_item(item_id):
    items_collection.delete_one({'_id': ObjectId(item_id)})
    return 'Item deleted'


@app.route('/items')
@cross_origin(supports_credentials=True)
def get_items():
    items = []
    for item_dict in items_collection.find():
        item_dict['_id'] = str(item_dict['_id'])
        items.append(item_dict)
    return jsonify(items)


class User:
    def __init__(self, username, email, password, role):
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.reviews = []

    def get_average_rating(self):
        if len(self.reviews) == 0:
            return 0
        else:
            return sum(review['rating'] for review in self.reviews) / len(self.reviews)

    def save(self):
        encrypted_password = bcrypt.hashpw(self.password.encode('utf-8'), bcrypt.gensalt())
        user_dict = {'username': self.username, 'email': self.email, 'password': encrypted_password, 'reviews': self.reviews, 'role': self.role}
        try:
            user_id = users_collection.insert_one(user_dict).inserted_id
        except:
            return str("error: user with username or email already exists")
        return str(user_id)


@app.route('/users', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_user():
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')
    role = request.json.get('role')
    if username is None:
        return jsonify({'error': 'Username is missing'})
    if email is None:
        return jsonify({'error': 'Email is missing'})
    if password is None:
        return jsonify({'error': 'Password is missing'})
    if role is None:
        role = 'user'

    user_id = User(username, email, password, role).save()
    if user_id == "error: user with username or email already exists":
        return jsonify({'success': False, 'error': 'user with username or email already exists'})
    return jsonify({'success': True, 'user_id': user_id})


@app.route('/users/<user_id>')
@cross_origin(supports_credentials=True)
def get_user(user_id):
    user_dict = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_dict is None:
        return jsonify({'error': 'User not found'})
    else:
        user_dict['_id'] = str(user_dict['_id'])
        user_dict['reviews'] = User(user_dict['username']).reviews
        return jsonify(user_dict)


@app.route('/users/<user_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_user(user_id):
    username = request.json.get('username')
    if username is None:
        return jsonify({'error': 'Username is missing'})
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': username}})
    return 'User updated'


@app.route('/users/<user_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def delete_user(user_id):
    users_collection.delete_one({'_id': ObjectId(user_id)})
    return 'User deleted'


@app.route('/users')
@cross_origin(supports_credentials=True)
def get_users():
    users = []
    for user_dict in users_collection.find():
        user_dict['_id'] = str(user_dict['_id'])
        user_dict['email'] = str(user_dict['email'])
        user_dict['password'] = str(user_dict['password'])
        user_dict['role'] = str(user_dict['role'])
        users.append(user_dict)
    return jsonify(users)


@app.route("/register", methods=['POST', 'GET'])
def register():
    message = 'You need to login as admin before adding a user.'
    if "email" not in session:
        return redirect(url_for("login"))
    render_template('register.html', message=message)
    if request.method == "POST":
        current_user = users_collection.find_one({"email": session["email"]})
        if current_user['role'] != 'admin':
            return redirect(url_for("logged_in"))
        username = request.form.get("username")
        email = request.form.get("email")

        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user_found = users_collection.find_one({"username": username})
        email_found = users_collection.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that username'
            return render_template('register.html', message=message)
        if email_found:
            message = 'This email already exists in database'
            return render_template('register.html', message=message)
        if password1 != password2:
            message = 'Passwords should match!'
            return render_template('register.html', message=message)
        else:
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            user_input = {'username': username, 'email': email, 'password': hashed, 'role': 'user'}
            users_collection.insert_one(user_input)
            return redirect(url_for('registered'))
    else:
        return render_template('register.html', message=message)


@app.route("/registe    red")
def registered():
    if "email" in session:
        session.pop("email")
        return render_template('registered.html')
    else:
        return redirect(url_for("login"))


@app.route("/", methods=["POST", "GET"])
def login():
    message = 'Please login to your account'
    if "email" in session:
        return redirect(url_for("logged_in"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        email_found = users_collection.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']

            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["email"] = email_val
                return redirect(url_for('logged_in'))
            else:
                if "email" in session:
                    return redirect(url_for("logged_in"))
                message = 'Wrong password'
                return render_template('login.html', message=message)
        else:
            message = 'Email not found'
            return render_template('login.html', message=message)
    return render_template('login.html', message=message)


@app.route('/logged_in')
def logged_in():
    if "email" in session:
        email = session['email']
        return render_template('logged_in.html', email=email)
    else:
        return redirect(url_for("login"))


@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
        return render_template("logout.html")
    else:
        return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=False)
