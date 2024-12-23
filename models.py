from pymongo import MongoClient

# MongoDB setup
client = MongoClient('mongodb://admin:admin123@35.183.49.252:27017/')
db = client['admin']

# MongoDB collection for health permits
HealthPermitForm = db['health_permits']
