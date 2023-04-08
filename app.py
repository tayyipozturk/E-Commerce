from flask import Flask, request, jsonify, render_template, url_for, redirect, session, flash
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
cart_collection = db['cart']
users_collection.create_index([('username', 1)], unique=True)


class Item:
    def __init__(self, category, name, description, price, seller, image, size=None, colour=None, spec=None):
        self._id = None
        self.category = category
        self.name = name
        self.description = description
        self.price = price
        self.seller = seller
        self.image = image
        self.size = size
        self.colour = colour
        self.spec = spec
        self.rating = 0
        self.rate_count = 0
        self.reviews = []

    def insert_review(self, review):
        self.reviews.append(review)
        items_collection.update_one({'_id': ObjectId(self._id)}, {'$push': {'reviews': review}})
        return 'Review inserted'

    def rate(self, rating):
        self.rate_count += 1
        self.rating = (self.rating * (self.rate_count - 1) + rating) / self.rate_count
        items_collection.update_one({'_id': ObjectId(self._id)}, {'$set': {'rating': self.rating}})

    def save(self):
        item_dict = {'category': self.category, 'name': self.name, 'description': self.description, 'price': self.price, 'seller': self.seller,
                     'image': self.image, 'size': self.size, 'colour': self.colour, 'spec': self.spec,
                     'rating': self.rating, 'reviews': self.reviews}
        self._id = items_collection.insert_one(item_dict).inserted_id
        return str(self._id)


@app.route('/items', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_item():
    category = request.json.get('category')
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
    item = Item(category, name, description, price, seller, image, size, colour, spec)
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
    category = request.json.get('category')
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
    items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'category': category, 'name': name, 'description': description,
                                                                      'price': price, 'seller': seller, 'image': image,
                                                                      'size': size, 'colour': colour, 'spec': spec}})
    return 'Item updated'


@app.route('/items/<item_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def delete_item(item_id):
    items_collection.delete_one({'_id': ObjectId(item_id)})
    return 'Item deleted'


@app.route('/items', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_items():
    product_list = []
    for item in items_collection.find():
        item['_id'] = str(item['_id'])
        item['name'] = str(item['name'])
        item['seller'] = str(item['seller'])
        item['reviews'] = [str(review) for review in item['reviews']]
        item['rating'] = str(item['rating'])
        item['price'] = str(item['price'])
        item['size'] = str(item['size'])
        item['colour'] = str(item['colour'])
        item['spec'] = str(item['spec'])
        item['image'] = str(item['image'])
        product_list.append(item)
    return render_template('page/product/all_products.html', product_list=product_list)


@app.route('/', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def products(message=None):
    # get form inputs to check if categories are selected
    show = {'Clothing': request.form.get('showClothing'),
            'Computer Components': request.form.get('showComputerComponents'),
            'Monitors': request.form.get('showMonitors'), 'Snacks': request.form.get('showSnacks')}

    print(show)
    # get all items from database
    product_list = []
    if show['Clothing'] != 'True' and show['Computer Components'] != 'True' and show['Monitors'] != 'True' and show['Snacks'] != 'True':
        for item in items_collection.find():
            item['_id'] = str(item['_id'])
            item['name'] = str(item['name'])
            item['seller'] = str(item['seller'])
            item['reviews'] = [str(review) for review in item['reviews']]
            item['rating'] = str(item['rating'])
            item['price'] = str(item['price'])
            item['size'] = str(item['size'])
            item['colour'] = str(item['colour'])
            item['spec'] = str(item['spec'])
            item['image'] = str(item['image'])
            seller_id = users_collection.find_one({'username': item['seller']})
            item.update({'seller_id': str(seller_id['_id'])})
            item['seller_id'] = str(item['seller_id'])
            product_list.append(item)
    else:
        for item in items_collection.find():
            if show[item['category']] == 'True':
                item['_id'] = str(item['_id'])
                item['name'] = str(item['name'])
                item['seller'] = str(item['seller'])
                item['reviews'] = [str(review) for review in item['reviews']]
                item['rating'] = str(item['rating'])
                item['price'] = str(item['price'])
                item['size'] = str(item['size'])
                item['colour'] = str(item['colour'])
                item['spec'] = str(item['spec'])
                item['image'] = str(item['image'])
                seller_id = users_collection.find_one({'username': item['seller']})
                item.update({'seller_id': str(seller_id['_id'])})
                item['seller_id'] = str(item['seller_id'])
                product_list.append(item)

    current_user = users_collection.find_one({'username': session['username']})
    if 'email' in session:
        return render_template('page/product/all_products.html', product_list=product_list, message=message, role=current_user['role'])
    else:
        return render_template('page/index.html', product_list=product_list)


class User:
    def __init__(self, username, email, password, role):
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.rating = 0
        self.rate_count = 0
        self.reviews = []

    def insert_review_to_item(self, item_id, review):
        self.reviews.append(review)
        items_collection.update_one({'_id': ObjectId(item_id)}, {'$push': {'reviews': review}})
        return 'Review inserted'

    def rate(self, item_id):
        items_collection.update_one({'_id': ObjectId(item_id)}, {'$inc': {'rate_count': 1}})
        items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'rating': {'$avg': ['$rating', self.rating]}}})
        self.rate_count += 1
        self.rating = (self.rating * (self.rate_count - 1) + self.rating) / self.rate_count
        return 'Rating updated'

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


