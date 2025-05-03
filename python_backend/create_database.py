import parse_html
import vector_index

from dotenv import load_dotenv
import os

import pymongo

def create_database(html_file_name:str, database_name:str, collection_name:str):
    load_dotenv()

    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN") #DATABASE_LOGIN is in the form username:password

    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

    # connect to your Atlas cluster
    client = pymongo.MongoClient(uri)

    database = client[database_name]

    collection = database[collection_name]

    data = parse_html.parse_html(html_file_name)

    collection.insert_many(data)

    client.close()

create_database("bylaws.html","bylaws","1-304")