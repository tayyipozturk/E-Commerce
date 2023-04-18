from flask import Flask, request, jsonify, render_template, url_for, redirect, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_cors import CORS, cross_origin
import werkzeug.security as ws

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
        self.seller_id = users_collection.find_one({'username': seller})['_id']
        self.image = image
        self.size = size
        self.colour = colour
        self.spec = spec
        self.rating = 0
        self.reviews = []
        self.rates = []
        users_collection.find_one({'username': seller})['items'].append(self._id)

    def save(self):
        item_dict = {'category': self.category, 'name': self.name, 'description': self.description, 'price': self.price, 'seller': self.seller,
                     'image': self.image, 'size': self.size, 'colour': self.colour, 'spec': self.spec,
                     'rating': self.rating, 'reviews': self.reviews, 'seller_id': self.seller_id, 'rates': self.rates}
        self._id = items_collection.insert_one(item_dict).inserted_id

        user = users_collection.find_one({'username': self.seller})
        user['items'].append(str(self._id))
        users_collection.update_one({'username': self.seller}, {'$set': {'items': user['items']}})
        return str(self._id)


@app.route('/items/<category>', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_item(category):
    current_user = users_collection.find_one({'username': session['username']})
    if current_user['role'] != 'admin':
        return redirect(url_for('products'))
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    image = request.form.get('image')
    seller = request.form.get('seller')
    if seller not in [user['username'] for user in users_collection.find({})]:
        flash('Seller does not exist')
        message = 'Seller user does not exist'
        return render_template('page/product/product_form.html', category=category, message=message)
    if category == 'Clothing':
        size = request.form.get('size')
        colour = request.form.get('colour')
        item = Item(category, name, description, price, seller, image, size, colour)
    elif category == 'Computer Components' or category == 'Monitors':
        spec = request.form.get('spec')
        item = Item(category, name, description, price, seller, image, spec=spec)
    else:
        item = Item(category, name, description, price, seller, image)
    item.save()
    return redirect(url_for('products'))


@app.route('/category_choice', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def category_choice():
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/category_form.html', role=current_user['role'])


@app.route('/item_form', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def item_form():
    category = request.form.get('category')
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/product_form.html', category=category, role=current_user['role'])


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


@app.route('/delete_item/<item_id>', methods=['POST'])
@cross_origin(supports_credentials=True)
def delete_item(item_id):
    item = items_collection.find_one({'_id': ObjectId(item_id)})
    seller_id = item['seller_id']
    print(item)
    user = users_collection.find_one({'_id': seller_id})

    for review in item['reviews']:
        reviewer = users_collection.find_one({'_id': ObjectId(review[0])})
        for i in range(len(reviewer['reviews'])):
            if reviewer['reviews'][i][0] == str(item_id):
                reviewer['reviews'].pop(i)
                break
        users_collection.update_one({'_id': ObjectId(review[0])}, {'$set': {'reviews': reviewer['reviews']}})

    for rate in item['rates']:
        rater = users_collection.find_one({'_id': ObjectId(rate[0])})
        for i in range(len(rater['rates'])):
            if rater['rates'][i][0] == str(item_id):
                rater['rates'].pop(i)
                if len(rater['rates']) == 0:
                    rater['rating'] = 0
                else:
                    rater['rating'] = sum([int(rate[2]) for rate in rater['rates']]) / len(rater['rates'])
                    users_collection.update_one({'_id': ObjectId(rate[0])}, {'$set': {'rating': rater['rating']}})
                break
        users_collection.update_one({'_id': ObjectId(rate[0])}, {'$set': {'rates': rater['rates']}})

    # pop item from user's items
    for i in range(len(user['items'])):
        if user['items'][i] == item_id:
            user['items'].pop(i)
            users_collection.update_one({'_id': seller_id}, {'$set': {'items': user['items']}})
            break
    items_collection.delete_one({'_id': ObjectId(item_id)})
    return redirect(url_for('products'))


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
    return render_template('page/product/products.html', product_list=product_list)


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
            item['seller_id'] = str(item['seller_id'])
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
                item['seller_id'] = str(seller_id['_id'])
                item['seller_id'] = str(item['seller_id'])
                product_list.append(item)

    if 'username' in session:
        current_user = users_collection.find_one({'username': session['username']})
        return render_template('page/product/products.html', product_list=product_list, message=message, role=current_user['role'])
    else:
        return render_template('page/index.html', product_list=product_list)


@app.route("/add_review/<item_id>", methods=['POST'])
@cross_origin(supports_credentials=True)
def add_review(item_id):
    review = request.form.get('review')
    if review is None or review == '':
        return redirect(url_for('products', message='Review cannot be empty'))

    item = items_collection.find_one({'_id': ObjectId(item_id)})
    current_user = users_collection.find_one({'username': session['username']})

    items_review = [str(current_user['_id']), current_user['username'], review]
    users_review = [str(item_id), item['name'], review]

    for i in range(len(item['reviews'])):
        if item['reviews'][i][0] == str(current_user['_id']):
            item['reviews'][i] = items_review
            items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'reviews': item['reviews']}})
            for j in range(len(current_user['reviews'])):
                if current_user['reviews'][j][0] == str(item_id):
                    current_user['reviews'][j] = users_review
                    users_collection.update_one({'_id': ObjectId(current_user['_id'])}, {'$set': {'reviews': current_user['reviews']}})
                    return redirect(url_for('get_product', item_id=item_id))

    item['reviews'].append(items_review)
    items_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'reviews': item['reviews']}})
    current_user['reviews'].append(users_review)
    users_collection.update_one({'_id': ObjectId(current_user['_id'])}, {'$set': {'reviews': current_user['reviews']}})
    return redirect(url_for('get_product', item_id=item_id))


