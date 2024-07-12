import pandas as pd
from pymongo import MongoClient

# MongoDB setup
print("Connecting to MongoDB...")
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['imot-scrape']
collection = db['imoti-for-sale']

# Import CSV data into MongoDB
print("Importing CSV...")
df = pd.read_csv('properties.csv')

# Convert DataFrame to dictionary and insert into MongoDB
print("Inserting data into MongoDB...")
data_dict = df.to_dict("records")
collection.insert_many(data_dict)
print(f"Inserted {len(data_dict)} records from CSV into MongoDB.")