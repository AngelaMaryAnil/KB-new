import os
import logging
from flask import Flask, request, jsonify
from pymongo import MongoClient
import bcrypt
from flask_cors import CORS
import re
from bson import ObjectId

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["mydatabase"]  # Replace with your actual database name
users_collection = db["users"]
products_collection = db["products"]  # New collection for storing products

# ======================= USER AUTHENTICATION ========================== #

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    logger.info("Received registration data: %s", data)

    # Validate data
    errors = {}
    if not data.get('name'):
        errors['name'] = 'Name is required'
    if not data.get('email'):
        errors['email'] = 'Email is required'
    elif not re.match(r'\S+@\S+\.\S+', data['email']):
        errors['email'] = 'Please enter a valid email'
    if data.get('phone') and not re.match(r'^\d{10}$', data['phone']):
        errors['phone'] = 'Please enter a valid 10-digit phone number'
    if not data.get('password'):
        errors['password'] = 'Password is required'
    elif len(data['password']) < 8:
        errors['password'] = 'Password must be at least 8 characters'

    if errors:
        logger.error("Validation errors: %s", errors)
        return jsonify({'errors': errors}), 400

    # Hash the password
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())

    # Store data in MongoDB
    user = {
        'name': data['name'],
        'email': data['email'],
        'phone': data.get('phone'),
        'address': data.get('address'),
        'pincode': data.get('pincode'),
        'password': hashed_password,
        'role': data['role']
    }
    users_collection.insert_one(user)
    logger.info("User registered successfully: %s", user)

    return jsonify({'message': 'User registered successfully', 'id': str(user['_id'])}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    logger.info("Received login data: %s", data)

    # Validate data
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user in MongoDB
    user = users_collection.find_one({'email': data['email']})
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Check password
    if not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Return user data
    user_data = {
        'id': str(user['_id']),
        'email': user['email'],
        'name': user['name'],
        'phone': user['phone'],
        'address': user['address'],
        'pincode': user['pincode'],
        'role': user['role']
    }
    logger.info("User logged in successfully: %s", user_data)
    return jsonify(user_data), 200

# ========================== PRODUCT MANAGEMENT ========================== #

@app.route('/products', methods=['POST'])
def add_product():
    data = request.get_json()
    logger.info("Received product data: %s", data)

    # Validate input
    if not data.get('name') or not data.get('price') or not data.get('category'):
        return jsonify({'error': 'Product name, price, and category are required'}), 400

    product = {
        "name": data['name'],
        "description": data.get('description', ''),
        "price": float(data['price']),
        "stock": int(data.get('stock', 0)),
        "category": data['category'],
        "imageUrl": data.get('imageUrl', '')
    }
    result = products_collection.insert_one(product)
    logger.info("Product added: %s", product)

    return jsonify({'message': 'Product added successfully', 'id': str(result.inserted_id)}), 201


@app.route('/products', methods=['GET'])
def get_products():
    products = list(products_collection.find())
    products_list = [
        {
            'id': str(product['_id']),
            'name': product['name'],
            'description': product.get('description', ''),
            'price': product['price'],
            'stock': product.get('stock', 0),
            'category': product['category'],
            'imageUrl': product.get('imageUrl', '')
        }
        for product in products
    ]
    return jsonify(products_list), 200


@app.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    logger.info(f"Updating product {product_id} with data: {data}")

    if not ObjectId.is_valid(product_id):
        return jsonify({'error': 'Invalid product ID'}), 400

    update_data = {key: value for key, value in data.items() if value is not None}

    result = products_collection.update_one({'_id': ObjectId(product_id)}, {'$set': update_data})
    if result.matched_count == 0:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({'message': 'Product updated successfully'}), 200


@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    logger.info(f"Deleting product with ID: {product_id}")

    if not ObjectId.is_valid(product_id):
        return jsonify({'error': 'Invalid product ID'}), 400

    result = products_collection.delete_one({'_id': ObjectId(product_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({'message': 'Product deleted successfully'}), 200

# ===================================================================== #

if __name__ == '__main__':
    app.run(debug=True)