@app.route("/add_rating/<item_id>", methods=['POST'])
@cross_origin(supports_credentials=True)
def add_rating(item_id):
    rating = request.form.get('rating')
    if rating is None or rating == '':
        return redirect(url_for('get_product', item_id=item_id, message='Rating cannot be empty'))

    item = items_collection.find_one({'_id': ObjectId(item_id)})
    current_user = users_collection.find_one({'username': session['username']})

    items_rating = [str(current_user['_id']), current_user['username'], rating]
    users_rating = [str(item_id), item['name'], rating]

    for i in range(len(item['rates'])):
        if item['rates'][i][0] == str(current_user['_id']):
            item['rates'][i] = items_rating
            for j in range(len(current_user['rates'])):
                if current_user['rates'][j][0] == str(item_id):
                    current_user['rates'][j] = users_rating
                    updateRating(item, current_user)
                    return redirect(url_for('get_product', item_id=item_id))

    item['rates'].append(items_rating)
    current_user['rates'].append(users_rating)
    updateRating(item, current_user)
    return redirect(url_for('get_product', item_id=item_id, message='Rating added'))


def updateRating(item, user):
    total_rating = 0
    for rate in item['rates']:
        total_rating += int(rate[2])
    item['rating'] = float(total_rating) / len(item['rates'])
    items_collection.update_one({'_id': ObjectId(item['_id'])}, {'$set': {'rates': item['rates']}})
    items_collection.update_one({'_id': ObjectId(item['_id'])}, {'$set': {'rating': item['rating']}})
    total_rating = 0
    for rate in user['rates']:
        total_rating += int(rate[2])
    if len(user['rates']) == 0:
        user['rating'] = 0
    else:
        user['rating'] = float(total_rating) / len(user['rates'])
    users_collection.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'rates': user['rates']}})
    users_collection.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'rating': user['rating']}})


class User:
    def __init__(self, username, email, password, role):
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.items = []
        self.rating = 0
        self.rates = []
        self.reviews = []

    def save(self):
        user_dict = {'username': self.username, 'email': self.email, 'password': self.password, 'role': self.role, 'items': self.items, 'rating': self.rating, 'rates': self.rates, 'reviews': self.reviews}
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
    password = ws.generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    user_id = User(username, email, password, role).save()
    if user_id == "error: user with username or email already exists":
        return jsonify({'success': False, 'error': 'user with username or email already exists'})
    return jsonify({'success': True, 'user_id': user_id})


