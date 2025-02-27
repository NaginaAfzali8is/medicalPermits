from pymongo import MongoClient

# MongoDB setup
# client = MongoClient('mongodb://admin:admin123@35.183.49.252:27017/')
# db = client['admin']
client = MongoClient('mongodb://admin:Hayat123%3F%3F@3.99.161.206:27017/')
db = client['madinahBot']

# MongoDB collection for health permits
HealthPermitForm = db['health_permits']

# MongoDB collection for health permits
Owner = db['owner']