@app.route('/clothing', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_clothing():
    clothing_list = []
    for item in items_collection.find():
        if item['category'] == 'Clothing':
            item['_id'] = str(item['_id'])
            item['name'] = str(item['name'])
            item['seller'] = str(item['seller'])
            item['reviews'] = [str(review) for review in item['reviews']]
            item['rating'] = str(item['rating'])
            item['price'] = str(item['price'])
            item['size'] = str(item['size'])
            item['colour'] = str(item['colour'])
            item['spec'] = str(item['spec'])
            item['image'] = str(item['image'])
            clothing_list.append(item)
    return render_template('page/product/clothing.html', clothing_list=clothing_list)


@app.route('/computer_components', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_computer_components():
    computer_component_list = []
    for item in items_collection.find():
        if item['category'] == 'Computer Components':
            item['_id'] = str(item['_id'])
            item['name'] = str(item['name'])
            item['seller'] = str(item['seller'])
            item['reviews'] = [str(review) for review in item['reviews']]
            item['rating'] = str(item['rating'])
            item['price'] = str(item['price'])
            item['spec'] = str(item['spec'])
            item['image'] = str(item['image'])
            computer_component_list.append(item)
    return render_template('page/product/computer_components.html', computer_component_list=computer_component_list)


@app.route('/monitors', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_monitors():
    monitor_list = []
    for item in items_collection.find():
        if item['category'] == 'Monitors':
            item['_id'] = str(item['_id'])
            item['name'] = str(item['name'])
            item['seller'] = str(item['seller'])
            item['reviews'] = [str(review) for review in item['reviews']]
            item['rating'] = str(item['rating'])
            item['price'] = str(item['price'])
            item['spec'] = str(item['spec'])
            item['image'] = str(item['image'])
            monitor_list.append(item)
    return render_template('page/product/monitors.html', monitor_list=monitor_list)


@app.route('/snacks', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_snacks():
    snack_list = []
    for item in items_collection.find():
        if item['category'] == 'Snacks':
            item['_id'] = str(item['_id'])
            item['name'] = str(item['name'])
            item['seller'] = str(item['seller'])
            item['reviews'] = [str(review) for review in item['reviews']]
            item['rating'] = str(item['rating'])
            item['price'] = str(item['price'])
            item['image'] = str(item['image'])
            snack_list.append(item)
    return render_template('page/product/snacks.html', snack_list=snack_list)


@app.route('/items/item/<item_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_product(item_id):
    item = items_collection.find_one({'_id': ObjectId(item_id)})
    item['_id'] = str(item['_id'])
    item['name'] = str(item['name'])
    item['seller'] = str(item['seller'])
    seller = users_collection.find_one({'username': item['seller']})
    seller_id = str(seller['_id'])
    item['reviews'] = [str(review) for review in item['reviews']]
    item['rating'] = str(item['rating'])
    item['price'] = str(item['price'])
    item['size'] = str(item['size'])
    item['colour'] = str(item['colour'])
    item['spec'] = str(item['spec'])
    item['image'] = str(item['image'])
    item['category'] = str(item['category'])
    item['description'] = str(item['description'])
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/product.html', item=item, seller_id=seller_id, role=current_user['role'])


@app.route('/all_users', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_all_users():
    user_list = []
    for user in users_collection.find():
        user['_id'] = str(user['_id'])
        user['username'] = str(user['username'])
        user['email'] = str(user['email'])
        user['password'] = str(user['password'])
        user['role'] = str(user['role'])
        user_list.append(user)
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/admin/all_users.html', user_list=user_list, role=current_user['role'])


@app.route('/user_delete/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_delete(user_id):
    users_collection.delete_one({'_id': ObjectId(user_id)})
    return redirect(url_for('get_all_users'))


@app.route('/user_add_form', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_add_form():
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/admin/user_add_form.html', role=current_user['role'])


@app.route('/user_add', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_add():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('user_add_form'))
        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        role = request.form.get('role')
        user = {
            'username': username,
            'email': email,
            'password': password,
            'role': role
        }
        users_collection.insert_one(user)
        return redirect(url_for('get_all_users'))


@app.route('/user_update_form/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_update_form(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    user['_id'] = str(user['_id'])
    user['username'] = str(user['username'])
    user['email'] = str(user['email'])
    user['role'] = str(user['role'])
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/admin/user_update_form.html', user=user, role=current_user['role'])


@app.route('/user_update/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_update(user_id):
    if request.method == 'POST':
        role = request.form.get('role')
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'role': role}})
        return redirect(url_for('get_all_users'))


@app.route('/all_users/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_seller(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    user['_id'] = str(user['_id'])
    user['username'] = str(user['username'])
    user['email'] = str(user['email'])
    user['role'] = str(user['role'])
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/user/seller_profile.html', seller=user, role=current_user['role'])


@app.route("/register", methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def register():
    message = 'You need to login as admin before adding a user.'
    if "username" not in session:
        return redirect(url_for("login"))
    current_user = users_collection.find_one({"username": session["username"]})
    render_template('page/register.html', message=message, role=current_user['role'])
    if request.method == "POST":
        if current_user['role'] != 'admin':
            message = 'You need to login as admin before adding a user.'
            return redirect(url_for("products", message=message))
        username = request.form.get("username")
        email = request.form.get("email")

        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user_found = users_collection.find_one({"username": username})
        email_found = users_collection.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that username'
            flash(message)
            return render_template('page/register.html', message=message, role=current_user['role'])
        if email_found:
            message = 'This email already exists in database'
            flash(message)
            return render_template('page/register.html', message=message, role=current_user['role'])
        if password1 != password2:
            message = 'Passwords should match!'
            flash(message)
            return render_template('page/register.html', message=message, role=current_user['role'])
        else:
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            user_input = {'username': username, 'email': email, 'password': hashed, 'role': 'user'}
            users_collection.insert_one(user_input)
            flash("User has been registered successfully")
            return redirect(url_for('registered'))
    else:
        return render_template('page/register.html', message=message, role=current_user['role'])


@app.route("/registered")
@cross_origin(supports_credentials=True)
def registered():
    if "username" in session:
        session.pop("username")
        flash("You have been logged out")
        return render_template('page/registered.html')
    else:
        return redirect(url_for("login"))


@app.route("/login", methods=["POST", "GET"])
@cross_origin(supports_credentials=True)
def login():
    message = 'Please login to your account'
    if "username" in session:
        return redirect(url_for("products"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        username_found = users_collection.find_one({"username": username})
        if username_found:
            username_val = username_found['username']
            passwordcheck = username_found['password']

            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["username"] = username_val
                session['role'] = users_collection.find_one({"username": username})['role']
                return redirect(url_for('products'))
            else:
                if "username" in session:
                    message = 'You are already logged in'
                    return redirect(url_for("products", message=message))
                message = 'Wrong password'
                flash(message)
                return render_template('page/product/all_products.html', message=message)
        else:
            message = 'Username not found'
            flash(message)
            return render_template('page/login.html', message=message)
    return render_template('page/login.html', message=message)


@app.route('/logged_in')
@cross_origin(supports_credentials=True)
def logged_in():
    if "username" in session:
        username = session['username']
        current_user = users_collection.find_one({'username': session['username']})
        return render_template('page/logged_in.html', username=username, role=current_user['role'])
    else:
        return redirect(url_for("login"))


@app.route("/logout", methods=["POST", "GET"])
@cross_origin(supports_credentials=True)
def logout():
    if "username" in session:
        session.pop("username", None)
        flash("You have been logged out")
        return render_template("page/logout.html")
    else:
        return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=False)