@app.route('/users/<user_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_user(user_id):
    username = request.json.get('username')
    if username is None:
        return jsonify({'error': 'Username is missing'})
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': username}})
    return 'User updated'


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
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/clothing.html', clothing_list=clothing_list, role=current_user['role'])


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
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/computer_components.html', computer_component_list=computer_component_list, role=current_user['role'])


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
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/monitors.html', monitor_list=monitor_list, role=current_user['role'])


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
    current_user = users_collection.find_one({'username': session['username']})
    return render_template('page/product/snacks.html', snack_list=snack_list, role=current_user['role'])


@app.route('/items/item/<item_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_product(item_id):
    item = items_collection.find_one({'_id': ObjectId(item_id)})
    item['_id'] = str(item['_id'])
    item['name'] = str(item['name'])
    item['seller'] = str(item['seller'])
    seller = users_collection.find_one({'username': item['seller']})
    seller_id = str(seller['_id'])
    item['reviews'] = [{'user_id': review[0], 'user_name': review[1], 'review': review[2]} for review in item['reviews']]
    item['rates'] = [{'user_id': rating[0], 'user_name': rating[1], 'review': rating[2]} for rating in item['rates']]
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


@app.route('/users', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_users():
    if 'username' not in session:
        return redirect(url_for('logout'))
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


@app.route('/users/delete/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def delete_user(user_id):
    isLoggedInUser = False
    if 'username' in session:
        isLoggedInUser = True
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    users_items = user['items']
    users_reviews = user['reviews']
    users_rates = user['rates']
    # delete ratings and reviews of the item from other users
    for item in users_items:
        item_reviews = items_collection.find_one({'_id': ObjectId(item)})['reviews']
        item_rates = items_collection.find_one({'_id': ObjectId(item)})['rates']
        for review in item_reviews:
            reviewer_id = review[0]
            reviewer_user = users_collection.find_one({'_id': ObjectId(reviewer_id)})
            for i in range(len(reviewer_user['reviews'])):
                if reviewer_user['reviews'][i][0] == item:
                    reviewer_user['reviews'].pop(i)
                    break
            users_collection.update_one({'_id': ObjectId(reviewer_id)}, {'$set': {'reviews': reviewer_user['reviews']}})
        for rate in item_rates:
            rater_id = rate[0]
            rater_user = users_collection.find_one({'_id': ObjectId(rater_id)})
            for i in range(len(rater_user['rates'])):
                if rater_user['rates'][i][0] == item:
                    rater_user['rates'].pop(i)
                    rater_user['rating'] = sum([int(rate[2]) for rate in rater_user['rates']]) / len(rater_user['rates'])
                    break
            users_collection.update_one({'_id': ObjectId(rater_id)}, {'$set': {'rates': rater_user['rates']}})
            users_collection.update_one({'_id': ObjectId(rater_id)}, {'$set': {'rating': rater_user['rating']}})
        items_collection.delete_one({'_id': ObjectId(item)})
    # delete reviews of the user from items they reviewed
    for review in users_reviews:
        reviewed_item = review[0]
        item = items_collection.find_one({'_id': ObjectId(reviewed_item)})
        for i in range(len(item['reviews'])):
            if item['reviews'][i][0] == user_id:
                item['reviews'].pop(i)
                break
        items_collection.update_one({'_id': ObjectId(reviewed_item)}, {'$set': {'reviews': item['reviews']}})
    # delete rates of the user from items they rated
    for rate in users_rates:
        rated_item = rate[0]
        item = items_collection.find_one({'_id': ObjectId(rated_item)})
        for i in range(len(item['rates'])):
            if item['rates'][i][0] == user_id:
                item['rates'].pop(i)
                if len(item['rates']) > 0:
                    item['rating'] = sum([int(rate[2]) for rate in item['rates']]) / len(item['rates'])
                else:
                    item['rating'] = 0
                break
        items_collection.update_one({'_id': ObjectId(rated_item)}, {'$set': {'rates': item['rates']}})
        items_collection.update_one({'_id': ObjectId(rated_item)}, {'$set': {'rating': item['rating']}})

    users_collection.delete_one({'_id': ObjectId(user_id)})
    if isLoggedInUser:
        return redirect(url_for('logout'))
    return redirect(url_for('get_users'))


@app.route('/users/form', methods=['GET', 'POST'])
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
        role = request.form.get('role')
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('user_add_form'))
        password = ws.generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        User(username, email, password, role).save()
        return redirect(url_for('get_users'))


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
        return redirect(url_for('get_users'))


@app.route('/profile', methods=['GET'])
@cross_origin(supports_credentials=True)
def profile():
    current_user = users_collection.find_one({'username': session['username']})
    current_user['_id'] = str(current_user['_id'])
    current_user['username'] = str(current_user['username'])
    current_user['email'] = str(current_user['email'])
    current_user['role'] = str(current_user['role'])
    return render_template('page/user/profile.html', user=current_user, role=current_user['role'])


@app.route('/users/<user_id>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_user(user_id):
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
    if "username" not in session:
        return redirect(url_for("login"))
    current_user = users_collection.find_one({"username": session["username"]})
    render_template('page/admin/user_add_form.html', role=current_user['role'])
    if request.method == "POST":
        if current_user['role'] != 'admin':
            message = 'You need to login as admin before adding a user.'
            return redirect(url_for("products", message=message))
        username = request.form.get("username")
        email = request.form.get("email")

        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        role = request.form.get("role")
        user_found = users_collection.find_one({"username": username})
        email_found = users_collection.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that username'
            flash(message)
            return render_template('page/admin/user_add_form.html', message=message, role=current_user['role'])
        if email_found:
            message = 'This email already exists in database'
            flash(message)
            return render_template('page/admin/user_add_form.html', message=message, role=current_user['role'])
        if password1 != password2:
            message = 'Passwords should match!'
            flash(message)
            return render_template('page/admin/user_add_form.html', message=message, role=current_user['role'])
        else:
            hashed = ws.generate_password_hash(password2, method='pbkdf2:sha256', salt_length=8)
            User(username, email, hashed, role).save()
            flash("User has been registered successfully")
            return redirect(url_for('registered'))
    else:
        return render_template('page/register.html', role=current_user['role'])


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
    if "username" in session:
        return redirect(url_for("products"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        username_found = users_collection.find_one({"username": username})
        if username_found:
            username_val = username_found['username']
            passwordcheck = username_found['password']

            if ws.check_password_hash(passwordcheck, password):
                session["username"] = username_val
                session['role'] = users_collection.find_one({"username": username})['role']
                return redirect(url_for('products'))
            else:
                if "username" in session:
                    message = 'You are already logged in'
                    return redirect(url_for("products", message=message))
                message = 'Wrong password'
                flash(message)
                return render_template('page/index.html', message=message)
        else:
            message = 'Username not found'
            flash(message)
            return render_template('page/login.html', message=message)
    return render_template('page/login.html')


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
        session.pop("username")
        flash("You have been logged out")
        return render_template("page/logout.html")
    else:
        return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
